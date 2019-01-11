# coding: utf-8

# Copyright 2014-2019 Álvaro Justen <https://github.com/turicas/rows/>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import io
from collections import defaultdict

import six

try:
    import fitz as pymupdf

    pymupdf_imported = True
except ImportError:
    pymupdf_imported = False

from cached_property import cached_property

try:
    from pdfminer.converter import PDFPageAggregator, TextConverter
    from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTChar, LTRect
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter, resolve1
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdfparser import PDFParser
    import logging

    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    TEXT_TYPES = (LTTextBox, LTTextLine, LTChar)
    pdfminer_imported = True
except ImportError:
    pdfminer_imported = False

from rows.plugins.utils import create_table, get_filename_and_fobj


def default_backend():
    if pymupdf_imported:
        return "pymupdf"
    elif pdfminer_imported:
        return "pdfminer.six"
    else:
        raise ImportError(
            "No PDF backend found. Did you install the dependencies (pymupdf or pdfminer.six)?"
        )


def number_of_pages(filename_or_fobj, backend=None):
    backend = backend or default_backend()
    Backend = get_backend(backend)
    pdf_doc = Backend(filename_or_fobj)
    return pdf_doc.number_of_pages


def pdf_to_text(filename_or_fobj, page_numbers=None, backend=None):
    backend = backend or default_backend()
    Backend = get_backend(backend)
    pdf_doc = Backend(filename_or_fobj)
    yield from pdf_doc.extract_text(page_numbers=page_numbers)


class PDFBackend(object):

    """Base Backend class to parse PDF files"""

    x_order = 1
    y_order = 1

    def __init__(self, filename_or_fobj):
        self.filename_or_fobj = filename_or_fobj

    @property
    def number_of_pages(self):
        "Number of pages in the document"
        raise NotImplementedError()

    def extract_text(self):
        "Return a string for each page in the document (generator)"
        raise NotImplementedError()

    def objects(self):
        "Return a list of objects for each page in the document (generator)"
        raise NotImplementedError()

    def text_objects(self):
        "Return a list of text objects for each page in the document (generator)"
        raise NotImplementedError()

    @property
    def text(self):
        return "\n\n".join(self.extract_text())

    def get_cell_text(self, cell):
        if not cell:
            return ""
        if self.y_order == 1:
            cell.sort(key=lambda obj: obj.y0)
        else:
            cell.sort(key=lambda obj: -obj.y0)
        return "\n".join(obj.text.strip() for obj in cell)


class PDFMinerBackend(PDFBackend):

    name = "pdfminer.six"
    y_order = -1

    @cached_property
    def document(self):
        filename, fobj = get_filename_and_fobj(self.filename_or_fobj, mode="rb")
        parser = PDFParser(fobj)
        doc = PDFDocument(parser)
        parser.set_document(doc)
        return doc

    @cached_property
    def number_of_pages(self):
        return resolve1(self.document.catalog["Pages"])["Count"]

    def extract_text(self, page_numbers=None):
        for page_number, page in enumerate(
            PDFPage.create_pages(self.document), start=1
        ):
            if page_numbers is not None and page_number not in page_numbers:
                continue

            rsrcmgr = PDFResourceManager()
            laparams = LAParams()
            result = io.StringIO()
            device = TextConverter(rsrcmgr, result, laparams=laparams)
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            interpreter.process_page(page)
            yield result.getvalue()

    @staticmethod
    def convert_object(obj):
        if isinstance(obj, TEXT_TYPES):
            return TextObject(
                x0=obj.x0, y0=obj.y0, x1=obj.x1, y1=obj.y1, text=obj.get_text()
            )
        elif isinstance(obj, LTRect):
            return RectObject(x0=obj.x0, y0=obj.y0, x1=obj.x1, y1=obj.y1, fill=obj.fill)

    def objects(
        self,
        page_numbers=None,
        starts_after=None,
        ends_before=None,
        desired_types=(LTTextBox, LTTextLine, LTChar, LTRect),
    ):

        doc = self.document
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        started, finished = False, False
        if starts_after is None:
            started = True
        else:
            starts_after = get_delimiter_function(starts_after)
        if ends_before is not None:
            ends_before = get_delimiter_function(ends_before)

        for page_number, page in enumerate(PDFPage.create_pages(doc), start=1):
            if page_numbers is not None and page_number not in page_numbers:
                continue

            interpreter.process_page(page)
            layout = device.get_result()
            objs = [
                PDFMinerBackend.convert_object(obj)
                for obj in layout
                if isinstance(obj, desired_types)
            ]
            objs.sort(key=lambda obj: -obj.y0)
            objects_in_page = []
            for obj in objs:
                if not started and starts_after is not None and starts_after(obj):
                    started = True
                if started and ends_before is not None and ends_before(obj):
                    finished = True
                    break

                if started:
                    objects_in_page.append(obj)
            yield objects_in_page

            if finished:
                break

    def text_objects(self, page_numbers=None, starts_after=None, ends_before=None):
        return self.objects(
            page_numbers=page_numbers,
            starts_after=starts_after,
            ends_before=ends_before,
            desired_types=(LTTextBox, LTTextLine, LTChar),
        )


