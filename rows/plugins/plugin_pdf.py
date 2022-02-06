# coding: utf-8

# Copyright 2014-2022 Álvaro Justen <https://github.com/turicas/rows/>

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

import math
import statistics
from dataclasses import dataclass

import six
from cached_property import cached_property

from rows.plugins.utils import create_table
from rows.utils import Source

try:
    import fitz as pymupdf

    pymupdf.TOOLS.mupdf_display_errors(False)

    pymupdf_imported = True
except ImportError:
    pymupdf_imported = False


try:
    import logging

    from pdfminer.converter import PDFPageAggregator
    from pdfminer.layout import LAParams, LTChar, LTRect, LTTextBox, LTTextLine
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager, resolve1
    from pdfminer.pdfpage import PDFPage
    from pdfminer.pdfparser import PDFParser

    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    PDFMINER_TEXT_TYPES = (LTTextBox, LTTextLine, LTChar)
    PDFMINER_ALL_TYPES = (LTTextBox, LTTextLine, LTChar, LTRect)
    pdfminer_imported = True
except ImportError:
    pdfminer_imported = False
    PDFMINER_TEXT_TYPES, PDFMINER_ALL_TYPES = None, None


def extract_intervals(text, repeat=False, sort=True):
    """
    >>> extract_intervals("1,2,3")
    [1, 2, 3]
    >>> extract_intervals("1,2,5-10")
    [1, 2, 5, 6, 7, 8, 9, 10]
    >>> extract_intervals("1,2,5-10,3")
    [1, 2, 3, 5, 6, 7, 8, 9, 10]
    >>> extract_intervals("1,2,5-10,6,7")
    [1, 2, 5, 6, 7, 8, 9, 10]
    """

    result = []
    for value in text.split(","):
        value = value.strip()
        if "-" in value:
            start_value, end_value = value.split("-")
            start_value = int(start_value.strip())
            end_value = int(end_value.strip())
            result.extend(range(start_value, end_value + 1))
        else:
            result.append(int(value.strip()))

    if not repeat:
        result = list(set(result))
    if sort:
        result.sort()

    return result


def get_check_object_function(value):
    if isinstance(value, str):  # regular string, match exactly
        return lambda obj: (
            isinstance(obj, TextObject) and obj.text.strip() == value.strip()
        )

    elif hasattr(value, "search"):  # regular expression
        return lambda obj: bool(
            isinstance(obj, TextObject) and value.search(obj.text.strip())
        )

    elif callable(value):  # function
        return lambda obj: bool(value(obj))


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
    if isinstance(page_numbers, six.text_type):
        page_numbers = extract_intervals(page_numbers)

    backend = backend or default_backend()
    Backend = get_backend(backend)
    pdf_doc = Backend(filename_or_fobj)
    for page in pdf_doc.extract_text(page_numbers=page_numbers):
        yield page


class PDFBackend(object):

    """Base Backend class to parse PDF files"""

    def __init__(self, source):
        self.source = Source.from_file(source, plugin_name="pdf", mode="rb")

    @property
    def number_of_pages(self):
        "Number of pages in the document"
        raise NotImplementedError()

    @property
    def pages(self):
        "Yields each page of the document"
        raise NotImplementedError()

    def page_objects(self, page):
        "Return all objects for a page (got from self.pages)"
        raise NotImplementedError()

    def extract_text(self, page_numbers=None):
        "Return a string for each page in the document (generator)"
        for page_number, page in enumerate(self.pages, start=1):
            if page_numbers is not None and page_number not in page_numbers:
                continue
            yield "\n".join(
                obj.text
                for obj in self.page_objects(page)
                if isinstance(obj, TextObject)
            )

    @property
    def text(self):
        return "\n\n".join(self.extract_text())

    def get_cell_text(self, cell):
        if not cell:
            return ""
        cell.sort(key=lambda obj: (obj.y0, obj.x0))
        text = "\n".join(obj.text.strip() for obj in cell)
        # Each object could have its own lines (with trailing spaces), so we do
        # it again:
        return "\n".join(line.strip() for line in text.splitlines())

    def objects(self, page_numbers=None, starts_after=None, ends_before=None):
        "Return a list of objects for each page in the document (generator)"
        started, finished = False, False
        if starts_after is None:
            started = True
        else:
            starts_after = get_check_object_function(starts_after)
        if ends_before is not None:
            ends_before = get_check_object_function(ends_before)

        for page_number, page in enumerate(self.pages, start=1):
            if page_numbers is not None and page_number not in page_numbers:
                continue
            objects_in_page = []
            for obj in self.page_objects(page):
                if not started and starts_after is not None and starts_after(obj):
                    started = True
                elif started:
                    if ends_before is not None and ends_before(obj):
                        finished = True
                        break
                    objects_in_page.append(obj)
            yield objects_in_page
            if finished:
                break

    def text_objects(self, page_numbers=None, starts_after=None, ends_before=None):
        "Return a list of text objects for each page in the document (generator)"
        pages = self.objects(
            page_numbers=page_numbers,
            starts_after=starts_after,
            ends_before=ends_before,
        )
        for page in pages:
            yield [obj for obj in page if isinstance(obj, TextObject)]

    def __del__(self):
        source = self.source
        if (
            source.should_close
            and hasattr(source.fobj, "closed")
            and not source.fobj.closed
        ):
            source.fobj.close()


