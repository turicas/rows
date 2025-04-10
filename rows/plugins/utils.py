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
    samples=None,
    force_types=None,
    max_rows=None,
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
    from collections import OrderedDict
    from itertools import chain, islice
    from os import unlink
    from pathlib import Path

    from rows.fields import TextField, detect_types, get_items, make_header
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
            table_rows = chain(sample_rows, table_rows)
        else:
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
        fields = OrderedDict(
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
        if not isinstance(fields, OrderedDict):
            raise ValueError("`fields` must be an `OrderedDict`")

        if skip_header:
            # If we're skipping the header probably this row is not trustable
            # (can be data or garbage).
            next(table_rows)

        header = make_header(list(fields.keys()))
        if import_fields is None:
            import_fields = header

        fields = OrderedDict(
            [(field_name, fields[key]) for field_name, key in zip(header, fields)]
        )
    if max_rows is not None and max_rows > 0:
        table_rows = islice(table_rows, max_rows)

    # TODO: may unroll the loop of adding rows to the table to avoid calling `append` and `_make_row` repeatedly
    diff = set(import_fields) - set(header)
    if diff:
        field_names = ", ".join('"{}"'.format(field) for field in diff)
        raise ValueError("Invalid field names: {}".format(field_names))
    fields = OrderedDict(
        [(field_name, fields[field_name]) for field_name in import_fields]
    )

    table = Table(fields=fields, meta=meta)
    if list(header) == list(import_fields):  # Add rows directly, no need to get specific indices
        table.extend(dict(zip(import_fields, row)) for row in table_rows)
    else:
        get_row = get_items(*map(header.index, import_fields))
        table.extend(dict(zip(import_fields, get_row(row))) for row in table_rows)

    source = table.meta.get("source", None)
    if source is not None:
        if source.should_close:
            source.fobj.close()
        if source.should_delete and Path(source.uri).exists():
            unlink(source.uri)

    return table


def prepare_to_export(table, export_fields=None, *args, **kwargs):
    from rows.fields import make_header
    from rows.table import FlexibleTable, Table

    # TODO: optimize for more used cases (export_fields=None)
    table_type = type(table)
    if table_type not in (FlexibleTable, Table):
        raise ValueError("Table type not recognized")

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

    if table_type is Table:
        if list(table_field_names) == list(export_fields):  # Yield directly the stored rows
            for row in table._rows:
                yield row
        else:
            field_indexes = tuple(map(table_field_names.index, export_fields))
            for row in table._rows:
                yield tuple([row[field_index] for field_index in field_indexes])
    elif table_type is FlexibleTable:
        for row in table._rows:
            yield tuple([row[field_name] for field_name in export_fields])


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
    from io import BytesIO

    # TODO: probabaly there's a better way to check if a file-like object is open in binary or text mode
    return isinstance(fobj, BytesIO) or (hasattr(fobj, "mode") and "b" in fobj.mode)


def is_fobj(obj):
    from pathlib import Path

    from rows.compat import BINARY_TYPE, TEXT_TYPE

    return obj is not None and not isinstance(obj, (TEXT_TYPE, BINARY_TYPE, Path)) and hasattr(obj, "read")