class PyMuPDFBackend(PDFBackend):

    name = "pymupdf"

    @cached_property
    def document(self):
        filename, fobj = get_filename_and_fobj(self.filename_or_fobj, mode="rb")
        if not filename:
            data = fobj.read()  # TODO: may use a lot of memory
            doc = pymupdf.open(stream=data, filetype="pdf")
        else:
            doc = pymupdf.open(filename=filename, filetype="pdf")
        return doc

    @cached_property
    def number_of_pages(self):
        return self.document.pageCount

    def extract_text(self, page_numbers=None):
        doc = self.document
        for page_number, page_index in enumerate(range(doc.pageCount), start=1):
            if page_numbers is not None and page_number not in page_numbers:
                continue

            page = doc.loadPage(page_index)
            page_text = "\n".join(block[4] for block in page.getTextBlocks())
            yield page_text

    def objects(self, page_numbers=None, starts_after=None, ends_before=None):
        doc = self.document

        started, finished = False, False
        if starts_after is None:
            started = True
        else:
            starts_after = get_delimiter_function(starts_after)
        if ends_before is not None:
            ends_before = get_delimiter_function(ends_before)

        for page_number, page_index in enumerate(range(doc.pageCount), start=1):
            if page_numbers is not None and page_number not in page_numbers:
                continue

            page = doc.loadPage(page_index)
            text_objs = []
            for block in page.getText("dict")["blocks"]:
                if block["type"] != 0:
                    continue

                for line in block["lines"]:
                    line_text = " ".join(span["text"] for span in line["spans"])
                    text_objs.append([*line["bbox"], line_text])
            objs = [
                TextObject(x0=obj[0], y0=obj[1], x1=obj[2], y1=obj[3], text=obj[4])
                for obj in text_objs
            ]
            objs.sort(key=lambda obj: (obj.y0, obj.x0))
            objects_in_page = []
            for obj in objs:
                if not started and starts_after is not None and starts_after(obj):
                    started = True
                if started and ends_before is not None and ends_before(obj):
                    finished = True
                    break

                if started:
                    objects_in_page.append(obj)

            yield objects_in_page

            if finished:
                break

    text_objects = objects


def get_delimiter_function(value):
    if isinstance(value, str):  # regular string, match exactly
        return lambda obj: (isinstance(obj, TextObject) and obj.text.strip() == value)

    elif hasattr(value, "search"):  # regular expression
        return lambda obj: bool(
            isinstance(obj, TextObject) and value.search(obj.text.strip())
        )

    elif callable(value):  # function
        return lambda obj: bool(value(obj))


class TextObject(object):
    def __init__(self, x0, y0, x1, y1, text):
        self.x0 = x0
        self.x1 = x1
        self.y0 = y0
        self.y1 = y1
        self.text = text

    @property
    def bbox(self):
        return (self.x0, self.y0, self.x1, self.y1)

    def __repr__(self):
        text = repr(self.text)
        if len(text) > 50:
            text = repr(self.text[:45] + "[...]")
        bbox = ", ".join("{:.3f}".format(value) for value in self.bbox)
        return "<TextObject ({}) {}>".format(bbox, text)


