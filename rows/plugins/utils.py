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
from rows.utils import slug


def get_filename_and_fobj(filename_or_fobj, mode='r', dont_open=False):
    if getattr(filename_or_fobj, 'read', None) is not None:
        fobj = filename_or_fobj
        filename = getattr(fobj, 'name', None)
    else:
        fobj = open(filename_or_fobj, mode=mode) if not dont_open else None
        filename = filename_or_fobj

    return filename, fobj


def make_header(data):
    header = [slug(field_name).lower() for field_name in data]
    return [field_name if field_name else 'field_{}'.format(index)
            for index, field_name in enumerate(header)]


def create_table(data, meta=None, force_headers=None, fields=None,
                 skip_header=True, samples=None, *args, **kwargs):
    # TODO: add auto_detect_types=True parameter
    table_rows = iter(data)
    sample_rows = []

    if fields is None:
        header = force_headers or make_header(table_rows.next())
        if samples is not None:
            sample_rows = list(islice(table_rows, 0, samples))
        else:
            sample_rows = list(table_rows)
        fields = detect_types(header, sample_rows, *args, **kwargs)
    else:
        if skip_header:
            _ = table_rows.next()
            header = make_header(fields.keys())
            assert isinstance(fields, OrderedDict)
            fields = {field_name: fields[key]
                      for field_name, key in zip(header, fields)}
        else:
            header = make_header(fields.keys())

    # TODO: put this inside Table.__init__
    table = Table(fields=fields, meta=meta)
    for row in chain(sample_rows, table_rows):
        table.append({field_name: value
                      for field_name, value in zip(header, row)})

    return table


def serialize(table, field_names=None, *args, **kwargs):
    fields = table.fields
    table_field_names = fields.keys()
    if field_names is None:
        field_names = fields.keys()
    elif not set(field_names).issubset(set(table_field_names)):
        raise ValueError("Invalid field names")

    yield field_names

    fields_items = [(table_field_names.index(field_name), fields[field_name])
                    for field_name in field_names]
    for row in table._rows:
        yield [field_type.serialize(row[field_index], *args, **kwargs)
               for field_index, field_type in fields_items]
