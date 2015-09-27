# coding: utf-8

import datetime
import decimal

from openpyxl import load_workbook, Workbook
from rows.plugins.utils import create_table, get_filename_and_fobj
from rows import fields


def import_from_xlsx(filename_or_fobj, sheet_name='Sheet1', sheet_index=0,
                     start_row=1, start_column=1, *args, **kwargs):
    filename, _ = get_filename_and_fobj(filename_or_fobj)
    workbook = load_workbook(filename)
    if sheet_name is not None:
        worksheet = workbook.get_sheet_by_name(sheet_name)
    else:
        worksheet = workbook.get_sheet_by_name(
                workbook.get_sheet_names()[sheet_index])

    # Get the header
    header = []
    col_pos = start_column
    current_header_value  = worksheet.cell(row=1, column=col_pos).value
    header.append(current_header_value)
    while current_header_value:
        col_pos += 1
        current_header_value = worksheet.cell(row=start_row, column=col_pos).value
        header.append(current_header_value)

    # Remove the last header. Is a None
    header = filter(lambda v: v is not None, header)

    # Get the rows content
    get_cell_value = lambda row, col: validate_cell_value(worksheet.cell(row=row, column=col))
    get_row = lambda row, colsize: [validate_cell_value(worksheet.cell(row=row, column=col))
                                    for col in range(1, colsize)]
    row_pos = start_row + 1
    current_row = get_row(row_pos, col_pos)
    all_rows = [current_row, ]
    while any(current_row):
        row_pos += 1
        current_row = get_row(row_pos, col_pos)
        all_rows.append(current_row)

    # Remove the last row with Nones
    all_rows = filter(lambda v: any(v), all_rows)
    metadata = {'imported_from': 'xlsx', 'filename': filename}
    return create_table([header] + all_rows, meta=metadata, *args, **kwargs)


def export_to_xlsx(table, filename_or_fobj, sheet_name='Sheet'):

    filename, fobj = get_filename_and_fobj(filename_or_fobj, dont_open=True)
    workbook = Workbook()
    worksheet = workbook.create_sheet(title=sheet_name)
    fields = [(index, field_name)
            for index, field_name in enumerate(table.fields)]
    for index, field_name in fields:
        worksheet.cell(row=1, column=index + 1, value=field_name)

    for row_index, row_obj in enumerate(table, start=2):
        for col_index, field_obj in fields:
            value = getattr(row_obj, field_obj)
            current_field_type = table.fields[field_obj]
            cell_obj = worksheet.cell(row=row_index, column=col_index + 1)
            cell_obj.value = value
            cell_obj = correct_field_types(cell_obj, current_field_type)

    workbook.save(filename)

def validate_cell_value(cell_obj):
    """
    For some reason the openpyxl is not recognizing boolean type.
    It returns True or False but as string.
    """
    #TODO: Check if all cases of xlsx types are treated
    if cell_obj.value == u"=TRUE()":
        result = True
    elif cell_obj.value == u"=FALSE()":
        result = False
    elif cell_obj.style.number_format.lower() == "yyyy-mm-dd":
        result = str(cell_obj.value).split(" 00:00:00")[0]
    elif cell_obj.style.number_format.lower() == "yyyy-mm-dd hh:mm:ss":
        result = str(cell_obj.value)
    elif cell_obj.style.number_format.endswith("%"):
        result = "{}%".format(cell_obj.value * 100)
    elif cell_obj.value is None:
        result = ''
    else:
        result = cell_obj.value
    return result

def correct_field_types(cell_obj, current_field_type):
    """
    Make some correctios to export
    """
    #TODO: compare xlsx type with rows field types
    if current_field_type is fields.PercentField:
        cell_obj.number_format = "0.00%"
    elif current_field_type is fields.DatetimeField:
        cell_obj.value = str(cell_obj.value).split(" 00:00:00")[0]
        cell_obj.number_format = "YYYY/MM/DD"
    return cell_obj
