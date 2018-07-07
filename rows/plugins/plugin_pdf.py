# coding: utf-8

# Copyright 2014-2018 Álvaro Justen <https://github.com/turicas/rows/>

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
import logging
from collections import defaultdict

from cached_property import cached_property
from pdfminer.converter import PDFPageAggregator, TextConverter
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTChar, LTRect
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter, resolve1
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

from rows.plugins.utils import create_table, get_filename_and_fobj


logging.getLogger("pdfminer").setLevel(logging.ERROR)
TEXT_TYPES = (LTTextBox, LTTextLine, LTChar)


def number_of_pages(filename_or_fobj):
    filename, fobj = get_filename_and_fobj(filename_or_fobj, mode='rb')
    parser = PDFParser(fobj)
    document = PDFDocument(parser)
    return resolve1(document.catalog['Pages'])['Count']


def _get_pdf_document(fobj):
    parser = PDFParser(fobj)
    doc = PDFDocument(parser)
    parser.set_document(doc)
    return doc


def pdf_to_text(filename_or_fobj, page_numbers=None):
    """Extract all text objects from a PDF file"""

    filename, fobj = get_filename_and_fobj(filename_or_fobj, mode='rb')
    doc = _get_pdf_document(fobj)
    for page_number, page in enumerate(PDFPage.create_pages(doc), start=1):
        if page_numbers is None or page_number in page_numbers:
            rsrcmgr = PDFResourceManager()
            laparams = LAParams()
            result = io.StringIO()
            device = TextConverter(rsrcmgr, result, laparams=laparams)
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            interpreter.process_page(page)
            yield result.getvalue()


def get_delimiter_function(value):
    if isinstance(value, str):  # regular string, match exactly
        return lambda obj: (isinstance(obj, TEXT_TYPES) and
                            obj.get_text().strip() == value)

    elif hasattr(value, 'search'):  # regular expression
        return lambda obj: bool(isinstance(obj, TEXT_TYPES) and
                                value.search(obj.get_text().strip()))

    elif callable(value):  # function
        return lambda obj: bool(value(obj))


def pdf_objects(fobj, page_numbers, starts_after=None, ends_before=None,
                desired_types=(LTTextBox, LTTextLine, LTChar, LTRect)):
    'For each page inside a PDF, return the list of text objects'

    doc = _get_pdf_document(fobj)
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
        if page_numbers is None or page_number in page_numbers:
            interpreter.process_page(page)
            layout = device.get_result()
            objs = [obj for obj in layout if isinstance(obj, desired_types)]
            objs.sort(key=lambda obj: -obj.y0)
            objects_in_page = []
            for obj in objs:
                if (not started and starts_after is not None
                    and starts_after(obj)):
                    started = True
                if started and ends_before is not None and ends_before(obj):
                    finished = True
                    break

                if started:
                    objects_in_page.append(obj)
            yield objects_in_page

            if finished:
                break
    fobj.close()


class Group(object):
    'Helper class to group objects based on its positions and sizes'

    def __init__(self, minimum=float('inf'), maximum=float('-inf'), threshold=0):
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
    dimension_0 = 'y0'
    dimension_1 = 'y1'


class VerticalGroup(Group):
    dimension_0 = 'x0'
    dimension_1 = 'x1'


def group_objects(objs, threshold, axis):
    if axis == 'x':
        GroupClass = VerticalGroup
    elif axis == 'y':
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

    contains = x2min >= x1min and x2max <= x1max and \
            y2min >= y1min and y2max <= y1max
    overlaps = (x1min <= x2min <= x1max and y1min <= y2min <= y1max) or \
               (x1min <= x2min <= x1max and y1min <= y2max <= y1max) or \
               (x1min <= x2max <= x1max and y1min <= y2min <= y1max) or \
               (x1min <= x2max <= x1max and y1min <= y2max <= y1max)
    return contains or overlaps


class ExtractionAlgorithm(object):

    def __init__(self, objects, text_objects, x_threshold, y_threshold):
        self.objects = objects
        self.text_objects = text_objects
        self.x_threshold = x_threshold
        self.y_threshold = y_threshold

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

        return [obj for obj in self.text_objects
                if contains_or_overlap(self.table_bbox, obj.bbox)]

    def get_lines(self):
        x_intervals = list(self.x_intervals)
        y_intervals = reversed(list(self.y_intervals))
        objs = list(self.selected_objects)

        matrix = []
        for y0, y1 in y_intervals:
            line = []
            for x0, x1 in x_intervals:
                cell = [obj
                    for obj in objs
                    if x0 <= obj.x0 <= x1 and y0 <= obj.y0 <= y1]
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

    name = 'y-groups'

    # TODO: filter out objects with empty text before grouping by y0 (but
    # consider them if inside table's bbox)
    # TODO: get y0 groups bbox and merge overlapping ones (overlapping only on
    # y, not on x). ex: imgs-33281.pdf/06.png should not remove bigger cells

    @cached_property
    def table_bbox(self):
        groups = group_objects(self.text_objects, self.y_threshold, 'y')
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

        intervals = [(key, max_attr(max(value, key=max_attr)))
                     for key, value in groups.items()]
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
            axis='x',
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
            axis='y',
        )


