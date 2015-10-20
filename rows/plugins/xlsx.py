# coding: utf-8

from __future__ import unicode_literals

import datetime
import decimal

from openpyxl import load_workbook, Workbook
from rows.plugins.utils import create_table, get_filename_and_fobj
from rows import fields


def _read_row(sheet, row_pos, number_of_columns):
    return [cell_to_python(sheet.cell(row=row_pos, column=column))
            for column in range(1, number_of_columns)]


def cell_to_python(cell):
    '''Convert a PyOpenXL's `Cell` object to the corresponding Python object'''

    if cell.value == u"=TRUE()":
        return True
    elif cell.value == u"=FALSE()":
        return False
    elif cell.number_format.lower() == "yyyy-mm-dd":
        return str(cell.value).split(" 00:00:00")[0]
    elif cell.number_format.lower() == "yyyy-mm-dd hh:mm:ss":
        return str(cell.value)
    elif cell.number_format.endswith("%"):
        return "{}%".format(cell.value * 100)
    elif cell.value is None:
        return ''
    else:
        return cell.value


def import_from_xlsx(filename_or_fobj, sheet_name=None, sheet_index=0,
                     start_row=1, start_column=1, *args, **kwargs):
    filename, _ = get_filename_and_fobj(filename_or_fobj)
    workbook = load_workbook(filename)
    if sheet_name is None:
        sheet_name = workbook.sheetnames[sheet_index]
    sheet = workbook.get_sheet_by_name(sheet_name)

    # Get sheet header
    header = []
    max_columns = start_column
    current_header_value  = sheet.cell(row=start_row, column=max_columns).value
    while current_header_value:
        header.append(current_header_value)
        max_columns += 1
        current_header_value = sheet.cell(row=start_row,
                                          column=max_columns).value

    # Get sheet rows based on `max_columns` defined in 'get sheet header'
    row_pos = start_row + 1
    all_rows = []
    current_row = _read_row(sheet, row_pos, max_columns)
    while any(current_row):
        all_rows.append(current_row)
        row_pos += 1
        current_row = _read_row(sheet, row_pos, max_columns)

    metadata = {'imported_from': 'xlsx', 'filename': filename, }
    return create_table([header] + all_rows, meta=metadata, *args, **kwargs)


def _write_cell(sheet, row_index, col_index, value, field_type):
    '''Write a cell to the sheet, fixing value/formatting if needed'''

    cell = sheet.cell(row=row_index, column=col_index)
    cell.value = value

    if field_type is fields.PercentField:
        cell.number_format = '0.00%'
    elif field_type is fields.DatetimeField:
        cell.value = str(cell.value).split(' 00:00:00')[0]
        cell.number_format = 'YYYY-MM-DD'


def export_to_xlsx(table, filename_or_fobj, sheet_name='Sheet1'):

    filename, fobj = get_filename_and_fobj(filename_or_fobj, dont_open=True)
    workbook = Workbook()
    sheet = workbook.get_active_sheet()
    sheet.title = sheet_name
    field_names = [(index, field_name)
                   for index, field_name in enumerate(table.fields, start=1)]

    # Write header
    for col_index, field_name in field_names:
        _write_cell(sheet, 1, col_index, field_name, fields.TextField)

    # Write sheet rows
    for row_index, row_obj in enumerate(table, start=2):
        for col_index, field_name in field_names:
            _write_cell(sheet, row_index, col_index,
                        value=getattr(row_obj, field_name),
                        field_type=table.fields[field_name])

    workbook.save(filename)
