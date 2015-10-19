# coding: utf-8

# Copyright 2014-2015 Álvaro Justen <https://github.com/turicas/rows/>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import datetime
from io import BytesIO

import xlrd
import xlwt

import rows.fields as fields

from rows.plugins.utils import (create_table, get_filename_and_fobj,
                                prepare_to_export)


CELL_TYPES = {xlrd.XL_CELL_BLANK: fields.BinaryField,
              xlrd.XL_CELL_DATE: fields.DatetimeField,
              xlrd.XL_CELL_ERROR: None,
              xlrd.XL_CELL_TEXT: fields.TextField,
              xlrd.XL_CELL_BOOLEAN: fields.BoolField,
              xlrd.XL_CELL_EMPTY: None,
              xlrd.XL_CELL_NUMBER: fields.FloatField,}

def cell_value(sheet, row, col):
    try:
        cell = sheet.cell(row, col)
    except IndexError:
        return None

    field_type = CELL_TYPES[cell.ctype]
    if field_type is None:
        return None

    # TODO: this approach will not work if using locale
    value = cell.value
    if field_type is fields.DatetimeField:
        time_tuple = xlrd.xldate_as_tuple(value, sheet.book.datemode)
        value = field_type.serialize(datetime.datetime(*time_tuple))
        return value.split('T00:00:00')[0]
    else:
        book = sheet.book
        xf = book.xf_list[cell.xf_index]
        fmt = book.format_map[xf.format_key]
        if fmt.format_str.endswith('%'):
            return '{}%'.format(cell.value * 100)
        elif type(value) == float and int(value) == value:
            return int(value)
        else:
            return value

def import_from_xls(filename_or_fobj, sheet_name=None, sheet_index=0,
                    start_row=0, start_column=0, *args, **kwargs):

    filename, _ = get_filename_and_fobj(filename_or_fobj)
    book = xlrd.open_workbook(filename, formatting_info=True)
    if sheet_name is not None:
        sheet = book.sheet_by_name(sheet_name)
    else:
        sheet = book.sheet_by_index(sheet_index)
    # TODO: may re-use Excel data types

    # Get field names
    # TODO: may use sheet.col_values or even sheet.ncols
    column_count = 0
    header = []
    column_value = cell_value(sheet, start_row, start_column + column_count)
    while column_value:
        header.append(column_value)
        column_count += 1
        column_value = cell_value(sheet, start_row,
                                  start_column + column_count)

    # Get sheet rows
    # TODO: may use sheel.col_slice or even sheet.nrows
    table_rows = []
    row_count = 0
    start_row += 1
    cell_is_empty = False
    while not cell_is_empty:
        row = [cell_value(sheet, start_row + row_count,
                          start_column + column_index)
               for column_index in range(column_count)]
        cell_is_empty = not any(row)
        if not cell_is_empty:
            table_rows.append(row)
            row_count += 1

    meta = {'imported_from': 'xls', 'filename': filename,}
    return create_table([header] + table_rows, meta=meta, *args, **kwargs)


# TODO: add more formatting styles for other types such as currency
# TODO: styles may be influenced by locale
FORMATTING_STYLES = {fields.DateField: xlwt.easyxf(num_format_str='yyyy-mm-dd'),
                     fields.DatetimeField: xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss'),
                     fields.PercentField: xlwt.easyxf(num_format_str='0.00%'),}

def export_to_xls(table, filename_or_fobj=None, sheet_name='Sheet1', *args,
                  **kwargs):

    work_book = xlwt.Workbook()
    sheet = work_book.add_sheet(sheet_name)

    prepared_table = prepare_to_export(table, *args, **kwargs)

    field_names = prepared_table.next()
    for column_index, field_name in enumerate(field_names):
        sheet.write(0, column_index, field_name)

    for row_index, row in enumerate(prepared_table, start=1):
        for column_index, (field_name, value) in \
                enumerate(zip(field_names, row)):
            field_type = table.fields[field_name]
            data = {}
            if field_type in FORMATTING_STYLES:
                data['style'] = FORMATTING_STYLES[field_type]
            sheet.write(row_index, column_index, value, **data)

    if filename_or_fobj is not None:
        _, fobj = get_filename_and_fobj(filename_or_fobj, mode='wb')
        work_book.save(fobj)
        fobj.flush()
        return fobj
    else:
        fobj = BytesIO()
        work_book.save(fobj)
        fobj.seek(0)
        result = fobj.read()
        fobj.close()
        return result
