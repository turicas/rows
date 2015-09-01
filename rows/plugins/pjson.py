# coding: utf-8

# Copyright 2014-2015 Álvaro Justen <https://github.com/turicas/rows/>
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

import json
import rows
from rows.utils import create_table, get_filename_and_fobj


def import_from_json(
    filename_or_fobj, force_headers=None, encoding='utf-8',
    *args, **kwargs
):
    'Import data from a JSON file'

    filename, fobj = get_filename_and_fobj(filename_or_fobj)
    kwargs['encoding'] = encoding
    json_obj = json.loads(fobj.read(), encoding=encoding)
    force_headers = json_obj[0].keys()
    json_reader = [[item[key] for key in force_headers] for item in json_obj]

    meta = {'imported_from': 'json', 'filename': filename, }
    return create_table(
        json_reader, meta=meta, force_headers=force_headers, *args, **kwargs
    )


def serialize_json(table, *args, **kwargs):
    fields = table.fields
    fields_items = fields.items()
    for row in table:
        rec = dict()
        for field_name, field_type in fields_items:
            val = getattr(row, field_name)
            if (
                field_type in (
                    rows.fields.DateField,
                    rows.fields.DatetimeField
                )
            ):
                value = field_type.serialize(
                    val, *args, **kwargs
                )
            elif field_type == rows.fields.PercentField:
                value = str(val * 100).strip('0').strip('.').strip(',') + '%'
            else:
                value = val
            rec[field_name] = value
        yield rec


def export_to_json(
    table, filename_or_fobj, encoding='utf-8',
    *args, **kwargs
):
    # TODO: will work only if table.fields is OrderedDict

    filename, fobj = get_filename_and_fobj(filename_or_fobj, mode='w')

    ilist = serialize_json(table, encoding=encoding, *args, **kwargs)

    fobj.write(json.dumps(list(ilist), encoding=encoding))

    fobj.flush()
    return fobj
