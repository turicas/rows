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

import datetime
import decimal
import json

from rows.fields import DateField, DatetimeField, DecimalField, PercentField
from rows.plugins.utils import (create_table, get_filename_and_fobj,
                                prepare_to_export)


def import_from_json(filename_or_fobj, encoding='utf-8', *args, **kwargs):
    'Import data from a JSON file'

    kwargs['encoding'] = encoding
    filename, fobj = get_filename_and_fobj(filename_or_fobj)

    json_obj = json.load(fobj, encoding=encoding)
    field_names = json_obj[0].keys()
    table_rows = [[item[key] for key in field_names] for item in json_obj]

    data = [field_names] + table_rows
    meta = {'imported_from': 'json', 'filename': filename, }
    return create_table(data, meta=meta, *args, **kwargs)


def _convert(value, field_type, *args, **kwargs):
    if field_type in (DateField, DatetimeField, DecimalField, PercentField):
        value = field_type.serialize(value, *args, **kwargs)

    return value


def export_to_json(table, filename_or_fobj, encoding='utf-8', *args, **kwargs):
    # TODO: will work only if table.fields is OrderedDict

    _, fobj = get_filename_and_fobj(filename_or_fobj, mode='w')

    fields = table.fields
    prepared_table = prepare_to_export(table, *args, **kwargs)
    field_names = prepared_table.next()
    data = [{field_name: _convert(value, fields[field_name], *args, **kwargs)
             for field_name, value in zip(field_names, row)}
            for row in prepared_table]

    json.dump(data, fobj)
    fobj.flush()
    return fobj
