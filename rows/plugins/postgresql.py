# coding: utf-8

# Copyright 2014-2018 Álvaro Justen <https://github.com/turicas/rows/>
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
import six
import string

from psycopg2 import connect as pgconnect

import rows.fields as fields
from rows.plugins.utils import (create_table, get_filename_and_fobj,
                                ipartition, make_unique_name,
                                prepare_to_export)


SQL_TABLE_NAMES = """
    SELECT
        tablename
    FROM pg_tables
    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
"""
SQL_CREATE_TABLE = ('CREATE TABLE IF NOT EXISTS '
                    '"{table_name}" ({field_types})')
SQL_SELECT_ALL = 'SELECT * FROM "{table_name}"'
SQL_INSERT = ('INSERT INTO "{table_name}" ({field_names}) '
              'VALUES ({placeholders})')
SQL_TYPES = {
    fields.BinaryField: 'BYTEA',
    fields.BoolField: 'BOOLEAN',
    fields.DateField: 'DATE',
    fields.DatetimeField: 'TIMESTAMP(0) WITHOUT TIME ZONE',
    fields.DecimalField: 'NUMERIC',
    fields.FloatField: 'REAL',
    fields.IntegerField: 'INTEGER',
    fields.PercentField: 'REAL',
    fields.TextField: 'TEXT',
    fields.JSONField: 'JSONB',
}
DEFAULT_TYPE = 'BYTEA'


def _python_to_postgresql(field_types):

    def convert_value(field_type, value):
        if field_type in (fields.BinaryField,
                          fields.BoolField,
                          fields.DateField,
                          fields.DatetimeField,
                          fields.DecimalField,
                          fields.FloatField,
                          fields.IntegerField,
                          fields.PercentField,
                          fields.TextField,
                          fields.JSONField):
            return value

        else:  # don't know this field
            return field_type.serialize(value)

    def convert_row(row):
        return [convert_value(field_type, value)
                for field_type, value in zip(field_types, row)]

    return convert_row


def _get_connection(connection):

    if isinstance(connection, (six.binary_type, six.text_type)):
        return True, pgconnect(connection)

    else:  # already a connection
        return False, connection


def _valid_table_name(name):
    '''Verify if a given table name is valid for `rows`

    Rules:
    - Should start with a letter or '_'
    - Letters can be capitalized or not
    - Accepts letters, numbers and _
    '''

    if name[0] not in '_' + string.ascii_letters or \
       not set(name).issubset('_' + string.ascii_letters + string.digits):
        return False

    else:
        return True


def import_from_postgresql(connection, table_name='table1', query=None,
                           query_args=None, *args, **kwargs):

    should_close_connection, connection = _get_connection(connection)
    cursor = connection.cursor()

    if query is None:
        if not _valid_table_name(table_name):
            raise ValueError('Invalid table name: {}'.format(table_name))

        query = SQL_SELECT_ALL.format(table_name=table_name)

    if query_args is None:
        query_args = tuple()

    cursor.execute(query, query_args)  # TODO: may be lazy
    table_rows = list(cursor.fetchall())
    header = [six.text_type(info[0]) for info in cursor.description]
    cursor.close()
    # TODO: should close connection also?

    meta = {'imported_from': 'postgresql', 'uri': connection, }
    return create_table([header] + table_rows, meta=meta, *args, **kwargs)


def export_to_postgresql(table, connection, table_name=None,
                         table_name_format='table{index}', batch_size=100,
                         *args, **kwargs):
    # TODO: should add transaction support?

    prepared_table = prepare_to_export(table, *args, **kwargs)
    should_close_connection, connection = _get_connection(connection)
    cursor = connection.cursor()

    if table_name is None:
        cursor.execute(SQL_TABLE_NAMES)
        table_names = [item[0] for item in cursor.fetchall()]
        table_name = make_unique_name(table_name_format.format(index=1),
                                      existing_names=table_names,
                                      name_format=table_name_format,
                                      start=1)

    elif not _valid_table_name(table_name):
            raise ValueError('Invalid table name: {}'.format(table_name))

    field_names = next(prepared_table)
    field_types = list(map(table.fields.get, field_names))
    columns = ['{} {}'.format(field_name,
                              SQL_TYPES.get(field_type, DEFAULT_TYPE))
               for field_name, field_type in zip(field_names, field_types)]
    cursor.execute(SQL_CREATE_TABLE.format(table_name=table_name,
                                           field_types=', '.join(columns)))

    insert_sql = SQL_INSERT.format(
            table_name=table_name,
            field_names=', '.join(field_names),
            placeholders=', '.join('%s' for _ in field_names))
    _convert_row = _python_to_postgresql(field_types)
    for batch in ipartition(prepared_table, batch_size):
        cursor.executemany(insert_sql, map(_convert_row, batch))

    connection.commit()
    if should_close_connection:
        connection.close()
    return connection
