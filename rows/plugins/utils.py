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

# `slug` and `make_unique_name` are required here to maintain backwards compatibility
# TODO: add warnings about `make_header`, `make_unique_name` and `slug` deprecation (from here)
from rows.compat import DEFAULT_SAMPLE_ROWS
from rows.fields import make_header, make_unique_name, slug  # noqa


def ipartition(iterable, partition_size):
    from rows.compat import PYTHON_VERSION

    if PYTHON_VERSION < (3, 0, 0):
        from collections import Iterator
    else:
        from collections.abc import Iterator

    if not isinstance(iterable, Iterator):
        iterator = iter(iterable)
    else:
        iterator = iterable

    finished = False
    while not finished:
        data = []
        for _ in range(partition_size):
            try:
                data.append(next(iterator))
            except StopIteration:
                finished = True
                break
        if data:
            yield data


def valid_table_name(name):
    """Verify if a given table name is valid for `rows`.

    Rules:
    - Should start with a letter or '_'
    - Letters can be capitalized or not
    - Acceps letters, numbers and _
    """
    return (
        name[0] in "_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        and set(name).issubset(set("_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"))
    )


def create_table(
    data,
    meta=None,
    fields=None,
    skip_header=True,
    import_fields=None,
    samples=DEFAULT_SAMPLE_ROWS,
    force_types=None,
    max_rows=None,
    mode=None,
    *args,
    **kwargs
):
    """Create a rows.Table object based on data rows and some configurations

    - `skip_header` is only used if `fields` is set
    - `samples` is only used if `fields` is `None`. If samples=None, all data
      is filled in memory - use with caution.
    - `force_types` is only used if `fields` is `None`
    - `import_fields` can be used either if `fields` is set or not, the
      resulting fields will seek its order
    - `fields` must always be in the same order as the data
    """
    from itertools import chain, islice
    from os import unlink
    from pathlib import Path

    from rows.compat import ORDERED_DICT, ORDERED_DICTS
    from rows.fields import TextField, cached_type_deserialize, detect_types, get_items, make_header
    from rows.table import Table

    table_rows = iter(data)
    force_types = force_types or {}
    if import_fields is not None:
        import_fields = make_header(import_fields)

    # TODO: test max_rows
    if fields is None:  # autodetect field types
        # TODO: may add `type_hints` parameter so autodetection can be easier
        #       (plugins may specify some possible field types).
        header = make_header(next(table_rows))

        if samples is not None:
            sample_rows = list(islice(table_rows, 0, samples))
            if len(sample_rows) < samples:  # Read all the data
                table_rows = sample_rows
            else:
                table_rows = chain(sample_rows, table_rows)
        else:  # Read the whole table
            if max_rows is not None and max_rows > 0:
                sample_rows = table_rows = list(islice(table_rows, max_rows))
            else:
                sample_rows = table_rows = list(table_rows)

        # Detect field types using only the desired columns
        detected_fields = detect_types(
            header,
            sample_rows,
            skip_indexes=[
                index
                for index, field in enumerate(header)
                if field in force_types or field not in (import_fields or header)
            ],
            *args,
            **kwargs
        )
        # Check if any field was added during detecting process
        new_fields = [
            field_name
            for field_name in detected_fields.keys()
            if field_name not in header
        ]
        # Finally create the `fields` with both header and new field names,
        # based on detected fields `and force_types`
        fields = ORDERED_DICT(
            [
                (field_name, detected_fields.get(field_name, TextField))
                for field_name in header + new_fields
            ]
        )
        fields.update(force_types)

        # Update `header` and `import_fields` based on new `fields`
        header = list(fields.keys())
        if import_fields is None:
            import_fields = header

    else:  # using provided field types
        if not isinstance(fields, ORDERED_DICTS):
            raise ValueError("`fields` must be an instance of {}".format(ORDERED_DICTS))

        if skip_header:
            # If we're skipping the header probably this row is not trustable
            # (can be data or garbage).
            next(table_rows)

        header = make_header(list(fields.keys()))
        if import_fields is None:
            import_fields = header

        fields = ORDERED_DICT(
            [(field_name, fields[key]) for field_name, key in zip(header, fields)]
        )
    if max_rows is not None and max_rows > 0:
        # TODO: transform in list if data is already read
        table_rows = islice(table_rows, max_rows)

    diff = set(import_fields) - set(header)
    if diff:
        field_names = ", ".join('"{}"'.format(field) for field in diff)
        raise ValueError("Invalid field names: {}".format(field_names))
    fields = ORDERED_DICT(
        [(field_name, fields[field_name]) for field_name in import_fields]
    )
    field_types = list(fields.values())

    # What if we deserialize only when the data is read from the Table (not from the plugin)?
    if list(header) == list(import_fields):  # Add rows directly, no need to get specific indices
        table_rows = (
            tuple([
                cached_type_deserialize(field_type, value)
                for field_type, value in zip(field_types, row)
            ])
            for row in table_rows
        )
    else:
        field_indices = list(map(header.index, import_fields))
        table_rows = (
            tuple([
                cached_type_deserialize(field_type, row[index])
                for index, field_type in zip(field_indices, field_types)
            ])
            for row in table_rows
        )
    table = Table(fields=fields, meta=meta, data=table_rows, mode=mode)
    return table


def prepare_to_export(table, export_fields=None, *args, **kwargs):
    from rows.fields import make_header
    from rows.table import Table

    # TODO: optimize for more used cases (export_fields=None)
    if not isinstance(table, Table):
        raise ValueError("Table type '{}' not recognized".format(type(table).__name__))

    if export_fields is None:
        # we use already slugged-fieldnames
        export_fields = tuple(table.field_names)
    else:
        # we need to slug all the field names
        export_fields = tuple(make_header(export_fields))

    table_field_names = table.field_names
    diff = set(export_fields) - set(table_field_names)
    if diff:
        field_names = ", ".join('"{}"'.format(field) for field in diff)
        raise ValueError("Invalid field names: {}".format(field_names))

    yield export_fields
    for row in table.export(field_names=export_fields):
        yield row


def serialize(table, *args, **kwargs):
    prepared_table = prepare_to_export(table, *args, **kwargs)

    field_names = next(prepared_table)
    yield field_names

    field_types = [table.fields[field_name] for field_name in field_names]
    for row in prepared_table:
        yield [
            field_type.serialize(value, *args, **kwargs)
            for value, field_type in zip(row, field_types)
        ]

def is_binary_file(fobj):
    from gzip import GzipFile
    from io import BytesIO

    from rows.compat import TEXT_TYPE

    # TODO: probabaly there's a better way to check if a file-like object is open in binary or text mode
    if isinstance(fobj, BytesIO):
        return True
    has_mode = hasattr(fobj, "mode")
    if has_mode and isinstance(fobj, GzipFile) and isinstance(fobj.mode, int):
        # `gzip.GzipFile.mode` in Python 3.5 is an integer
        return True
    return has_mode and "b" in TEXT_TYPE(fobj.mode)


def is_fobj(obj):
    from pathlib import Path

    from rows.compat import BINARY_TYPE, TEXT_TYPE

    return obj is not None and not isinstance(obj, (TEXT_TYPE, BINARY_TYPE, Path)) and hasattr(obj, "read")
