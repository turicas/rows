# coding: utf-8

import locale

from collections import Mapping, OrderedDict, namedtuple
from contextlib import contextmanager
from unicodedata import normalize

import fields

from utils import as_string, is_null, slug


class Table(object):

    def __init__(self, fields):
        self.fields = OrderedDict(fields)
        # TODO: should we really use OrderedDict here?
        # TODO: slug field names
        self.field_names, self.field_types = [], []
        for field_name, field_type in self.fields.items():
            self.field_names.append(field_name)
            self.field_types.append(field_type)
        # TODO: should be able to customize row return type (namedtuple, dict etc.)
        self.Row = namedtuple('Row', self.field_names)
        self._rows = []

    def append(self, row):
        """Add a row to the table. Should be a dict"""

        # TODO: should be able to customize row type (namedtuple, dict etc.)
        row_data = []
        for field_name, field_type in self.fields.items():
            value = row.get(field_name, None)
            if not isinstance(value, field_type.TYPE):
                value = field_type.deserialize(value)
            row_data.append(value)
        self._rows.append(row_data)

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, item):
        # TODO: should support slice also?
        if not isinstance(item, int):
            raise ValueError('Type not recognized: {}'.format(type(item)))

        return self.Row(*self._rows[item])


def detect_field_types(field_names, sample_rows, *args, **kwargs):
    """Where the magic happens"""

    # TODO: should support receiving unicode objects directly
    # TODO: should expect data in unicode or will be able to use binary data?
    columns = zip(*sample_rows)
    # TODO: raise a ValueError exception instead
    assert len(columns) == len(field_names)

    available_types = list([getattr(fields, name) for name in fields.__all__
                            if name != 'Field'])
    none_type = set([type(None)])
    detected_types = OrderedDict([(field_name, None)
                                  for field_name in field_names])
    encoding = kwargs.get('encoding', None)
    for index, field_name in enumerate(field_names):
        possible_types = list(available_types)
        column_data = set(columns[index])

        if not [value for value in column_data if as_string(value).strip()]:
            # all rows with an empty field -> str (can't identify)
            identified_type = fields.ByteField
        else:
            # ok, let's try to identify the type of this column by
            # converting every value in the sample
            for value in column_data:
                if is_null(value):
                    continue

                cant_be = set()
                for type_ in possible_types:
                    try:
                        type_.deserialize(value, *args, **kwargs)
                    except (ValueError, TypeError):
                        cant_be.add(type_)
                for type_to_remove in cant_be:
                    possible_types.remove(type_to_remove)
            identified_type = possible_types[0]  # priorities matter
        detected_types[field_name] = identified_type
    return detected_types


# Utilities

@contextmanager
def locale_context(name, category=locale.LC_ALL):

    old_name = locale.getlocale(category)
    locale.setlocale(category, name)
    try:
        yield
    finally:
        locale.setlocale(category, old_name)


# CSV plugin

def import_from_csv(filename, fields=None, delimiter=',', quotechar='"',
                    encoding='utf-8'):
    'Import data from a CSV file'
    # TODO: add auto_detect_types=True parameter
    # this import will be moved in the future (to another module, actually)
    import unicodecsv

    fobj = open(filename)
    csv_reader = unicodecsv.reader(fobj, encoding=encoding, delimiter=',',
                                   quotechar='"')
    table_rows = [row for row in csv_reader]
    header, table_rows = table_rows[0], table_rows[1:]
    header = [slug(field_name).lower() for field_name in header]

    if fields is None:
        fields = detect_field_types(header, table_rows, encoding=encoding)
    table = Table(fields=fields)
    for row in table_rows:
        table.append({field_name: value
                      for field_name, value in zip(header, row)})
    return table

def export_to_csv(table, filename, encoding='utf-8'):
    import csv  # TODO: may use unicodecsv here

    with open(filename, mode='w') as fobj:
        fields = table.fields.items()
        csv_writer = csv.writer(fobj)
        csv_writer.writerow([field.encode(encoding) for field, _ in fields])

        for row in table:
            # TODO: will work only if table.fields is OrderedDict
            csv_writer.writerow([type_.serialize(getattr(row, field))
                                 for field, type_ in fields])


# XLS plugin

