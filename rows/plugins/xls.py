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

import datetime
import os
from io import BytesIO

import xlrd
import xlwt

import rows.fields as fields
from rows.plugins.utils import create_table, prepare_to_export
from rows.utils import Source

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
    fields.DateField: xlwt.easyxf(num_format_str="yyyy-mm-dd"),
    fields.DatetimeField: xlwt.easyxf(num_format_str="yyyy-mm-dd hh:mm:ss"),
    fields.PercentField: xlwt.easyxf(num_format_str="0.00%"),
}


def _python_to_xls(field_types):
    def convert_value(field_type, value):
        data = {}
        if field_type in FORMATTING_STYLES:
            data["style"] = FORMATTING_STYLES[field_type]

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
        return [
            convert_value(field_type, value)
            for field_type, value in zip(field_types, row)
        ]

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
            return ""

    elif field_type is fields.DatetimeField:
        if value == 0.0:
            return None

        try:
            time_tuple = xlrd.xldate_as_tuple(value, sheet.book.datemode)
        except xlrd.xldate.XLDateTooLarge:
            return None
        value = field_type.serialize(datetime.datetime(*time_tuple))
        return value.split("T00:00:00")[0]

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

        if fmt.format_str.endswith("%"):
            # TODO: we may optimize this approach: we're converting to string
            # and the library is detecting the type when we could just say to
            # the library this value is PercentField

            if value is not None:
                try:
                    decimal_places = len(fmt.format_str[:-1].split(".")[-1])
                except IndexError:
                    decimal_places = 2
                return "{}%".format(str(round(value * 100, decimal_places)))
            else:
                return None

        elif type(value) == float and int(value) == value:
            return int(value)

        else:
            return value


def get_table_start(sheet):
    empty_cell_type = xlrd.empty_cell.ctype
    start_column, start_row = 0, 0
    for col in range(sheet.ncols):
        if any(cell for cell in sheet.col(col) if cell.ctype != empty_cell_type):
            start_column = col
            break
    for row in range(sheet.nrows):
        if any(cell for cell in sheet.row(row) if cell.ctype != empty_cell_type):
            start_row = row
            break
    return start_row, start_column


def sheet_names(filename_or_fobj):
    # TODO: setup/teardown must be methods of a class so we can reuse them
    source = Source.from_file(filename_or_fobj, mode="rb", plugin_name="xls")
    source.fobj.close()
    devnull = open(os.devnull, mode="w")
    book = xlrd.open_workbook(source.uri, formatting_info=False, logfile=devnull)
    result = book.sheet_names()
    del book
    devnull.close()
    return result


def import_from_xls(
    filename_or_fobj,
    sheet_name=None,
    sheet_index=0,
    start_row=None,
    start_column=None,
    end_row=None,
    end_column=None,
    *args,
    **kwargs
):
    """Return a rows.Table created from imported XLS file."""

    source = Source.from_file(filename_or_fobj, mode="rb", plugin_name="xls")
    source.fobj.close()
    devnull = open(os.devnull, mode="w")
    book = xlrd.open_workbook(source.uri, formatting_info=True, logfile=devnull)

    if sheet_name is not None:
        sheet = book.sheet_by_name(sheet_name)
    else:
        sheet = book.sheet_by_index(sheet_index)
    # TODO: may re-use Excel data types

    # Get header and rows
    # xlrd library reads rows and columns starting from 0 and ending on
    # sheet.nrows/ncols - 1. rows accepts the same pattern
    # The xlrd library reads rows and columns starting from 0 and ending on
    # sheet.nrows/ncols - 1. rows also uses 0-based indexes, so no
    # transformation is needed
    min_row, min_column = get_table_start(sheet)
    max_row, max_column = sheet.nrows - 1, sheet.ncols - 1
    # TODO: consider adding a parameter `ignore_padding=True` and when it's
    # True, consider `start_row` starting from `min_row` and `start_column`
    # starting from `min_col`.
    start_row = max(start_row if start_row is not None else min_row, min_row)
    end_row = min(end_row if end_row is not None else max_row, max_row)
    start_column = max(
        start_column if start_column is not None else min_column, min_column
    )
    end_column = min(end_column if end_column is not None else max_column, max_column)

    table_rows = [
        [
            cell_value(sheet, row_index, column_index)
            for column_index in range(start_column, end_column + 1)
        ]
        for row_index in range(start_row, end_row + 1)
    ]

    devnull.close()
    meta = {"imported_from": "xls", "source": source, "name": sheet.name}
    return create_table(table_rows, meta=meta, *args, **kwargs)


def export_to_xls(table, filename_or_fobj=None, sheet_name="Sheet1", *args, **kwargs):
    """Export the rows.Table to XLS file and return the saved file."""

    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet(sheet_name)

    prepared_table = prepare_to_export(table, *args, **kwargs)

    field_names = next(prepared_table)
    for column_index, field_name in enumerate(field_names):
        sheet.write(0, column_index, field_name)

    _convert_row = _python_to_xls([table.fields.get(field) for field in field_names])
    for row_index, row in enumerate(prepared_table, start=1):
        for column_index, (value, data) in enumerate(_convert_row(row)):
            sheet.write(row_index, column_index, value, **data)

    return_result = False
    if filename_or_fobj is None:
        filename_or_fobj = BytesIO()
        return_result = True

    source = Source.from_file(filename_or_fobj, mode="wb", plugin_name="xls")
    workbook.save(source.fobj)
    source.fobj.flush()

    if return_result:
        source.fobj.seek(0)
        result = source.fobj.read()
    else:
        result = source.fobj

    if source.should_close:
        source.fobj.close()

    return result
