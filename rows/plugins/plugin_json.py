# coding: utf-8

# Copyright 2014-2016 Álvaro Justen <https://github.com/turicas/rows/>
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
import decimal
import json

from rows import fields
from rows.plugins.utils import (create_table, export_data,
                                get_filename_and_fobj, prepare_to_export)


def import_from_json(filename_or_fobj, encoding='utf-8', *args, **kwargs):
    'Import data from a JSON file'

    filename, fobj = get_filename_and_fobj(filename_or_fobj, mode='rb')

    json_obj = json.load(fobj, encoding=encoding)
    field_names = json_obj[0].keys()
    table_rows = [[item[key] for key in field_names] for item in json_obj]

    data = [field_names] + table_rows
    meta = {'imported_from': 'json',
            'filename': filename,
            'encoding': encoding,}
    return create_table(data, meta=meta, *args, **kwargs)


def _convert(value, field_type, *args, **kwargs):
    if value is None or field_type in (
                fields.BinaryField,
                fields.BoolField,
                fields.FloatField,
                fields.IntegerField,
                fields.JSONField,
                fields.TextField,
    ):
        # If the field_type is one of those, the value can be passed directly
        # to the JSON encoder
        return value
    else:
        # The field type is not represented natively in JSON, then it needs to
        # be serialized (converted to a string)
        return field_type.serialize(value, *args, **kwargs)


def export_to_json(table, filename_or_fobj=None, encoding='utf-8', indent=None,
                   *args, **kwargs):
    # TODO: will work only if table.fields is OrderedDict

    fields = table.fields
    prepared_table = prepare_to_export(table, *args, **kwargs)
    field_names = next(prepared_table)
    data = [{field_name: _convert(value, fields[field_name], *args, **kwargs)
             for field_name, value in zip(field_names, row)}
            for row in prepared_table]

    result = json.dumps(data, indent=indent)
    if indent is not None:
        # clean up empty spaces at the end of lines
        result = '\n'.join(line.rstrip() for line in result.splitlines())

    return export_data(filename_or_fobj, result)