class PDFMinerBackend(PDFBackend):

    name = "pdfminer.six"

    @cached_property
    def document(self):
        parser = PDFParser(self.source.fobj)
        doc = PDFDocument(parser)
        parser.set_document(doc)
        return doc

    @cached_property
    def number_of_pages(self):
        return resolve1(self.document.catalog["Pages"])["Count"]

    @property
    def pages(self):
        yield from PDFPage.create_pages(self.document)

    @staticmethod
    def convert_object(obj, page_height):
        x0, x1 = obj.x0, obj.x1
        # Recalculate object's y values since PDFMiner uses bottom of page as 0
        # for y.
        y0, y1 = page_height - obj.y1, page_height - obj.y0

        if isinstance(obj, PDFMINER_TEXT_TYPES):
            return TextObject(x0=x0, y0=y0, x1=x1, y1=y1, text=obj.get_text().strip())
        elif isinstance(obj, LTRect):
            return RectObject(x0=x0, y0=y0, x1=x1, y1=y1, fill=obj.fill)

    def page_objects(self, page):
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        interpreter.process_page(page)
        layout = device.get_result()

        _, _, _, page_height = page.mediabox
        page_height = max([obj.y1 for obj in layout] + [page_height])
        objs = [
            PDFMinerBackend.convert_object(obj, page_height)
            for obj in layout
            if isinstance(obj, PDFMINER_ALL_TYPES)
        ]
        objs.sort(key=lambda obj: (obj.y0, obj.x0))
        return objs


class PyMuPDFBackend(PDFBackend):

    name = "pymupdf"

    @cached_property
    def document(self):
        if self.source.uri:
            doc = pymupdf.open(filename=self.source.uri, filetype="pdf")
        else:
            data = self.source.fobj.read()  # TODO: may use a lot of memory
            doc = pymupdf.open(stream=data, filetype="pdf")
        return doc

    @cached_property
    def number_of_pages(self):
        return self.document.pageCount

    @property
    def pages(self):
        load_page = getattr(self.document, "load_page") or getattr(
            self.document, "loadPage"
        )
        for page_index in range(self.number_of_pages):
            yield load_page(page_index)

    @staticmethod
    def convert_object(obj):
        bbox = obj["bbox"]
        text = " ".join(
            [
                "\n".join(line.strip() for line in span["text"].splitlines())
                for span in obj["spans"]
            ]
        )
        return TextObject(
            x0=bbox[0],
            y0=bbox[1],
            x1=bbox[2],
            y1=bbox[3],
            text=text,
            fonts=[span["font"] for span in obj["spans"]],
            sizes=[span["size"] for span in obj["spans"]],
            flags=[span["flags"] for span in obj["spans"]],
            colors=[span["color"] for span in obj["spans"]],
        )

    def page_objects(self, page):
        blocks = getattr(page, "get_text", getattr(page, "getText"))("dict")["blocks"]
        objects = [
            PyMuPDFBackend.convert_object(line)
            for block in blocks
            if block["type"] == 0
            for line in block["lines"]
        ]
        objects.sort(key=lambda obj: (obj.y0, obj.x0))
        return objects


@dataclass
class TextObject(object):
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    colors: int = None
    flags: int = None
    fonts: str = None
    sizes: int = None

    @property
    def center_x(self):
        return self.x0 + ((self.x1 - self.x0) / 2.0)

    @property
    def center_y(self):
        return self.y0 + ((self.y1 - self.y0) / 2.0)

    @property
    def center(self):
        return (self.center_x, self.center_y)

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


