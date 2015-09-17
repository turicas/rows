# coding: utf-8

import datetime
import decimal

from openpyxl import load_workbook, Workbook
from rows.plugins.utils import create_table, get_filename_and_fobj


def import_from_xlsx(filename_or_fobj, sheet_name=None, sheet_index=0,
        start_row=1, start_column=1, *args, **kwargs):
    filename, _ = get_filename_and_fobj(filename_or_fobj)
    #Load the workbook
    workbook = load_workbook(filename)
    #Get the desired sheet
    if sheet_name is not None:
        worksheet = workbook.get_sheet_by_name(sheet_name)
    else:
        #get the sheet by the index using all sheet names
        worksheet = workbook.get_sheet_by_name(workbook.get_sheet_names()[sheet_index])

    #Get the header
    header = []
    col_pos = start_column
    current_header_value  = worksheet.cell(row=1, column=col_pos).value
    header.append(current_header_value)
    while current_header_value:
        col_pos += 1
        current_header_value = worksheet.cell(row=start_row, column=col_pos).value
        header.append(current_header_value)

    #Remove the last header. Is a None
    header = filter(lambda v: v is not None, header)
    #Get the rows content
    row_pos = start_row + 1
    current_row = [validate_cell_value(worksheet.cell(row=row_pos, column=col)).value for col in
            xrange(1, col_pos)]
    all_rows = [current_row, ]
    while any(current_row):
        row_pos += 1
        current_row = [validate_cell_value(worksheet.cell(row=row_pos, column=col)).value for col in
                xrange(1, col_pos)]
        all_rows.append(current_row)

    #Remove the last row with Nones
    all_rows = filter(lambda v: any(v), all_rows)
    metadata = {'imported_from': 'xlsx', 'filename': filename}
    return create_table([header] + all_rows, meta=metadata, *args, **kwargs)

def export_to_xlsx(table, filename_or_fobj, sheet_name='Sheet'):

    filename, fobj = get_filename_and_fobj(filename_or_fobj, mode='wb')
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
    if cell_obj.value == u"=TRUE()":
        cell_obj.value = True
    elif cell_obj.value == u"=FALSE()":
        cell_obj.value = False
    elif cell_obj.style.number_format == "YYYY/MM/DD" or\
            cell_obj.style.number_format == "yyyy-mm-dd":
        cell_obj.value = str(cell_obj.value).split(" 00:00:00")[0]
    elif cell_obj.style.number_format == "0.00%":
        cell_obj.value = "{}%".format(cell_obj.value * 100)
    elif cell_obj.value is None:
        cell_obj.value = ''
    return cell_obj

def correct_field_types(cell_obj, current_field_type):
    """
    Make some correctios to export
    """
    if current_field_type.TYPE == decimal.Decimal:
        cell_obj.number_format = "0.00%"
    elif current_field_type.TYPE == datetime.datetime:
        cell_obj.value = str(cell_obj.value).split(" 00:00:00")[0]
        cell_obj.number_format = "YYYY/MM/DD"
    return cell_obj
