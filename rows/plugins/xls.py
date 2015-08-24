# coding: utf-8

from __future__ import unicode_literals

import datetime

import xlrd
import xlwt

from rows.fields import detect_types
from rows.table import Table


# TODO: add more formatting styles for other types such as percent, currency
# etc.
# TODO: styles may be influenced by locale
FORMATTING_STYLES = {
        datetime.date: xlwt.easyxf(num_format_str='yyyy-mm-dd'),
        datetime.datetime: xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss'), }

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

    # could use decorator from here

    if fields is None:
        fields = detect_types(header, table_rows, encoding='utf-8')
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
            value = getattr(row, field_name)
            data = {}
            if type(value) in FORMATTING_STYLES:
                data['style'] = FORMATTING_STYLES[type(value)]
            sheet.write(row_index, column_index, value, **data)

    work_book.save(filename)
