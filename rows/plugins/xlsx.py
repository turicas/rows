# coding: utf-8

from __future__ import unicode_literals

import datetime
import decimal

from io import BytesIO

from openpyxl import load_workbook, Workbook

from rows import fields
from rows.plugins.utils import (create_table, get_filename_and_fobj,
                                prepare_to_export)


def _get_cell_value(sheet, row_index, col_index):
    return sheet.cell(row=row_index + 1, column=col_index + 1).value


def _read_row(sheet, row_index, last_column):
    return [cell_to_python(sheet.cell(row=row_index + 1, column=column))
            for column in range(1, last_column + 2)]


def cell_to_python(cell):
    '''Convert a PyOpenXL's `Cell` object to the corresponding Python object'''

    if cell.value == u"=TRUE()":
        return True
    elif cell.value == u"=FALSE()":
        return False
    elif cell.number_format.lower() == "yyyy-mm-dd":
        return str(cell.value).split(" 00:00:00")[0]
    elif cell.number_format.lower() == "yyyy-mm-dd hh:mm:ss":
        return str(cell.value).split('.')[0]
    elif cell.number_format.endswith("%"):
        return "{}%".format(cell.value * 100)
    elif cell.value is None:
        return ''
    else:
        return cell.value


def import_from_xlsx(filename_or_fobj, sheet_name=None, sheet_index=0,
                     start_row=0, start_column=0, *args, **kwargs):
    workbook = load_workbook(filename_or_fobj)
    if sheet_name is None:
        sheet_name = workbook.sheetnames[sheet_index]
    sheet = workbook.get_sheet_by_name(sheet_name)

    # Get sheet header
    header = []
    last_column = start_column
    header_value = _get_cell_value(sheet, start_row, last_column)
    while header_value:
        header.append(header_value)
        last_column += 1
        header_value = _get_cell_value(sheet, start_row, last_column)
    last_column -= 1

    # Get sheet rows based on `last_column` defined in 'get sheet header'
    row_pos = start_row + 1
    all_rows = []
    row = _read_row(sheet, row_pos, last_column)
    while any(row):
        all_rows.append(row)
        row_pos += 1
        row = _read_row(sheet, row_pos, last_column)

    filename, _ = get_filename_and_fobj(filename_or_fobj, dont_open=True)
    metadata = {'imported_from': 'xlsx', 'filename': filename, }
    return create_table([header] + all_rows, meta=metadata, *args, **kwargs)


FORMATTING_STYLES = {
        fields.DateField: 'YYYY-MM-DD',
        fields.DatetimeField: 'YYYY-MM-DD HH:MM:SS',
        fields.PercentField: '0.00%',
}


def _python_to_xlsx(field_types):

    def convert_value(field_type, value):

        number_format = FORMATTING_STYLES.get(field_type, None)

        if field_type not in (
                fields.BoolField,
                fields.DateField,
                fields.DatetimeField,
                fields.DecimalField,
                fields.FloatField,
                fields.IntegerField,
                fields.PercentField,
                fields.TextField,
        ):
            # BinaryField, DatetimeField, JSONField or unknown
            value = field_type.serialize(value)

        return value, number_format

    def convert_row(row):
        return [convert_value(field_type, value)
                for field_type, value in zip(field_types, row)]

    return convert_row


def export_to_xlsx(table, filename_or_fobj=None, sheet_name='Sheet1', *args,
                   **kwargs):

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    prepared_table = prepare_to_export(table, *args, **kwargs)

    # Write header
    field_names = prepared_table.next()
    for col_index, field_name in enumerate(field_names):
        cell = sheet.cell(row=1, column=col_index + 1)
        cell.value = field_name

    # Write sheet rows
    _convert_row = _python_to_xlsx(map(table.fields.get, field_names))
    for row_index, row in enumerate(prepared_table, start=1):
        for col_index, (value, number_format) in enumerate(_convert_row(row)):
            cell = sheet.cell(row=row_index + 1, column=col_index + 1)
            cell.value = value
            if number_format is not None:
                cell.number_format = number_format

    if filename_or_fobj is not None:
        _, fobj = get_filename_and_fobj(filename_or_fobj, mode='wb')
        workbook.save(fobj)
        fobj.flush()
        return fobj
    else:
        fobj = BytesIO()
        workbook.save(fobj)
        fobj.seek(0)
        result = fobj.read()
        fobj.close()
        return result
