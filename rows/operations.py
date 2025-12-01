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


def join(keys, tables, ignore_repeated_fields=False):
    """
    Perform an INNER JOIN in tables using keys (only advised if tables are small - otherwise use a database)

    Even if `ignore_repeated_fields` is `False`, the keys are not repeated (since their values are equal)
    """
    from collections import defaultdict
    from itertools import product

    from rows.compat import ORDERED_DICT
    from rows.fields import make_header
    from rows.plugins.utils import create_table

    # First, create new field names since that could be conflicting names
    selected_field_names = []
    for table_index, table in enumerate(tables):
        for key in keys:
            if key not in table.field_names:
                raise ValueError("Key {} not found in table {}".format(repr(key), table_index))
        if table_index == 0:
            selected_field_names.extend([(table_index, field_name) for field_name in table.field_names])
        elif not ignore_repeated_fields:
            selected_field_names.extend(
                [(table_index, field_name) for field_name in table.field_names if field_name not in keys]
            )
        else:
            current_field_names = [field_name for _, field_name in selected_field_names]
            selected_field_names.extend(
                [
                    (table_index, field_name)
                    for field_name in table.field_names
                    if field_name not in keys and field_name not in current_field_names
                ]
            )
    new_field_names = make_header([field_name for _, field_name in selected_field_names])
    fields = ORDERED_DICT(
        [
            (new_field_name, tables[table_index].fields[original_field_name])
            for new_field_name, (table_index, original_field_name) in zip(new_field_names, selected_field_names)
        ]
    )

    # Hash join: build
    hashmap = defaultdict(list)
    for table_index, table in enumerate(tables):
        for row_index, row in enumerate(table):
            hashmap[tuple(getattr(row, key) for key in keys)].append((table_index, row_index))
    # Hash join: combine
    n_tables = len(tables)
    tuples = []
    for key_tuple, matching_rows in hashmap.items():
        rows_by_table = defaultdict(list)
        for table_index, row_id in matching_rows:
            rows_by_table[table_index].append(row_id)
        if len(rows_by_table) != n_tables:  # Do not match all tables
            continue
        for row_ids in product(*(rows_by_table[i] for i in range(n_tables))):
            tuples.append(
                tuple(
                    [
                        getattr(tables[table_index][row_ids[table_index]], field_name)
                        for table_index, field_name in selected_field_names
                    ]
                )
            )
    return create_table(data=tuples, fields=fields, skip_header=False, mode="eager")


def transform(fields, function, *tables):
    "Return a new table based on other tables and a transformation function"
    from rows.table import Table

    new_table = Table(fields=fields)
    for table in tables:
        for row in filter(bool, map(lambda row: function(row, table), table)):
            new_table.append(row)
    return new_table


def transpose(table, fields_column, *args, **kwargs):
    from rows.plugins.utils import create_table

    field_names = []
    new_rows = [{} for _ in range(len(table.fields) - 1)]
    for row in table:
        row = row._asdict()
        field_name = row[fields_column]
        field_names.append(field_name)
        del row[fields_column]
        for index, value in enumerate(row.values()):
            new_rows[index][field_name] = value

    table_rows = [[row[field_name] for field_name in field_names] for row in new_rows]
    return create_table([field_names] + table_rows, *args, **kwargs)
