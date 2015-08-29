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

from rows.table import Table


def join(keys, tables):
    """Merge a list of `Table` objects using `keys` to group rows"""

    # Make new (merged) Table fields
    fields = OrderedDict()
    map(lambda table: fields.update(table.fields), tables)
    # TODO: may raise an error if a same field is different in some tables

    # Check if all keys are inside merged Table's fields
    fields_keys = set(fields.keys())
    for key in keys:
        if key not in fields_keys:
            raise ValueError('Invalid key: "{}"'.format(key))

    # Group rows by key, without missing ordering
    none_fields = lambda: OrderedDict({field: None for field in fields.keys()})
    data = OrderedDict()
    for table in tables:
        for row in table:
            row_key = tuple([getattr(row, key) for key in keys])
            if row_key not in data:
                data[row_key] = none_fields()
            data[row_key].update(row._asdict())

    merged = Table(fields=fields)
    merged.extend(data.values())
    return merged


def transform(fields, function, *tables):
    "Return a new table based on other tables and a transformation function"

    new_table = Table(fields=fields)

    for table in tables:
        map(new_table.append,
            filter(bool, map(lambda row: function(row, table), table)))

    return new_table


def serialize(table, *args, **kwargs):
    fields = table.fields
    fields_items = fields.items()

    for row in table:
        yield [field_type.serialize(getattr(row, field_name),
                                    *args, **kwargs)
                for field_name, field_type in fields_items]
