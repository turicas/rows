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
from rows.table import Table
from rows.utils import slug, SLUG_CHARS


def get_filename_and_fobj(filename_or_fobj, mode='r', dont_open=False):
    if getattr(filename_or_fobj, 'read', None) is not None:
        fobj = filename_or_fobj
        filename = getattr(fobj, 'name', None)
    else:
        fobj = open(filename_or_fobj, mode=mode) if not dont_open else None
        filename = filename_or_fobj

    return filename, fobj


def _make_new_field_name(field_name, field_names):
    new_field_name = field_name
    index = 2
    while new_field_name in field_names:
        new_field_name = '{}_{}'.format(field_name, index)
        index += 1
    return new_field_name


def make_header(data, permit_not=False):
    permitted_chars = SLUG_CHARS
    if permit_not:
        permitted_chars += '^'

    header = [slug(field_name, permitted_chars=permitted_chars).lower()
              for field_name in data]
    field_names = []
    for index, field_name in enumerate(header):
        if not field_name:
            field_name = 'field_{}'.format(index)
        if field_name[0].isdigit():
            field_name = 'field_{}'.format(field_name)
        if field_name in field_names:
            field_name = _make_new_field_name(field_name, field_names)
        field_names.append(field_name)
    return field_names


def create_table(data, meta=None, fields=None, skip_header=True,
                 import_fields=None, samples=None, *args, **kwargs):
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
            raise ValueError("Invalid field names {}".format(field_names))

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
    if export_fields is None:  # for performance
        yield table.fields.keys()
        for row in table._rows:
            yield row
    else:
        export_fields = make_header(export_fields)
        fields = table.fields
        table_field_names = fields.keys()
        diff = set(export_fields) - set(table_field_names)
        if diff:
            field_names = ', '.join('"{}"'.format(field) for field in diff)
            raise ValueError("Invalid field names {}".format(field_names))

        field_indexes = map(table_field_names.index, export_fields)

        yield export_fields
        for row in table._rows:
            yield [row[field_index] for field_index in field_indexes]


def serialize(table, *args, **kwargs):
    prepared_table = prepare_to_export(table, *args, **kwargs)

    field_names = prepared_table.next()
    yield field_names

    field_types = [table.fields[field_name] for field_name in field_names]
    for row in prepared_table:
        yield [field_type.serialize(value, *args, **kwargs)
               for value, field_type in zip(row, field_types)]