def import_from_xls(filename, fields=None, sheet_name=None, sheet_index=0,
                    start_row=0, start_column=0):
    import xlrd

    book = xlrd.open_workbook(filename)
    if sheet_name is not None:
        sheet = book.sheet_by_name(sheet_name)
    else:
        sheet = book.sheet_by_index(sheet_index)
    # TODO: may re-use Excel data types
    cell_value = lambda row, col: unicode(sheet.cell_value(row, col)).strip()

    # Get field names
    # TODO: may use sheet.col_values or even sheet.ncols
    column_count = 0
    header = []
    column_value = cell_value(start_row, start_column + column_count)
    while column_value:
        header.append(slug(column_value).lower())
        column_count += 1
        try:
            column_value = cell_value(start_row, start_column + column_count)
        except IndexError:
            column_value = ''
    header = [field.encode('utf-8') for field in header]

    # Get sheet rows
    # TODO: may use sheel.col_slice or even sheet.nrows
    table_rows = []
    row_count = 0
    start_row += 1
    cell_is_empty = False
    while not cell_is_empty:
        row = [cell_value(start_row + row_count, start_column + column_index)
               for column_index in range(column_count)]
        cell_is_empty = ''.join([field.strip() for field in row]) == ''
        if not cell_is_empty:
            table_rows.append(row)
            row_count += 1

    if fields is None:
        fields = detect_field_types(header, table_rows, encoding='utf-8')
    table = Table(fields=fields)
    for row in table_rows:
        table.append({field_name: value
                      for field_name, value in zip(header, row)})
    return table


# HTML plugin

import HTMLParser

from lxml.etree import HTML as html_element_tree, tostring as to_string


html_parser = HTMLParser.HTMLParser()

def import_from_html(html, fields=None, table_index=0, include_fields=None,
                     exclude_fields=None, converters=None, force_types=None):
    # TODO: unescape before returning
    # html = html_parser.unescape(html.decode(encoding))

    html_tree = html_element_tree(html)
    table_tree = html_tree.xpath('//table')
    try:
        table_tree = table_tree[table_index]
    except IndexError:
        raise IndexError('Table index {} not found'.format(table_index))

    table_html = to_string(table_tree)
    tr_elements = html_element_tree(table_html).xpath('//tr')
    table_rows = []
    for tr_element in tr_elements:
        td_elements = html_element_tree(to_string(tr_element)).xpath('//td')
        new_row = []
        for td_element in td_elements:
            data = u'\n'.join([x.strip()
                    for x in list(td_element.itertext(with_tail=False))])
            new_row.append(data)
        table_rows.append(new_row)

    # TODO: lxml -> unicode?
    # TODO: unescape

    header = [x.strip() for x in table_rows[0]]
    # TODO: test this feature
    new_header = []
    for index, field_name in enumerate(header):
        if not field_name:
            field_name = 'field_{}'.format(index)
        new_header.append(field_name)
    header = new_header

    table_rows = table_rows[1:]
    if fields is None:
        fields = detect_field_types(header, table_rows, encoding='utf-8')
    else:
        header = fields.keys()

    table = Table(fields=fields)
    for row in table_rows:
        table.append({field_name: value
                      for field_name, value in zip(header, row)})
    return table


# TODO: replace 'None' with '' on export_to_*
def export_to_html(table, filename=None, encoding='utf-8'):
    fields = table.fields.keys()
    result = [u'<table>', u'', u'  <thead>', u'    <tr>']
    header = [u'      <th>{}</th>'.format(field) for field in fields]
    result.extend(header)
    result.extend([u'    </tr>', u'  </thead>', u'', u'  <tbody>', u''])
    for index, row in enumerate(table, start=1):
        css_class = u'odd' if index % 2 == 1 else u'even'
        result.append(u'    <tr class="{}">'.format(css_class))
        for field in fields:
            value = table.fields[field].serialize(getattr(row, field))
            result.append(u'      <td>{}</td>'.format(value))
        result.extend([u'    </tr>', u''])
    result.extend([u'  </tbody>', u'</table>', u''])
    html = u'\n'.join(result)

    if filename is not None:
        with open(filename, 'w') as fobj:
            fobj.write(html.encode(encoding))
    else:
        return html