class RectObject(object):
    def __init__(self, x0, y0, x1, y1, fill):
        self.x0 = x0
        self.x1 = x1
        self.y0 = y0
        self.y1 = y1
        self.fill = fill

    @property
    def bbox(self):
        return (self.x0, self.y0, self.x1, self.y1)

    def __repr__(self):
        bbox = ", ".join("{:.3f}".format(value) for value in self.bbox)
        return "<RectObject ({}) fill={}>".format(bbox, self.fill)


class Group(object):
    "Helper class to group objects based on its positions and sizes"

    def __init__(self, minimum=float("inf"), maximum=float("-inf"), threshold=0):
        self.minimum = minimum
        self.maximum = maximum
        self.threshold = threshold
        self.objects = []

    @property
    def min(self):
        return self.minimum - self.threshold

    @property
    def max(self):
        return self.maximum + self.threshold

    def contains(self, obj):
        d0 = getattr(obj, self.dimension_0)
        d1 = getattr(obj, self.dimension_1)
        middle = d0 + (d1 - d0) / 2.0
        return self.min <= middle <= self.max

    def add(self, obj):
        self.objects.append(obj)
        d0 = getattr(obj, self.dimension_0)
        d1 = getattr(obj, self.dimension_1)
        if d0 < self.minimum:
            self.minimum = d0
        if d1 > self.maximum:
            self.maximum = d1


class HorizontalGroup(Group):
    dimension_0 = "y0"
    dimension_1 = "y1"


class VerticalGroup(Group):
    dimension_0 = "x0"
    dimension_1 = "x1"


def group_objects(objs, threshold, axis):
    if axis == "x":
        GroupClass = VerticalGroup
    elif axis == "y":
        GroupClass = HorizontalGroup

    groups = []
    for obj in objs:
        found = False
        for group in groups:
            if group.contains(obj):
                group.add(obj)
                found = True
                break
        if not found:
            group = GroupClass(threshold=threshold)
            group.add(obj)
            groups.append(group)
    return {group.minimum: group.objects for group in groups}


def contains_or_overlap(a, b):
    x1min, y1min, x1max, y1max = a
    x2min, y2min, x2max, y2max = b

    contains = x2min >= x1min and x2max <= x1max and y2min >= y1min and y2max <= y1max
    overlaps = (
        (x1min <= x2min <= x1max and y1min <= y2min <= y1max)
        or (x1min <= x2min <= x1max and y1min <= y2max <= y1max)
        or (x1min <= x2max <= x1max and y1min <= y2min <= y1max)
        or (x1min <= x2max <= x1max and y1min <= y2max <= y1max)
    )
    return contains or overlaps


class ExtractionAlgorithm(object):
    def __init__(
        self, objects, text_objects, x_threshold, y_threshold, x_order, y_order
    ):
        self.objects = objects
        self.text_objects = text_objects
        self.x_threshold = x_threshold
        self.y_threshold = y_threshold
        self.x_order = x_order
        self.y_order = y_order

    @property
    def table_bbox(self):
        raise NotImplementedError

    @property
    def x_intervals(self):
        raise NotImplementedError

    @property
    def y_intervals(self):
        raise NotImplementedError

    @cached_property
    def selected_objects(self):
        """Filter out objects outside table boundaries"""

        return [
            obj
            for obj in self.text_objects
            if contains_or_overlap(self.table_bbox, obj.bbox)
        ]

    def get_lines(self):
        x_intervals = list(self.x_intervals)
        if self.x_order == -1:
            x_intervals = list(reversed(x_intervals))
        y_intervals = list(self.y_intervals)
        if self.y_order == -1:
            y_intervals = list(reversed(y_intervals))
        objs = list(self.selected_objects)

        matrix = []
        for y0, y1 in y_intervals:
            line = []
            for x0, x1 in x_intervals:
                cell = [
                    obj for obj in objs if x0 <= obj.x0 <= x1 and y0 <= obj.y0 <= y1
                ]
                if not cell:
                    line.append(None)
                else:
                    line.append(cell)
                    for obj in cell:
                        objs.remove(obj)
            matrix.append(line)
        return matrix


