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

from collections import OrderedDict
from itertools import chain, islice

from rows.fields import detect_types
from rows.table import FlexibleTable, Table
from rows.utils import slug, SLUG_CHARS


def get_filename_and_fobj(filename_or_fobj, mode='r', dont_open=False):
    if getattr(filename_or_fobj, 'read', None) is not None:
        fobj = filename_or_fobj
        filename = getattr(fobj, 'name', None)
    else:
        fobj = open(filename_or_fobj, mode=mode) if not dont_open else None
        filename = filename_or_fobj

    return filename, fobj


def make_unique_name(name, existing_names, name_format='{name}_{index}'):
    '''Return a unique name based on `name_format` and `name`.'''

    new_name = name
    index = 2
    while new_name in existing_names:
        new_name = name_format.format(name=name, index=index)
        index += 1
    return new_name


def make_header(data, permit_not=False):
    permitted_chars = SLUG_CHARS
    if permit_not:
        permitted_chars += '^'

    header = map(slug, data)
    field_names = []
    for index, field_name in enumerate(header):
        if not field_name:
            field_name = 'field_{}'.format(index)
        if field_name[0].isdigit():
            field_name = 'field_{}'.format(field_name)
        if field_name in field_names:
            field_name = make_unique_name(name=field_name,
                                          existing_names=field_names)
        field_names.append(field_name)
    return field_names


def create_table(data, meta=None, fields=None, skip_header=True,
                 import_fields=None, samples=None, force_types=None,
                 *args, **kwargs):
    # TODO: add auto_detect_types=True parameter
    table_rows = iter(data)
    sample_rows = []

    if fields is None:
        header = make_header(table_rows.next())

        if samples is not None:
            sample_rows = list(islice(table_rows, 0, samples))
        else:
            sample_rows = list(table_rows)

        fields = detect_types(header, sample_rows, *args, **kwargs)

        if force_types is not None:
            # TODO: optimize field detection (ignore fields on `force_types`)
            for field_name, field_type in force_types.items():
                fields[field_name] = field_type
    else:
        if not isinstance(fields, OrderedDict):
            raise ValueError('`fields` must be an `OrderedDict`')

        if skip_header:
            _ = table_rows.next()

        header = make_header(fields.keys())
        fields = OrderedDict([(field_name, fields[key])
                              for field_name, key in zip(header, fields)])

    if import_fields is not None:
        # TODO: can optimize if import_fields is not None.
        #       Example: do not detect all columns
        import_fields = make_header(import_fields)

        diff = set(import_fields) - set(header)
        if diff:
            field_names = ', '.join('"{}"'.format(field) for field in diff)
            raise ValueError("Invalid field names: {}".format(field_names))

        new_fields = OrderedDict()
        for field_name in import_fields:
            new_fields[field_name] = fields[field_name]
        fields = new_fields

    table = Table(fields=fields, meta=meta)
    # TODO: put this inside Table.__init__
    for row in chain(sample_rows, table_rows):
        table.append({field_name: value
                      for field_name, value in zip(header, row)})

    return table


def prepare_to_export(table, export_fields=None, *args, **kwargs):
    # TODO: optimize for more used cases (export_fields=None)
    table_type = type(table)
    if table_type not in (FlexibleTable, Table):
        raise ValueError('Table type not recognized')

    if export_fields is None:
        export_fields = table.fields.keys()
    export_fields = make_header(export_fields)

    fields = table.fields
    table_field_names = fields.keys()
    diff = set(export_fields) - set(table_field_names)
    if diff:
        field_names = ', '.join('"{}"'.format(field) for field in diff)
        raise ValueError("Invalid field names: {}".format(field_names))

    yield export_fields

    if table_type is Table:
        field_indexes = map(table_field_names.index, export_fields)
        for row in table._rows:
            yield [row[field_index] for field_index in field_indexes]
    elif table_type is FlexibleTable:
        for row in table._rows:
            yield [row[field_name] for field_name in export_fields]


def serialize(table, *args, **kwargs):
    prepared_table = prepare_to_export(table, *args, **kwargs)

    field_names = prepared_table.next()
    yield field_names

    field_types = [table.fields[field_name] for field_name in field_names]
    for row in prepared_table:
        yield [field_type.serialize(value, *args, **kwargs)
               for value, field_type in zip(row, field_types)]


def export_data(filename_or_fobj, data, mode='w'):
    if filename_or_fobj is not None:
        _, fobj = get_filename_and_fobj(filename_or_fobj, mode=mode)
        fobj.write(data)
        fobj.flush()
        return fobj
    else:
        return data
