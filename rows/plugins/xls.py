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

import datetime
from io import BytesIO

import xlrd
import xlwt

import rows.fields as fields
from rows.plugins.utils import (create_table, get_filename_and_fobj,
                                prepare_to_export)

CELL_TYPES = {
        xlrd.XL_CELL_BLANK: fields.TextField,
        xlrd.XL_CELL_DATE: fields.DatetimeField,
        xlrd.XL_CELL_ERROR: None,
        xlrd.XL_CELL_TEXT: fields.TextField,
        xlrd.XL_CELL_BOOLEAN: fields.BoolField,
        xlrd.XL_CELL_EMPTY: None,
        xlrd.XL_CELL_NUMBER: fields.FloatField,
}


# TODO: add more formatting styles for other types such as currency
# TODO: styles may be influenced by locale
FORMATTING_STYLES = {
        fields.DateField: xlwt.easyxf(num_format_str='yyyy-mm-dd'),
        fields.DatetimeField: xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss'),
        fields.PercentField: xlwt.easyxf(num_format_str='0.00%'),
}


def _python_to_xls(field_types):

    def convert_value(field_type, value):
        data = {}
        if field_type in FORMATTING_STYLES:
            data['style'] = FORMATTING_STYLES[field_type]

        if field_type in (
                fields.BinaryField,
                fields.BoolField,
                fields.DateField,
                fields.DatetimeField,
                fields.DecimalField,
                fields.FloatField,
                fields.IntegerField,
                fields.PercentField,
                fields.TextField,
        ):
            return value, data

        else:  # don't know this field
            return field_type.serialize(value), data

    def convert_row(row):
        return [convert_value(field_type, value)
                for field_type, value in zip(field_types, row)]

    return convert_row


def cell_value(sheet, row, col):
    """Return the cell value of the table passed by argument, based in row and column."""
    cell = sheet.cell(row, col)
    field_type = CELL_TYPES[cell.ctype]

    # TODO: this approach will not work if using locale
    value = cell.value

    if field_type is None:
        return None

    elif field_type is fields.TextField:
        if cell.ctype != xlrd.XL_CELL_BLANK:
            return value
        else:
            return ''

    elif field_type is fields.DatetimeField:
        time_tuple = xlrd.xldate_as_tuple(value, sheet.book.datemode)
        value = field_type.serialize(datetime.datetime(*time_tuple))
        return value.split('T00:00:00')[0]

    elif field_type is fields.BoolField:
        if value == 0:
            return False
        elif value == 1:
            return True

    elif cell.xf_index is None:
        return value  # TODO: test

    else:
        book = sheet.book
        xf = book.xf_list[cell.xf_index]
        fmt = book.format_map[xf.format_key]

        if fmt.format_str.endswith('%'):
            # TODO: we may optimize this approach: we're converting to string
            # and the library is detecting the type when we could just say to
            # the library this value is PercentField

            if value is not None:
                try:
                    decimal_places = len(fmt.format_str[:-1].split('.')[-1])
                except IndexError:
                    decimal_places = 2
                return '{}%'.format(str(round(value * 100, decimal_places)))
            else:
                return None

        elif type(value) == float and int(value) == value:
            return int(value)

        else:
            return value


def import_from_xls(filename_or_fobj, sheet_name=None, sheet_index=0,
                    start_row=0, start_column=0, end_row=None, end_column=None,
                    *args, **kwargs):
      """Return a rows.Table created from imported XLS file."""

    filename, _ = get_filename_and_fobj(filename_or_fobj, mode='rb')
    book = xlrd.open_workbook(filename, formatting_info=True)
    if sheet_name is not None:
        sheet = book.sheet_by_name(sheet_name)
    else:
        sheet = book.sheet_by_index(sheet_index)
    # TODO: may re-use Excel data types

    # Get header and rows
    # xlrd library reads rows and columns starting from 0 and ending on
    # sheet.nrows/ncols - 1. rows accepts the same pattern
    max_row, max_col = sheet.nrows - 1, sheet.ncols - 1
    column_range = range(start_column, (end_column or max_col) + 1)
    row_range = range(start_row, (end_row or max_row) + 1)
    table_rows = [[cell_value(sheet, row_index, column_index)
                   for column_index in column_range]
                  for row_index in row_range]

    meta = {'imported_from': 'xls',
            'filename': filename,
            'sheet_name': sheet.name, }
    return create_table(table_rows, meta=meta, *args, **kwargs)


def export_to_xls(table, filename_or_fobj=None, sheet_name='Sheet1', *args,
                  **kwargs):
    """Export the rows.Table to XLS file and return the saved file."""
    work_book = xlwt.Workbook()
    sheet = work_book.add_sheet(sheet_name)

    prepared_table = prepare_to_export(table, *args, **kwargs)

    field_names = next(prepared_table)
    for column_index, field_name in enumerate(field_names):
        sheet.write(0, column_index, field_name)

    _convert_row = _python_to_xls([table.fields.get(field)
                                   for field in field_names])
    for row_index, row in enumerate(prepared_table, start=1):
        for column_index, (value, data) in enumerate(_convert_row(row)):
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