class YGroupsAlgorithm(ExtractionAlgorithm):
    """Extraction algorithm based on objects' y values"""

    name = "y-groups"

    # TODO: filter out objects with empty text before grouping by y0 (but
    # consider them if inside table's bbox)
    # TODO: get y0 groups bbox and merge overlapping ones (overlapping only on
    # y, not on x). ex: imgs-33281.pdf/06.png should not remove bigger cells

    @cached_property
    def table_bbox(self):
        groups = group_objects(self.text_objects, self.y_threshold, "y")
        desired_objs = []
        for group_objs in groups.values():
            if len(group_objs) < 2:  # Ignore floating text objects
                continue
            desired_objs.extend(group_objs)
        if not desired_objs:
            return (0, 0, 0, 0)
        x_min = min(obj.x0 for obj in desired_objs)
        x_max = max(obj.x1 for obj in desired_objs)
        y_min = min(obj.y0 for obj in desired_objs)
        y_max = max(obj.y1 for obj in desired_objs)
        return (x_min, y_min, x_max, y_max)

    @staticmethod
    def _define_intervals(objs, min_attr, max_attr, threshold, axis):
        groups = group_objects(objs, threshold, axis)

        intervals = [
            (key, max_attr(max(value, key=max_attr))) for key, value in groups.items()
        ]
        intervals.sort()
        if not intervals:
            return []

        # Merge overlapping intervals
        result = [intervals[0]]
        for current in intervals[1:]:
            previous = result.pop()
            if current[0] <= previous[1] or current[1] <= previous[1]:
                result.append((previous[0], max((previous[1], current[1]))))
            else:
                result.extend((previous, current))
        return result

    @cached_property
    def x_intervals(self):
        objects = self.selected_objects
        objects.sort(key=lambda obj: obj.x0)
        return self._define_intervals(
            objects,
            min_attr=lambda obj: obj.x0,
            max_attr=lambda obj: obj.x1,
            threshold=self.x_threshold,
            axis="x",
        )

    @cached_property
    def y_intervals(self):
        objects = self.selected_objects
        objects.sort(key=lambda obj: -obj.y1)
        return self._define_intervals(
            objects,
            min_attr=lambda obj: obj.y0,
            max_attr=lambda obj: obj.y1,
            threshold=self.y_threshold,
            axis="y",
        )


class HeaderPositionAlgorithm(YGroupsAlgorithm):

    name = "header-position"

    @property
    def x_intervals(self):
        raise NotImplementedError

    def get_lines(self):
        objects = self.selected_objects
        objects.sort(key=lambda obj: obj.x0)
        y_intervals = list(self.y_intervals)
        if self.y_order == -1:
            y_intervals = list(reversed(y_intervals))
        used, lines = [], []

        header_interval = y_intervals[0]
        header_objs = [
            obj for obj in objects if header_interval[0] <= obj.y0 <= header_interval[1]
        ]
        used.extend(header_objs)
        lines.append([[obj] for obj in header_objs])

        def x_intersects(a, b):
            return a.x0 < b.x1 and a.x1 > b.x0

        for y0, y1 in y_intervals[1:]:
            line_objs = [
                obj for obj in objects if obj not in used and y0 <= obj.y0 <= y1
            ]
            line = []
            for column in header_objs:
                y_objs = [
                    obj
                    for obj in line_objs
                    if obj not in used and x_intersects(column, obj)
                ]
                used.extend(y_objs)
                line.append(y_objs)
            lines.append(line)

            # TODO: may check if one of objects in line_objs is not in used and
            # raise an exception

        return lines


class RectsBoundariesAlgorithm(ExtractionAlgorithm):
    """Extraction algorithm based on rectangles present in the page"""

    name = "rects-boundaries"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rects = [
            obj for obj in self.objects if isinstance(obj, RectObject) and obj.fill
        ]

    @cached_property
    def table_bbox(self):
        y0 = min(obj.y0 for obj in self.rects)
        y1 = max(obj.y1 for obj in self.rects)
        x0 = min(obj.x0 for obj in self.rects)
        x1 = max(obj.x1 for obj in self.rects)
        return (x0, y0, x1, y1)

    @staticmethod
    def _clean_intersections(lines):
        def other_line_contains(all_lines, search_line):
            for line2 in all_lines:
                if search_line == line2:
                    continue
                elif search_line[0] >= line2[0] and search_line[1] <= line2[1]:
                    return True
            return False

        final = []
        for line in lines:
            if not other_line_contains(lines, line):
                final.append(line)
        return final

    @cached_property
    def x_intervals(self):
        x_intervals = set((obj.x0, obj.x1) for obj in self.rects)
        return sorted(self._clean_intersections(x_intervals))

    @cached_property
    def y_intervals(self):
        y_intervals = set((obj.y0, obj.y1) for obj in self.rects)
        return sorted(self._clean_intersections(y_intervals))