def object_intercepts(axis, obj1, obj2, threshold=0):
    """Check whether first object intercepts second's boundaries

    Each object is passed by its minimum and maximum value for the desired axis.
    """

    if axis == "x":
        min1, max1, min2, max2 = obj1.x0, obj1.x1, obj2.x0, obj2.x1
    elif axis == "y":
        min1, max1, min2, max2 = obj1.y0, obj1.y1, obj2.y0, obj2.y1
    return min1 < (max2 + threshold) and max1 > (min2 - threshold)


def object_contains_center(axis, obj1, obj2, threshold=0):
    """Check whether first object's center is contained by second's boundaries

    Each object is passed by its minimum and maximum value for the desired axis.
    """

    if axis == "x":
        min1, max1, min2, max2 = obj1.x0, obj1.x1, obj2.x0, obj2.x1
    elif axis == "y":
        min1, max1, min2, max2 = obj1.y0, obj1.y1, obj2.y0, obj2.y1
    return (min2 - threshold) <= (min1 + (max1 - min1) / 2.0) <= (max2 + threshold)


def object_contains(axis, obj1, obj2, threshold=0):
    """Check whether first object is contained by second's boundaries"""

    if axis == "x":
        min1, max1, min2, max2 = obj1.x0, obj1.x1, obj2.x0, obj2.x1
    elif axis == "y":
        min1, max1, min2, max2 = obj1.y0, obj1.y1, obj2.y0, obj2.y1
    return (min2 - threshold) <= min1 and max1 <= (max2 + threshold)


def define_threshold(axis, objects, proportion=0.3):
    """Define threshold based on average length of objects on this axis

    For y axis: uses `proportion` of average height
    For x axis: uses `proportion` of average character size (`(obj.x1 - obj.x0) / len(obj.text)`).
    """
    if not objects:
        return 0
    elif axis == "x":
        values = [
            (obj.x1 - obj.x0) / len(obj.text) if obj.text else 0 for obj in objects
        ]
    elif axis == "y":
        values = [obj.y1 - obj.y0 for obj in objects]
    return proportion * (sum(values) / len(values))


class Group(object):
    "Group objects based on its positions and sizes"

    def __init__(self, objects=None, threshold=0):
        self.x0 = float("inf")
        self.x1 = float("-inf")
        self.y0 = float("inf")
        self.y1 = float("-inf")
        self.objects = objects or []
        self.threshold = threshold
        if self.objects:
            self._update_boundaries(self.objects)

    def __len__(self):
        return len(self.objects)

    def __getitem__(self, key):
        return self.objects[key]

    def __repr__(self):
        return "<Group ({} element{}): [{}]>".format(
            len(self.objects),
            "s" if len(self.objects) != 1 else "",
            ", ".join(repr(obj.text) for obj in self.objects),
        )

    def _update_boundaries(self, objects):
        self.x0 = min(self.x0, min(obj.x0 for obj in objects))
        self.x1 = max(self.x1, max(obj.x1 for obj in objects))
        self.y0 = min(self.y0, min(obj.y0 for obj in objects))
        self.y1 = max(self.y1, max(obj.y1 for obj in objects))

    def add(self, obj):
        self.objects.append(obj)
        self._update_boundaries([obj])

    @property
    def bbox(self):
        return (self.x0, self.y0, self.x1, self.y1)

    def object_dimensions(self, obj):
        if self.axis == "x":
            return (obj.x0, obj.x1)
        elif self.axis == "y":
            return (obj.y0, obj.y1)

    def intercepts(self, axis, obj):
        """Check whether `obj` intercepts group boundaries (min/max -+ threshold)"""

        return object_intercepts(axis, obj, self, self.threshold)

    def contains_center(self, axis, obj):
        """Check whether `obj`'s center is contained by group boundaries (min/max -+ threshold)"""

        d0, d1 = self.object_dimensions(axis, obj)
        return object_contains_center(
            d0, d1, self.minimum, self.maximum, self.threshold
        )

    def contains(self, axis, obj):
        """Check whether `obj` is contained by group boundaries (min/max -+ threshold)"""

        d0, d1 = self.object_dimensions(axis, obj)
        return object_contains(d0, d1, self.minimum, self.maximum, self.threshold)


