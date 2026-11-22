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

from itertools import chain

from rows import fields
from rows.compat import ORDERED_DICT
from rows.plugins.utils import create_table, is_binary_file, is_fobj, prepare_to_export
from rows.utils import Source


def _arrow_type_to_field(arrow_type):
    """Return the `rows` field class for a pyarrow `DataType` (or `None` if it should be detected)"""
    import pyarrow

    types = pyarrow.types
    if types.is_boolean(arrow_type):
        return fields.BoolField
    elif types.is_integer(arrow_type):
        return fields.IntegerField
    elif types.is_floating(arrow_type):
        return fields.FloatField
    elif types.is_decimal(arrow_type):
        return fields.DecimalField
    elif types.is_string(arrow_type) or types.is_large_string(arrow_type):
        return fields.TextField
    elif types.is_binary(arrow_type) or types.is_large_binary(arrow_type) or types.is_fixed_size_binary(arrow_type):
        return fields.BinaryField
    elif types.is_date(arrow_type):
        return fields.DateField
    elif types.is_timestamp(arrow_type):
        return fields.DatetimeField
    return None


def _field_to_arrow_type(field_type):
    """Return the pyarrow `DataType` for a `rows` field class (or `None` if it should be inferred by pyarrow)"""
    import pyarrow

    if issubclass(field_type, fields.BoolField):
        return pyarrow.bool_()
    elif issubclass(field_type, fields.IntegerField):
        return pyarrow.int64()
    elif issubclass(field_type, fields.FloatField):
        return pyarrow.float64()
    elif issubclass(field_type, fields.DateField):
        return pyarrow.date32()
    elif issubclass(field_type, fields.BinaryField):
        return pyarrow.binary()
    elif issubclass(field_type, fields.TextField):
        return pyarrow.string()
    return None


def _iterate_rows(arrow_table):
    for batch in arrow_table.to_batches():
        columns = [column.to_pylist() for column in batch.columns]
        for row in zip(*columns):
            yield row


def import_from_feather(filename_or_fobj, *args, **kwargs):
    """Import data from a Feather (Apache Arrow IPC) file and return with rows.Table."""

    from pyarrow import feather

    if is_fobj(filename_or_fobj) and not is_binary_file(filename_or_fobj):
        raise ValueError("import_from_feather must not receive a file-like object in text mode")

    source = Source.from_file(filename_or_fobj, plugin_name="feather", mode="rb")
    arrow_table = feather.read_table(source.fobj)
    if source.should_close:  # The whole table is already in memory
        source.fobj.close()

    header = fields.make_header(arrow_table.schema.names)
    types = ORDERED_DICT()
    for field_name, arrow_field in zip(header, arrow_table.schema):
        field_type = _arrow_type_to_field(arrow_field.type)
        if field_type is not None:
            types[field_name] = field_type

    table_rows = _iterate_rows(arrow_table)
    meta = {"imported_from": "feather", "source": source}
    return create_table(chain([header], table_rows), meta=meta, force_types=types, *args, **kwargs)


def export_to_feather(table, filename_or_fobj=None, *args, **kwargs):
    """Export the rows.Table to a Feather (Apache Arrow IPC) file and return the saved file.

    If `filename_or_fobj` is `None`, the file contents are returned as bytes.
    """
    from io import BytesIO

    import pyarrow
    from pyarrow import feather

    if is_fobj(filename_or_fobj) and not is_binary_file(filename_or_fobj):
        raise ValueError("export_to_feather must receive a file-object open in binary mode")

    return_result = False
    if filename_or_fobj is None:
        filename_or_fobj = BytesIO()
        return_result = True
    source = Source.from_file(filename_or_fobj, mode="wb", plugin_name="feather")

    prepared_table = prepare_to_export(table, *args, **kwargs)
    field_names = list(next(prepared_table))
    field_types = [table.fields[field_name] for field_name in field_names]
    columns = [[] for _ in field_names]
    for row in prepared_table:
        for column, value in zip(columns, row):
            column.append(value)

    arrays = []
    for field_type, column in zip(field_types, columns):
        arrow_type = _field_to_arrow_type(field_type)
        if arrow_type is None and not issubclass(field_type, (fields.DecimalField, fields.DatetimeField)):
            # Decimal and datetime types are inferred by pyarrow (precision/scale and timezone vary). Types not
            # natively supported (like JSON and UUID) are stored as text.
            column = [None if value is None else field_type.serialize(value) for value in column]
            arrow_type = pyarrow.string()
        arrays.append(pyarrow.array(column, type=arrow_type))
    arrow_table = pyarrow.Table.from_arrays(arrays, names=field_names)

    feather.write_feather(arrow_table, source.fobj)
    source.fobj.flush()

    if return_result:
        source.fobj.seek(0)
        result = source.fobj.read()
    else:
        result = source.fobj

    if source.should_close:
        source.fobj.close()

    return result