def subclasses(cls):
    children = cls.__subclasses__()
    return set(children).union(
        set(grandchild for child in children for grandchild in subclasses(child))
    )


def algorithms():
    return {Class.name: Class for Class in subclasses(ExtractionAlgorithm)}


def get_algorithm(algorithm):
    available_algorithms = algorithms()

    if isinstance(algorithm, six.text_type):
        if algorithm not in available_algorithms:
            raise ValueError(
                'Unknown algorithm "{}" (options are: {})'.format(
                    algorithm, ", ".join(available_algorithms.keys())
                )
            )
        return available_algorithms[algorithm]

    elif issubclass(algorithm, ExtractionAlgorithm):
        return algorithm

    else:
        raise ValueError(
            'Unknown algorithm "{}" (options are: {})'.format(
                algorithm, ", ".join(available_algorithms.keys())
            )
        )


def backends():
    return {Class.name: Class for Class in subclasses(PDFBackend)}


def get_backend(backend):
    available_backends = backends()

    if isinstance(backend, six.text_type):
        if backend not in available_backends:
            raise ValueError(
                'Unknown PDF backend "{}" (options are: {})'.format(
                    backend, ", ".join(available_backends.keys())
                )
            )
        return available_backends[backend]

    elif issubclass(backend, PDFBackend):
        return backend

    else:
        raise ValueError(
            'Unknown PDF backend "{}" (options are: {})'.format(
                backend, ", ".join(available_backends.keys())
            )
        )


def pdf_table_lines(
    filename_or_fobj,
    page_numbers=None,
    algorithm="y-groups",
    starts_after=None,
    ends_before=None,
    x_threshold=0.5,
    y_threshold=0.5,
    backend=None,
):
    backend = backend or default_backend()

    # TODO: check if both backends accepts filename or fobj
    Backend = get_backend(backend)
    Algorithm = get_algorithm(algorithm)
    pdf_doc = Backend(filename_or_fobj)

    pages = pdf_doc.objects(
        page_numbers=page_numbers, starts_after=starts_after, ends_before=ends_before
    )
    header = line_size = None
    for page_index, page in enumerate(pages):
        objs = list(page)
        text_objs = [obj for obj in objs if isinstance(obj, TextObject)]
        extractor = Algorithm(
            objs, text_objs, x_threshold, y_threshold, pdf_doc.x_order, pdf_doc.y_order
        )
        lines = [
            [pdf_doc.get_cell_text(cell) for cell in row]
            for row in extractor.get_lines()
        ]

        for line_index, line in enumerate(lines):
            if line_index == 0:
                if page_index == 0:
                    header = line
                    line_size = len(line)
                elif page_index > 0 and line == header:  # skip header repetition
                    continue
            assert line_size == len(line)
            yield line


def import_from_pdf(
    filename_or_fobj,
    page_numbers=None,
    starts_after=None,
    ends_before=None,
    backend=None,
    algorithm="y-groups",
    x_threshold=0.5,
    y_threshold=0.5,
    *args,
    **kwargs
):
    backend = backend or default_backend()
    meta = {"imported_from": "pdf"}
    table_rows = pdf_table_lines(
        filename_or_fobj,
        page_numbers,
        starts_after=starts_after,
        ends_before=ends_before,
        algorithm=algorithm,
        x_threshold=x_threshold,
        y_threshold=y_threshold,
        backend=backend,
    )
    return create_table(table_rows, meta=meta, *args, **kwargs)


# Call the function so it'll raise ImportError if no backend is available
default_backend()
