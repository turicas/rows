# coding: utf-8

# Copyright 2016 Álvaro Justen <https://github.com/turicas/rows/>
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

import codecs

from io import BytesIO

import row

import rows

from rows.plugins.utils import create_table, get_filename_and_fobj, serialize


ROW_TO_ROWS = {
        'bool': rows.fields.BoolField,
        'int': rows.fields.IntegerField,
        'float': rows.fields.FloatField,
        'date': rows.fields.DateField,
        'datetime': rows.fields.DatetimeField,
        'text': rows.fields.TextField,
        'binary': rows.fields.BinaryField,
}
ROWS_TO_ROW = {
        rows.fields.BoolField: 'bool',
        rows.fields.IntegerField: 'int',
        rows.fields.FloatField: 'float',
        rows.fields.DateField: 'date',
        rows.fields.DatetimeField: 'datetime',
        rows.fields.TextField: 'text',
        rows.fields.BinaryField: 'binary',
}


def _convert_fields(data):
    result = data.copy()
    for key, value in data.items():
        result[key] = ROW_TO_ROWS[value]
    return result


def import_from_row(filename, *args, **kwargs):
    'Import data from a row file'

    fobj = codecs.open(filename, 'rb')
    reader = row.Reader(fobj)
    meta = {'imported_from': 'row', 'filename': filename,}
    fields = _convert_fields(reader.fields)

    return create_table(reader, meta=meta, fields=fields, skip_header=False,
                        *args, **kwargs)


def export_to_row(table, filename_or_fobj=None, *args, **kwargs):

    if filename_or_fobj is not None:
        _, fobj = get_filename_and_fobj(filename_or_fobj, mode='w')
    else:
        fobj = BytesIO()

    fieldnames = table.fields.keys()
    fieldtypes = [ROWS_TO_ROW[fieldtype]
                  for fieldtype in table.fields.values()]
    writer = row.Writer(fobj, fieldnames, fieldtypes)
    data = serialize(table, *args, **kwargs)
    next(data)  # consume the header
    for line in data:
        writer.writerow(line)

    if filename_or_fobj is not None:
        fobj.flush()
        return fobj
    else:
        fobj.seek(0)
        result = fobj.read()
        fobj.close()
        return result
