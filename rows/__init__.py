# coding: utf-8

import locale
import types

from collections import Mapping, OrderedDict, defaultdict, namedtuple
from contextlib import contextmanager
from unicodedata import normalize

import rows.fields

from rows.utils import as_string, is_null, slug


class Table(object):

    def __init__(self, fields):
        # TODO: should we really use OrderedDict here?
        # TODO: should use slug on each field name automatically or inside each
        #       plugin?
        self.fields = OrderedDict(fields)
        self.field_names = self.fields.keys()
        self.field_types = self.fields.values()

        # TODO: should be able to customize row return type (namedtuple, dict
        #       etc.)
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

    def __radd__(self, other):
        if other == 0:
            return self
        raise ValueError()


    def __add__(self, other):
        if other == 0:
            return self

        if type(self) != type(other) or self.fields != other.fields:
            raise ValueError('Tables have incompatible fields')

        table = Table(fields=self.fields)
        for row in self:
            table.append({field: getattr(row, field) for field in row._fields})
        for row in other:
            table.append({field: getattr(row, field) for field in row._fields})
        return table


def detect_field_types(field_names, sample_rows, *args, **kwargs):
    """Where the magic happens"""

    # TODO: should support receiving unicode objects directly
    # TODO: should expect data in unicode or will be able to use binary data?
    number_of_fields = len(field_names)
    columns = zip(*[row for row in sample_rows
                        if len(row) == number_of_fields])
    # TODO: raise a ValueError exception instead
    assert len(columns) == len(field_names)

    available_types = list([getattr(fields, name)
                            for name in rows.fields.__all__
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
            identified_type = rows.fields.ByteField
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
    if type(name) is types.UnicodeType:
        name = name.split('.')
    locale.setlocale(category, name)
    rows.fields.SHOULD_NOT_USE_LOCALE = False
    try:
        yield
    finally:
        locale.setlocale(category, old_name)
    rows.fields.SHOULD_NOT_USE_LOCALE = True


def join(keys, tables):
    '''Merge a list of `row.Table` objects using `keys` to group rows'''

    if isinstance(keys, (str, unicode)):
        keys = (keys, )

    data = defaultdict(OrderedDict)
    fields = OrderedDict()
    for table in tables:
        fields.update(table.fields)

        for row in table:
            row_key = tuple([getattr(row, key) for key in keys])
            data[row_key].update({field: getattr(row, field)
                                  for field in row._fields})

    merged = Table(fields=fields)
    for row in data.values():
        for field in fields:
            if field not in row:
                row[field] = None
        merged.append(row)

    return merged

# CSV plugin

import unicodecsv
import csv


def import_from_csv(filename, fields=None, delimiter=',', quotechar='"',
                    encoding='utf-8'):
    'Import data from a CSV file'
    # TODO: add auto_detect_types=True parameter
    # this import will be moved in the future (to another module, actually)

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
    # TODO: may use unicodecsv here

    with open(filename, mode='w') as fobj:
        fields = table.fields.items()
        csv_writer = csv.writer(fobj)
        csv_writer.writerow([field.encode(encoding) for field, _ in fields])

        for row in table:
            # TODO: will work only if table.fields is OrderedDict
            csv_writer.writerow([type_.serialize(getattr(row, field),
                                                 encoding=encoding)
                                 for field, type_ in fields])


# XLS plugin

import xlrd
import xlwt


def import_from_xls(filename, fields=None, sheet_name=None, sheet_index=0,
                    start_row=0, start_column=0):

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


def export_to_xls(table, filename, sheet_name='Sheet1'):
    work_book = xlwt.Workbook()
    sheet = work_book.add_sheet(sheet_name)
    fields = [(index, field_name)
              for index, field_name in enumerate(table.fields)]

    for index, field_name in fields:
        sheet.write(0, index, field_name)
    for row_index, row in enumerate(table, start=1):
        for column_index, field_name in fields:
            sheet.write(row_index, column_index, getattr(row, field_name))

    work_book.save(filename)

# HTML plugin

import HTMLParser

from lxml.etree import HTML as html_element_tree, tostring as to_string


html_parser = HTMLParser.HTMLParser()

def import_from_html(html, fields=None, table_index=0, ignore_colspan=True,
                     force_headers=None):
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
        # TODO: test 'td' and 'th'
        td_elements = html_element_tree(to_string(tr_element)).xpath('//td')
        td_elements += html_element_tree(to_string(tr_element)).xpath('//th')
        new_row = []
        for td_element in td_elements:
            data = u'\n'.join([x.strip()
                    for x in list(td_element.itertext(with_tail=False))])
            new_row.append(data)
        table_rows.append(new_row)

    max_columns = max(len(row) for row in table_rows)
    if ignore_colspan:
        table_rows = filter(lambda row: len(row) == max_columns, table_rows)

    # TODO: lxml -> unicode?
    # TODO: unescape

    if fields is not None:
        assert len(fields) == max_columns
        header = [slug(field_name) for field_name in fields.keys()]
    else:
        if force_headers is None:
            header = [x.strip() for x in table_rows[0]]
            # TODO: test this feature
            new_header = []
            for index, field_name in enumerate(header):
                if not field_name:
                    field_name = 'field_{}'.format(index)
                new_header.append(field_name)
            header = [slug(field_name) for field_name in new_header]
            table_rows = table_rows[1:]
        else:
            header = force_headers
        fields = detect_field_types(header, table_rows, encoding='utf-8')

    table = Table(fields=fields)
    for row in table_rows:
        table.append({field_name: value.strip()
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
            value = table.fields[field].serialize(getattr(row, field),
                                                  encoding=encoding)
            result.append(u'      <td>')
            result.append(value)
            result.append(u'</td>')
        result.extend([u'    </tr>', u''])
    result.extend([u'  </tbody>', u'</table>', u''])
    new_result = []
    for x in result:
        if isinstance(x, unicode):
            x = x.encode(encoding)
        new_result.append(x)
    html = u'\n'.encode(encoding).join(new_result)

    if filename is not None:
        with open(filename, 'w') as fobj:
            fobj.write(html)
    else:
        return html


# Example plugin: uwsgi log

from collections import OrderedDict

import datetime
import re


REGEXP_UWSGI_LOG = re.compile(r'\[pid: ([0-9]+)\|app: [0-9]+\|req: '
                              r'[0-9]+/[0-9]+\] '
                              r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+) .+ \[(.+)\] '
                              r'([^ ]+) (.+) => generated .+ in ([0-9]+) '
                              r'micros \(HTTP/([^ ]+) ([^)]+)\)')
UWSGI_FIELDS = OrderedDict([('pid', rows.fields.IntegerField),
                            ('ip', rows.fields.UnicodeField),
                            ('datetime', rows.fields.DatetimeField),
                            ('http_verb', rows.fields.UnicodeField),
                            ('http_path', rows.fields.UnicodeField),
                            ('generation_time', rows.fields.FloatField),
                            ('http_version', rows.fields.FloatField),
                            ('http_status', rows.fields.IntegerField)])
UWSGI_DATETIME_FORMAT = '%a %b %d %H:%M:%S %Y'


def import_from_uwsgi_log(filename):
    strptime = datetime.datetime.strptime
    fields = UWSGI_FIELDS.keys()
    table = Table(fields=UWSGI_FIELDS)
    with open(filename) as fobj:
        for line in fobj:
            result = REGEXP_UWSGI_LOG.findall(line)
            if result:
                data = list(result[0])
                # Convert datetime
                data[2] = strptime(data[2], UWSGI_DATETIME_FORMAT)
                # Convert generation time (micros -> seconds)
                data[5] = float(data[5]) / 1000000
                table.append({field_name: value
                              for field_name, value in zip(fields, data)})
    return table
