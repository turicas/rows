# coding: utf-8

# Copyright 2014-2017 Álvaro Justen <https://github.com/turicas/rows/>

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

from pdfminer.converter import PDFPageAggregator, TextConverter
from pdfminer.layout import LAParams, LTTextBox, LTTextLine, LTChar, LTRect
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter, resolve1
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

from rows.plugins.utils import create_table, get_filename_and_fobj


logging.getLogger("pdfminer").setLevel(logging.ERROR)
TEXT_TYPES = (LTTextBox, LTTextLine, LTChar)


def number_of_pages(filename):
    with open(filename, mode='rb') as fobj:
        parser = PDFParser(fobj)
        document = PDFDocument(parser)
        return resolve1(document.catalog['Pages'])['Count']


class Group(object):
    'Helper class to group objects based on its positions and sizes'

    def __init__(self, minimum=float('inf'), maximum=float('-inf'), threshold=0.5):
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
        return (self.min <= getattr(obj, self.dimension_0) <= self.max or
                self.min <= getattr(obj, self.dimension_1) <= self.max)

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

    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    parser = PDFParser(fobj)
    doc = PDFDocument(parser)
    parser.set_document(doc)
    assert doc.is_extractable

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


def group_objects(objs, get_attr_function, group_size, axis):
    if axis == 'x':
        GroupClass = VerticalGroup
    elif axis == 'y':
        GroupClass = HorizontalGroup

    objs.sort(key=get_attr_function)
    groups = []
    for obj in objs:
        found = False
        for group in groups:
            if group.contains(obj):
                group.add(obj)
                found = True
                break
        if not found:
            group = GroupClass(threshold=group_size)
            group.add(obj)
            groups.append(group)
    return {group.minimum: group.objects for group in groups}


def define_intervals(objs, min_attr, max_attr, threshold, axis):
    groups = group_objects(objs, min_attr, threshold, axis)

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


def fill_matrix(objs, x_intervals, y_intervals):
    y_intervals = reversed(list(y_intervals))
    objs = list(objs)

    matrix = []
    for y0, y1 in y_intervals:
        line = []
        for x0, x1 in x_intervals:
            cell = [obj
                   for obj in objs
                   if x0 <= obj.x0 <= x1 and y0 <= obj.y0 <= y1]
            if not cell:
                content = None
            else:
                cell.sort(key=lambda obj: -obj.y0)
                content = '\n'.join(obj.get_text().strip() for obj in cell)
                for obj in cell:
                    objs.remove(obj)
            line.append(content)
        matrix.append(line)
    return matrix


def get_table(objs, x_threshold=0.5, y_threshold=0.5):
    'Where the magic happens'

    # TODO: split this function in many others
    all_objs = objs
    text_objs = [obj for obj in all_objs if isinstance(obj, TEXT_TYPES)]

    # Define table lines based on objects' y values (with some threshold) -
    # these lines will only be used to determine table boundaries.
    lines = []
    groups = group_objects(objs, lambda obj: obj.y0, y_threshold)
    new_objs = []
    for key, value in groups.items():
        if len(value) < 2:  # Ignore 1-column tables and floating text objects
            continue
        value.sort(key=lambda obj: obj.x0)
        lines.append((key, value))
        new_objs.extend(value)

    # Define table boundaries
    x_min = y_min = float('inf')
    x_max = y_max = float('-inf')
    for _, line_objects in lines:
        for obj in line_objects:
            if obj.x0 <= x_min:
                x_min = obj.x0
            if obj.x1 >= x_max:
                x_max = obj.x1
            if obj.y0 <= y_min:
                y_min = obj.y0
            if obj.y1 >= y_max:
                y_max = obj.y1
    table_bbox = (x_min, y_min, x_max, y_max)

    # Filter out objects outside table boundaries
    objs = [obj for obj in text_objs
            if contains_or_overlap(table_bbox, obj.bbox)]

    # Define x and y intervals based on filtered objects
    objs.sort(key=lambda obj: obj.x0)
    x_intervals = define_intervals(
            objs,
            min_attr=lambda obj: obj.x0,
            max_attr=lambda obj: obj.x1,
            threshold=x_threshold
    )
    objs.sort(key=lambda obj: -obj.y1)
    y_intervals = define_intervals(
            objs,
            min_attr=lambda obj: obj.y0,
            max_attr=lambda obj: obj.y1,
            threshold=y_threshold
    )

    # Create an empty matrix and fill in with objects
    return fill_matrix(objs, x_intervals, y_intervals)


def pdf_table_lines(fobj, page_numbers, starts_after=None, ends_before=None):
    # TODO: may use LTRect and LTLine objects to help identifying table
    # boundaries and cells' positions when filling them.
    pages = pdf_objects(fobj, page_numbers, starts_after, ends_before)
    header = None
    for page_index, page in enumerate(pages):
        for line_index, line in enumerate(get_table(page)):
            if line_index == 0:
                if page_index == 0:
                    header = line
                elif page_index > 0 and line == header:  # skip header repetition
                    continue
            yield line


def pdf_to_text(filename_or_fobj):
    'Extract all text objects from a PDF file'

    filename, fobj = get_filename_and_fobj(filename_or_fobj, mode='rb')

    # TODO: specify page range

    parser = PDFParser(fobj)
    doc = PDFDocument(parser)
    parser.set_document(doc)
    assert doc.is_extractable

    for page in PDFPage.create_pages(doc):
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        result = io.StringIO()
        device = TextConverter(rsrcmgr, result, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        interpreter.process_page(page)
        yield result.getvalue()


def import_from_pdf(filename_or_fobj, page_numbers=None,
                    starts_after=None, ends_before=None,
                    *args, **kwargs):
    filename, fobj = get_filename_and_fobj(filename_or_fobj, mode='rb')

    # TODO: create tests
    # TODO: pass threshold to pdf_table_lines (and from there to get_pages)
    # TODO: specify page range
    # TODO: filter out objects with empty text before grouping by y0 (but
    # consider them if inside table's bbox)
    # TODO: get y0 groups bbox and merge overlapping ones (overlapping only on
    # y, not on x). ex: imgs-33281.pdf/06.png should not remove bigger cells
    meta = {
            'imported_from': 'pdf',
            'filename': filename,
    }
    table_rows = pdf_table_lines(
        fobj,
        page_numbers,
        starts_after=starts_after,
        ends_before=ends_before,
    )
    return create_table(table_rows, meta=meta, *args, **kwargs)
