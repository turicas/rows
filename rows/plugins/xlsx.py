# coding: utf-8

from __future__ import unicode_literals

import datetime
import decimal

from io import BytesIO

from openpyxl import load_workbook, Workbook

from rows import fields
from rows.plugins.utils import (create_table, get_filename_and_fobj,
                                prepare_to_export)


def _cell_to_python(cell):
    '''Convert a PyOpenXL's `Cell` object to the corresponding Python object'''

    value = cell.value

    if value == '=TRUE()':
        return True

    elif value == '=FALSE()':
        return False

    elif cell.number_format.lower() == 'yyyy-mm-dd':
        return str(value).split(' 00:00:00')[0]

    elif cell.number_format.lower() == 'yyyy-mm-dd hh:mm:ss':
        return str(value).split('.')[0]

    elif cell.number_format.endswith('%'):
        return '{}%'.format(value * 100) if value else None

    elif value is None:
        return ''

    else:
        return value


def import_from_xlsx(filename_or_fobj, sheet_name=None, sheet_index=0,
                     start_row=0, start_column=0, *args, **kwargs):
    workbook = load_workbook(filename_or_fobj)
    if sheet_name is None:
        sheet_name = workbook.sheetnames[sheet_index]
    sheet = workbook.get_sheet_by_name(sheet_name)

    start_row, end_row = max(start_row, sheet.min_row), sheet.max_row
    start_col, end_col = max(start_column, sheet.min_column), sheet.max_column
    table_rows = [[_cell_to_python(sheet.cell(row=row_index, column=col_index))
                   for col_index in range(start_col, end_col + 1)]
                  for row_index in range(start_row, end_row + 1)]

    filename, _ = get_filename_and_fobj(filename_or_fobj, dont_open=True)
    metadata = {'imported_from': 'xlsx', 'filename': filename, }
    return create_table(table_rows, meta=metadata, *args, **kwargs)


FORMATTING_STYLES = {
        fields.DateField: 'YYYY-MM-DD',
        fields.DatetimeField: 'YYYY-MM-DD HH:MM:SS',
        fields.PercentField: '0.00%',
}


def _python_to_cell(field_types):

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
    _convert_row = _python_to_cell(map(table.fields.get, field_names))
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
