# coding: utf-8

# Copyright 2014-2018 Álvaro Justen <https://github.com/turicas/rows/>

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

from collections import OrderedDict
from itertools import chain, islice
from unicodedata import normalize

import six

if six.PY2:
    from collections import Iterator
elif six.PY3:
    from collections.abc import Iterator

from rows.fields import detect_types, make_header, make_unique_name, slug
from rows.table import FlexibleTable, Table


def ipartition(iterable, partition_size):
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


def get_filename_and_fobj(filename_or_fobj, mode="r", dont_open=False):
    if getattr(filename_or_fobj, "read", None) is not None:
        fobj = filename_or_fobj
        filename = getattr(fobj, "name", None)
    else:
        fobj = open(filename_or_fobj, mode=mode) if not dont_open else None
        filename = filename_or_fobj

    return filename, fobj


def create_table(
    data,
    meta=None,
    fields=None,
    skip_header=True,
    import_fields=None,
    samples=None,
    force_types=None,
    *args,
    **kwargs
):
    """Create a rows.Table object based on data rows and some configurations

    - `skip_header` is only used if `fields` is set
    - `samples` is only used if `fields` is `None`
    - `force_types` is only used if `fields` is `None`
    - `import_fields` can be used either if `fields` is set or not, the
      resulting fields will seek its order
    - `fields` must always be in the same order as the data
    """
    # TODO: add warning if using skip_header and create skip_rows
    #       (int, default = ?). Could be used if `fields` is set or not.

    table_rows = iter(data)

    if fields is None:  # autodetect field types
        header = make_header(next(table_rows))

        if samples is not None:
            sample_rows = list(islice(table_rows, 0, samples))
        else:
            sample_rows = list(table_rows)
        table_rows = chain(sample_rows, table_rows)

        # TODO: optimize field detection (ignore fields on `force_types` and
        #       not in `import_fields`).
        # TODO: add `type_hints` parameter so autodetection can be easier
        #       (plugins may specify some possible field types).
        fields = detect_types(header, sample_rows, *args, **kwargs)

        if force_types is not None:
            fields.update(force_types)

    else:  # using provided field types
        if not isinstance(fields, OrderedDict):
            raise ValueError("`fields` must be an `OrderedDict`")

        if skip_header:
            # If we're skipping the header probably this row is not trustable
            # (can be data or garbage).
            _ = next(table_rows)

        header = make_header(list(fields.keys()))

        fields = OrderedDict(
            [(field_name, fields[key]) for field_name, key in zip(header, fields)]
        )

    if import_fields is not None:
        import_fields = make_header(import_fields)

        diff = set(import_fields) - set(header)
        if diff:
            field_names = ", ".join('"{}"'.format(field) for field in diff)
            raise ValueError("Invalid field names: {}".format(field_names))

        fields = OrderedDict(
            [(field_name, fields[field_name]) for field_name in import_fields]
        )

    fields_names_indexes = [
        (field_name, header.index(field_name)) for field_name in fields.keys()
    ]

    # TODO: put this inside Table.__init__
    table = Table(fields=fields, meta=meta)
    for row in table_rows:
        table.append(
            {
                field_name: row[field_index]
                for field_name, field_index in fields_names_indexes
            }
        )

    return table


def prepare_to_export(table, export_fields=None, *args, **kwargs):
    # TODO: optimize for more used cases (export_fields=None)
    table_type = type(table)
    if table_type not in (FlexibleTable, Table):
        raise ValueError("Table type not recognized")

    if export_fields is None:
        # we use already slugged-fieldnames
        export_fields = table.field_names
    else:
        # we need to slug all the field names
        export_fields = make_header(export_fields)

    table_field_names = table.field_names
    diff = set(export_fields) - set(table_field_names)
    if diff:
        field_names = ", ".join('"{}"'.format(field) for field in diff)
        raise ValueError("Invalid field names: {}".format(field_names))

    yield export_fields

    if table_type is Table:
        field_indexes = list(map(table_field_names.index, export_fields))
        for row in table._rows:
            yield [row[field_index] for field_index in field_indexes]
    elif table_type is FlexibleTable:
        for row in table._rows:
            yield [row[field_name] for field_name in export_fields]


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


def export_data(filename_or_fobj, data, mode="w"):
    """Return the object ready to be exported or only data if filename_or_fobj is not passed."""
    if filename_or_fobj is not None:
        _, fobj = get_filename_and_fobj(filename_or_fobj, mode=mode)
        fobj.write(data)
        fobj.flush()
        return fobj
    else:
        return data
