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

import six
import yaml

from rows import fields
from rows.plugins.utils import (create_table, export_data,
                                get_filename_and_fobj, prepare_to_export)


def import_from_yaml(filename_or_fobj, encoding='utf-8', *args, **kwargs):
    '''Import a YAML file or file-like object into a `rows.Table`

    If a file-like object is provided it MUST be open in text (non-binary) mode
    on Python 3 and could be open in both binary or text mode on Python 2.
    '''

    filename, fobj = get_filename_and_fobj(filename_or_fobj)

    yaml_obj = yaml.load(fobj)
    field_names = list(yaml_obj[0].keys())
    table_rows = [[item[key] for key in field_names] for item in yaml_obj]

    meta = {
        'imported_from': 'yaml',
        'filename': filename,
        'encoding': encoding
    }
    return create_table([field_names] + table_rows, meta=meta, *args, **kwargs)


def _convert(value, field_type, *args, **kwargs):
    if value is None or field_type in (
            fields.BinaryField,
            fields.BoolField,
            fields.FloatField,
            fields.IntegerField,
            fields.JSONField,
            fields.TextField,):
        return value
    else:
        return field_type.serialize(value, *args, **kwargs)


def export_to_yaml(table, filename_or_fobj=None, encoding='utf-8', indent=None,
                   *args, **kwargs):
    '''Export a `rows.Table` to a YAML file or file-like object
    '''

    all_fields = table.fields
    prepared_table = prepare_to_export(table, *args, **kwargs)
    field_names = next(prepared_table)
    data = [{field_name: _convert(value,
                                  all_fields[field_name],
                                  *args,
                                  **kwargs)
             for field_name, value in zip(field_names, row)}
            for row in prepared_table]

    result = yaml.dump(data, indent=indent)
    if type(result) is six.text_type:
        result = result.encode(encoding)

    if indent is not None:
        # clean up empty spaces at the end of lines
        result = b'\n'.join(line.rstrip() for line in result.splitlines())

    return export_data(filename_or_fobj, result, mode='wb')