class HeaderPositionAlgorithm(YGroupsAlgorithm):

    name = 'header-position'

    @property
    def x_intervals(self):
        raise NotImplementedError

    def get_lines(self):
        objects = self.selected_objects
        objects.sort(key=lambda obj: obj.x0)
        y_intervals = list(reversed(self.y_intervals))
        used, lines = [], []

        header_interval = y_intervals[0]
        header_objs = [obj for obj in objects
                       if header_interval[0] <= obj.y0 <= header_interval[1]]
        used.extend(header_objs)
        lines.append([[obj] for obj in header_objs])

        def x_intersects(a, b):
            return a.x0 < b.x1 and a.x1 > b.x0

        for y0, y1 in y_intervals[1:]:
            line_objs = [obj for obj in objects
                         if obj not in used and y0 <= obj.y0 <= y1]
            line = []
            for column in header_objs:
                y_objs = [obj for obj in line_objs
                          if obj not in used and x_intersects(column, obj)]
                used.extend(y_objs)
                line.append(y_objs)
            lines.append(line)

            # TODO: may check if one of objects in line_objs is not in used and
            # raise an exception

        return lines


class RectsBoundariesAlgorithm(ExtractionAlgorithm):
    """Extraction algorithm based on rectangles present in the page"""

    name = 'rects-boundaries'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rects = [obj for obj in self.objects
                      if isinstance(obj, LTRect) and obj.fill]

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
        set(grandchild for child in children
                       for grandchild in subclasses(child))
    )


def algorithms():
    return {Class.name: Class for Class in subclasses(ExtractionAlgorithm)}


def get_cell_text(cell):
    if cell is None:
        return None
    # TODO: this is not the best way to sort cells
    cell.sort(key=lambda obj: -obj.y0)
    return '\n'.join(obj.get_text().strip() for obj in cell)


def get_table(objs, algorithm='y-groups', x_threshold=0.5, y_threshold=0.5):
    'Where the magic happens'

    available_algorithms = algorithms()
    if isinstance(algorithm, ExtractionAlgorithm):
        AlgorithmClass = algorithm
    elif isinstance(algorithm, str):
        if algorithm not in available_algorithms:
            raise ValueError(
                'Unknown algorithm "{}" (options are: {})'.format(
                    algorithm, ', '.join(available_algorithms.keys())
                )
            )
        AlgorithmClass = available_algorithms[algorithm]
    else:
        raise ValueError(
            'Unknown algorithm "{}" (options are: {})'.format(
                algorithm, ', '.join(available_algorithms.keys())
            )
        )

    objs = list(objs)
    text_objs = [obj for obj in objs if isinstance(obj, TEXT_TYPES)]
    extractor = AlgorithmClass(objs, text_objs, x_threshold, y_threshold)

    # Fill the table based on x and y intervals from the extractor
    return [[get_cell_text(cell) for cell in row]
            for row in extractor.get_lines()]


def pdf_table_lines(fobj, page_numbers, algorithm='y-groups',
                    starts_after=None, ends_before=None,
                    x_threshold=0.5, y_threshold=0.5):
    pages = pdf_objects(fobj, page_numbers, starts_after, ends_before)
    header = line_size = None
    for page_index, page in enumerate(pages):
        lines = get_table(
            page,
            algorithm=algorithm,
            x_threshold=x_threshold,
            y_threshold=y_threshold,
        )
        for line_index, line in enumerate(lines):
            if line_index == 0:
                if page_index == 0:
                    header = line
                    line_size = len(line)
                elif page_index > 0 and line == header:  # skip header repetition
                    continue
            assert line_size == len(line)
            yield line


def import_from_pdf(filename_or_fobj, page_numbers=None,
                    starts_after=None, ends_before=None,
                    algorithm='y-groups', x_threshold=0.5, y_threshold=0.5,
                    *args, **kwargs):
    filename, fobj = get_filename_and_fobj(filename_or_fobj, mode='rb')

    # TODO: create tests
    meta = {
        'imported_from': 'pdf',
        'filename': filename,
    }
    table_rows = pdf_table_lines(
        fobj,
        page_numbers,
        starts_after=starts_after,
        ends_before=ends_before,
        algorithm=algorithm,
        x_threshold=x_threshold,
        y_threshold=y_threshold,
    )
    return create_table(table_rows, meta=meta, *args, **kwargs)