def group_objects(axis, objects, threshold=None, check_group=object_intercepts):
    """Group intercepting `objects` based on `axis` and `threshold`

    If `threshold` is `None`, `define_threshold` will be used to define a good
    one."""

    if threshold is None:
        threshold = define_threshold(axis, objects)

    if axis == "x":
        get_dimensions = lambda row: (row.x0, row.x1)
        get_ordering = lambda obj: (obj.x0, obj.x1)
        get_other_ordering = lambda obj: (obj.y0, obj.y1)
    elif axis == "y":
        get_dimensions = lambda row: (row.y0, row.y1)
        get_ordering = lambda obj: (obj.y0, obj.y1)
        get_other_ordering = lambda obj: (obj.x0, obj.x1)

    groups = [Group([obj]) for obj in sorted(objects, key=get_ordering)]
    index_1, final_index = 0, len(groups) - 1
    while index_1 < final_index:
        for index_2 in range(index_1 + 1, final_index + 1):
            group_1, group_2 = groups[index_1], groups[index_2]
            if check_group(axis, group_1, group_2, threshold):
                # Merge groups
                groups[index_1] = Group(group_1.objects + group_2.objects)
                del groups[index_2]
                final_index -= 1
                break
        else:
            index_1 += 1

    return [
        Group(sorted((obj for obj in group.objects), key=get_other_ordering))
        for group in groups
    ]


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


def distance(a, b):
    return math.sqrt((a.x0 - b.x0) ** 2 + (a.y0 - b.y0) ** 2)


def closest_object(objects, value):
    check = get_check_object_function(value)
    found = [obj for obj in objects if check(obj)]
    if not found:
        raise ValueError("Object not found with rule '{}'".format(value))

    desired_object = found[0]
    distances = {
        distance(desired_object, other): other
        for other in objects
        if other != desired_object
    }
    return distances[min(distances.keys())]


def objects_same_line(objects, value, threshold=None):
    if threshold is None:
        threshold = define_threshold("y", objects)

    check = get_check_object_function(value)

    for group in group_objects(axis="y", objects=objects, threshold=threshold):
        for obj in group:
            if check(obj):
                return group


def closest_same_line(objects, value, threshold=None):
    group = objects_same_line(objects, value, threshold)
    if group is None:
        return None

    distances = {
        min(abs(obj.x0 - other.x1), abs(obj.x1, other.x0)): other
        for other in group
        if other != obj
    }
    return distances[min(distances.keys())]


def objects_same_column(objects, value, threshold=None):
    if threshold is None:
        threshold = define_threshold("x", objects)

    check = get_check_object_function(value)

    for group in group_objects(axis="x", objects=objects, threshold=threshold):
        for obj in group:
            if check(obj):
                return group


def closest_same_column(objects, value, threshold=None):
    group = objects_same_column(objects, value, threshold)
    if group is None:
        return None

    distances = {
        min(abs(obj.y0 - other.y1), abs(obj.y1, other.y0)): other
        for other in group
        if other != obj
    }
    return distances[min(distances.keys())]


class ExtractionAlgorithm(object):
    # TODO: create an way to detect how many tables exist and its positions

    def __init__(
        self,
        objects,
        x_threshold=None,
        y_threshold=None,
        filtered=False,
    ):
        self.objects = list(objects)
        self.text_objects = [obj for obj in self.objects if isinstance(obj, TextObject)]
        self.x_threshold, self.y_threshold = x_threshold, y_threshold
        self.filtered = filtered

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
        y_intervals = list(self.y_intervals)

        # Ignore if it found only one column or line (in most cases it's not a
        # table)
        if len(x_intervals) < 2 or len(y_intervals) < 2:
            return []

        objs = list(self.selected_objects)

        # TODO: make the "match" method customizable, for example: create a
        # method to consider using {x,y}_intervals + {x,y}_threshold and the
        # object's bbox instead of using center of the object.
        matrix = []
        for y0, y1 in y_intervals:
            line = []
            for x0, x1 in x_intervals:
                cell = [
                    obj
                    for obj in objs
                    if x0 < obj.center_x < x1 and y0 < obj.center_y < y1
                ]
                if not cell:
                    line.append(None)
                else:
                    line.append(cell)
                    for obj in cell:
                        objs.remove(obj)

            # Remove empty lines
            line_text = "".join(
                "".join(str(obj.text or "") for obj in cell)
                for cell in line
                if cell is not None
            ).strip()
            if line_text:
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
    def selected_objects(self):
        """Select objects based on y groups and group widths"""

        if self.filtered:
            # Table is delimited by parameters, so won't try to decide where it
            # starts/finishes
            return self.text_objects

        # First, we group objects by y values (the goal is to have each
        # possible table line in a group)
        groups = group_objects("y", self.text_objects, threshold=self.y_threshold)

        # Then, calculate each group's width and the widths' mode and stdev
        groups_width = {
            index: group.x1 - group.x0 for index, group in enumerate(groups)
        }
        mode_width = statistics.mode(groups_width.values())
        stdev_width = statistics.stdev(groups_width.values())

        # To finish, find the groups that match the upper and lower width
        # limits (mode +- stdev) and get its objects.
        lower_limit, upper_limit = mode_width - stdev_width, mode_width + stdev_width
        objects = []
        for index, value in groups_width.items():
            if lower_limit <= value <= upper_limit:
                objects.extend(groups[index])
        return objects

    @cached_property
    def x_intervals(self):
        objects = self.selected_objects
        groups = group_objects(
            axis="x",
            objects=objects,
            threshold=self.x_threshold
            if self.x_threshold is not None
            else define_threshold("x", objects),
        )
        return sorted(((group.x0, group.x1) for group in groups))

    @cached_property
    def y_intervals(self):
        objects = self.selected_objects
        groups = group_objects(
            axis="y",
            objects=objects,
            threshold=self.y_threshold
            if self.y_threshold is not None
            else define_threshold("y", objects),
        )
        return [(group.y0, group.y1) for group in groups]


