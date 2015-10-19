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

import datetime

import sqlite3

import rows.fields as fields

from rows.plugins.utils import (create_table, get_filename_and_fobj,
                                make_unique_name, serialize)
from rows.utils import ipartition


SQL_TABLE_NAMES = 'SELECT name FROM sqlite_master WHERE type="table"'
SQL_CREATE_TABLE = 'CREATE TABLE IF NOT EXISTS {table_name} ({field_types})'
SQL_SELECT_ALL = 'SELECT * FROM {table_name}'
SQL_INSERT = 'INSERT INTO {table_name} ({field_names}) VALUES ({placeholders})'

SQLITE_TYPES = {fields.BinaryField: 'BLOB',
                fields.BoolField: 'INTEGER',
                fields.IntegerField: 'INTEGER',
                fields.FloatField: 'REAL',
                fields.DecimalField: 'REAL',
                fields.PercentField: 'REAL',
                fields.DateField: 'TEXT',
                fields.DatetimeField: 'TEXT',
                fields.TextField: 'TEXT', }

def _convert(field_type, value):
    if value is None:
        return None

    if field_type in (fields.BinaryField, fields.DateField, fields.TextField):
        return value
    elif field_type is fields.BoolField:
        return 1 if value == 'true' else 0
    elif field_type is fields.IntegerField:
        return int(value)
    elif field_type in (fields.FloatField, fields.DecimalField):
        return float(value)
    elif field_type is fields.PercentField:
        return float(value.replace('%', '')) / 100
    elif field_type is fields.DatetimeField:
        return value.replace('T', ' ')
    else:
        return value


def _get_connection(filename_or_connection):
    if isinstance(filename_or_connection, basestring):
        return sqlite3.connect(filename_or_connection)
    else:
        return filename_or_connection


def import_from_sqlite(filename_or_connection, table_name='rows', query=None,
                       *args, **kwargs):
    connection = _get_connection(filename_or_connection)
    cursor = connection.cursor()
    sql = query if query else SQL_SELECT_ALL.format(table_name=table_name)

    cursor.execute(sql)
    header = [info[0] for info in cursor.description]
    table_rows = list(cursor)  # TODO: may not put everything in memory
    cursor.close()

    meta = {'imported_from': 'sqlite', 'filename': filename_or_connection, }
    return create_table([header] + table_rows, meta=meta, *args, **kwargs)


def export_to_sqlite(table_obj, filename_or_connection, table_name='rows',
                     batch_size=100, *args, **kwargs):
    # TODO: should add transaction support?


    serialized_table = serialize(table_obj, *args, **kwargs)
    connection = _get_connection(filename_or_connection)
    table_names = [item[0]
                   for item in connection.execute(SQL_TABLE_NAMES).fetchall()]
    table_name = make_unique_name(name=table_name, existing_names=table_names)

    field_names = serialized_table.next()
    columns = ['{} {}'.format(field_name,
                              SQLITE_TYPES[table_obj.fields[field_name]])
               for field_name in field_names]
    sql = SQL_CREATE_TABLE.format(table_name=table_name,
                                  field_types=', '.join(columns))
    connection.execute(sql)

    columns = ', '.join(field_names)
    placeholders = ', '.join(['?' for field in field_names])
    insert_sql = SQL_INSERT.format(table_name=table_name,
                                   field_names=columns,
                                   placeholders=placeholders)
    field_types = [table_obj.fields[field_name] for field_name in field_names]
    for batch in ipartition(serialized_table, batch_size):
        rows_values = [[_convert(field_types[index], value)
                        for index, value in enumerate(row)]
                       for row in batch]
        connection.executemany(insert_sql, rows_values)

    connection.commit()
    return connection
