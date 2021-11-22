# coding: utf-8

# Copyright 2014-2019 Álvaro Justen <https://github.com/turicas/rows/>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import json
from io import BytesIO

import six

from rows import fields
from rows.plugins.utils import (
    create_table,
    prepare_to_export,
)
from rows.utils import Source


def import_from_json(filename_or_fobj, encoding="utf-8", *args, **kwargs):
    """Import a JSON file or file-like object into a `rows.Table`.

    If a file-like object is provided it MUST be open in text (non-binary) mode
    on Python 3 and could be open in both binary or text mode on Python 2.
    """

    source = Source.from_file(filename_or_fobj, mode="rb", plugin_name="json", encoding=encoding)

    # JSON should always use UTF-8, UTF-16 or UTF-32 encodings.
    json_obj = json.load(source.fobj)
    field_names = []
    for row in json_obj:
        for key in row.keys():
            if key not in field_names:
                field_names.append(key)
    table_rows = [[item.get(key) for key in field_names] for item in json_obj]

    meta = {"imported_from": "json", "source": source}
    return create_table([field_names] + table_rows, meta=meta, *args, **kwargs)


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


def export_to_json(table, filename_or_fobj=None, encoding="utf-8", indent=None, *args, **kwargs):
    """Export a `rows.Table` to a JSON file or file-like object.

    If a file-like object is provided it MUST be open in binary mode (like in
    `open('myfile.json', mode='wb')`).
    """

    return_data, should_close = False, None
    if filename_or_fobj is None:
        filename_or_fobj = BytesIO()
        return_data = should_close = True

    source = Source.from_file(
        filename_or_fobj,
        plugin_name="json",
        mode="wb",
        encoding=encoding,
        should_close=should_close,
    )

    # TODO: will work only if table.fields is OrderedDict
    fields = table.fields
    prepared_table = prepare_to_export(table, *args, **kwargs)
    field_names = next(prepared_table)
    data = [
        {
            field_name: _convert(value, fields[field_name], *args, **kwargs)
            for field_name, value in zip(field_names, row)
        }
        for row in prepared_table
    ]

    json_data = json.dumps(data, indent=indent)
    if type(json_data) is six.text_type:  # Python 3
        json_data = json_data.encode(encoding)

    if indent is not None:
        # clean up empty spaces at the end of lines
        json_data = b"\n".join(line.rstrip() for line in json_data.splitlines())

    if return_data:
        result = json_data
    else:
        result = source.fobj
        source.fobj.write(json_data)
        source.fobj.flush()

    if source.should_close:
        source.fobj.close()

    return result