class HeaderPositionAlgorithm(YGroupsAlgorithm):
    name = "header-position"

    @property
    def x_intervals(self):
        raise NotImplementedError

    @cached_property
    def selected_objects(self):
        return self.text_objects

    def get_lines(self):
        # TODO: use new implementations of `group_objects` and `Group` to
        # enhance this method's code
        objects = self.selected_objects
        objects.sort(key=lambda obj: obj.x0)
        y_intervals = list(self.y_intervals)

        used, lines = [], []
        header_interval = y_intervals[0]
        # TODO: should consider y_intervals on header interval and on match?
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
            # Remove empty lines
            line_text = "".join(
                "".join(str(obj.text or "") for obj in cell)
                for cell in line
                if cell is not None
            ).strip()
            if line_text:
                lines.append(line)

            # TODO: may check if one of objects in line_objs is not in used and
            # raise an exception

        return lines


class RectsBoundariesAlgorithm(ExtractionAlgorithm):
    """Extraction algorithm based on rectangles present in the page"""

    name = "rects-boundaries"

    def __init__(self, *args, **kwargs):
        super(RectsBoundariesAlgorithm, self).__init__(*args, **kwargs)
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
    source,
    page_numbers=None,
    algorithm="y-groups",
    starts_after=None,
    ends_before=None,
    x_threshold=None,
    y_threshold=None,
    backend=None,
):
    if isinstance(page_numbers, six.text_type):
        page_numbers = extract_intervals(page_numbers)
    backend = backend or default_backend()

    # TODO: check if both backends accepts filename or fobj
    Backend = get_backend(backend)
    Algorithm = get_algorithm(algorithm)
    pdf_doc = Backend(source)

    pages = pdf_doc.objects(
        page_numbers=page_numbers, starts_after=starts_after, ends_before=ends_before
    )
    header = None
    for page_index, page in enumerate(pages):
        extractor = Algorithm(
            objects=page,
            x_threshold=x_threshold,
            y_threshold=y_threshold,
            filtered=starts_after is not None or ends_before is not None,
        )
        lines = [
            [pdf_doc.get_cell_text(cell) for cell in row]
            for row in extractor.get_lines()
        ]

        for line_index, line in enumerate(lines):
            if line_index == 0:
                if page_index == 0:
                    header = line
                elif page_index > 0 and line == header:  # skip header repetition
                    continue
            yield line


def import_from_pdf(
    filename_or_fobj,
    page_numbers=None,
    starts_after=None,
    ends_before=None,
    backend=None,
    algorithm="y-groups",
    x_threshold=None,
    y_threshold=None,
    *args,
    **kwargs
):

    if isinstance(page_numbers, six.text_type):
        page_numbers = extract_intervals(page_numbers)

    backend = backend or default_backend()
    source = Source.from_file(filename_or_fobj, plugin_name="pdf", mode="rb")
    meta = {"imported_from": "pdf", "source": source}
    table_rows = pdf_table_lines(
        source,
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
