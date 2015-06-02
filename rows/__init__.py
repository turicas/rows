# coding: utf-8

import locale

from collections import Mapping, OrderedDict, namedtuple
from contextlib import contextmanager
from unicodedata import normalize

import fields


SLUG_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'


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

def _get_string(value):
    if isinstance(value, (unicode, str)):
        return value
    else:
        return str(value)

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

        if not [value for value in column_data if _get_string(value).strip()]:
            # all rows with an empty field -> str (can't identify)
            identified_type = fields.StringField
        else:
            # ok, let's try to identify the type of this column by
            # converting every value in the sample
            for value in column_data:
                if value is None or not _get_string(value).strip():
                    # TODO: should test 'value in NULL'?
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

def slug(text, encoding=None, separator='_', permitted_chars=SLUG_CHARS,
         replace_with_separator=' -_'):
    if isinstance(text, str):
        text = text.decode(encoding or 'ascii')
    clean_text = text.strip()
    for char in replace_with_separator:
        clean_text = clean_text.replace(char, separator)
    double_separator = separator + separator
    while double_separator in clean_text:
        clean_text = clean_text.replace(double_separator, separator)
    ascii_text = normalize('NFKD', clean_text).encode('ascii', 'ignore')
    strict_text = [x for x in ascii_text if x in permitted_chars]

    return ''.join(strict_text)

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
