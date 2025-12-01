# coding: utf-8

# Copyright 2014-2025 Álvaro Justen <https://github.com/turicas/rows/>
#    This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
#    Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
#    any later version.
#    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
#    warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
#    more details.
#    You should have received a copy of the GNU Lesser General Public License along with this program.  If not, see
#    <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import json
from io import BytesIO, TextIOWrapper

from rows.utils import Source


def import_from_json(filename_or_fobj, encoding="utf-8", *args, **kwargs):
    """Import a JSON file or file-like object into a `rows.Table`.

    If a file-like object is provided it MUST be open in text (non-binary) mode
    on Python 3 and could be open in both binary or text mode on Python 2.
    """
    from rows.plugins.utils import create_table, is_binary_file

    source = Source.from_file(filename_or_fobj, mode="r", plugin_name="json", encoding=encoding)
    fobj = source.fobj
    if is_binary_file(fobj):
        fobj = TextIOWrapper(fobj, encoding=encoding)

    # JSON should always use UTF-8, UTF-16 or UTF-32 encodings.
    json_obj = json.load(fobj)
    field_names = []
    for row in json_obj:
        for key in row.keys():
            if key not in field_names:
                field_names.append(key)
    table_rows = [[item.get(key) for key in field_names] for item in json_obj]

    meta = {"imported_from": "json", "source": source}
    return create_table([field_names] + table_rows, meta=meta, *args, **kwargs)


def _convert(value, field_type, *args, **kwargs):
    from rows import fields

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
    from rows.compat import BINARY_TYPE
    from rows.plugins.utils import is_binary_file, is_fobj, prepare_to_export

    orig_filename_or_fobj = filename_or_fobj
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
    result_must_be_encoded = return_data or not is_fobj(orig_filename_or_fobj) or is_binary_file(orig_filename_or_fobj)
    if result_must_be_encoded and not isinstance(json_data, BINARY_TYPE):
        json_data = json_data.encode(encoding)

    if return_data:
        result = json_data
    else:
        result = source.fobj
        source.fobj.write(json_data)
        source.fobj.flush()

    if source.should_close:
        source.fobj.close()

    return result
