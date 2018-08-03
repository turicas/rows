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

import psycopg2
import unittest

from collections import OrderedDict

import mock

import rows
import rows.plugins.postgresql
import rows.plugins.utils
import tests.utils as utils

from rows import fields
from rows.plugins.postgresql import pgconnect

import os


class PluginPostgreSQLTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'postgresql'
    uri = os.environ.get('POSTGRESQL_URI',
                         'postgresql://postgres:postgres@localhost/postgres')
    assert_meta_encoding = False
    override_fields = {'percent_column': fields.DecimalField,
                       'bool_column': fields.BoolField, }

    def test_imports(self):
        self.assertIs(rows.import_from_postgresql,
                      rows.plugins.postgresql.import_from_postgresql)
        self.assertIs(rows.export_to_postgresql,
                      rows.plugins.postgresql.export_to_postgresql)

    @mock.patch('rows.plugins.postgresql.create_table')
    def test_import_from_postgresql_uses_create_table(self,
                                                      mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'encoding': 'test', 'some_key': 123, 'other': 456, }
        result = rows.import_from_postgresql(self.uri, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'postgresql',
                          'uri': self.uri, }
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins.postgresql.create_table')
    def test_import_from_postgresql_retrieve_desired_data(self,
                                                          mocked_create_table):
        mocked_create_table.return_value = 42

        # import using uri
        table_1 = rows.import_from_postgresql(self.uri)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args)

        # import using connection
        connection = pgconnect(self.uri)
        table_2 = rows.import_from_postgresql(connection)
        call_args = mocked_create_table.call_args_list[1]
        self.assert_create_table_data(call_args, uri=connection)
        connection.close()

    def test_postgresql_injection(self):
        connection = rows.export_to_postgresql(utils.table, self.uri)
        with self.assertRaises(ValueError):
            rows.import_from_postgresql(connection,
                                        table_name=('table1","'
                                                    'postgresql_master'))

        with self.assertRaises(ValueError):
            rows.export_to_postgresql(utils.table, self.uri,
                                      table_name='table1", "postgresql_master')

    def test_export_to_postgresql_uri(self):
        rows.export_to_postgresql(utils.table, self.uri)

        table = rows.import_from_postgresql(self.uri)
        self.assert_table_equal(table, utils.table)

    def test_export_to_postgresql_connection(self):
        connection = pgconnect(self.uri)
        rows.export_to_postgresql(utils.table, connection)
        connection.close()

        table = rows.import_from_postgresql(self.uri)
        self.assert_table_equal(table, utils.table)

    def test_export_to_postgresql_create_unique_table_name(self):
        first_table = utils.table
        second_table = utils.table + utils.table

        rows.export_to_postgresql(first_table, self.uri)  # table1
        rows.export_to_postgresql(second_table, self.uri)  # table2

        result_first_table = rows.import_from_postgresql(self.uri,
                                                         table_name='table1')
        result_second_table = rows.import_from_postgresql(self.uri,
                                                          table_name='table2')
        self.assert_table_equal(result_first_table, first_table)
        self.assert_table_equal(result_second_table, second_table)

    def test_export_to_postgresql_forcing_table_name_appends_rows(self):
        rows.export_to_postgresql(utils.table, self.uri, table_name='rows')
        rows.export_to_postgresql(utils.table, self.uri, table_name='rows')

        result_table = rows.import_from_postgresql(self.uri, table_name='rows')

        self.assertEqual(len(result_table), 2 * len(utils.table))
        self.assert_table_equal(result_table, utils.table + utils.table)

    @mock.patch('rows.plugins.postgresql.prepare_to_export')
    def test_export_to_postgresql_prepare_to_export(self,
                                                    mocked_prepare_to_export):
        encoding = 'iso-8859-15'
        kwargs = {'test': 123, 'parameter': 3.14, }
        mocked_prepare_to_export.return_value = iter(rows.
                                                     plugins.utils.
                                                     prepare_to_export(utils.
                                                                       table))

        rows.export_to_postgresql(utils.table, self.uri, encoding=encoding,
                                  **kwargs)
        self.assertTrue(mocked_prepare_to_export.called)
        self.assertEqual(mocked_prepare_to_export.call_count, 1)

        call = mocked_prepare_to_export.call_args
        self.assertEqual(call[0], (utils.table, ))
        kwargs['encoding'] = encoding
        self.assertEqual(call[1], kwargs)

    def test_import_from_postgresql_query_args(self):
        connection = rows.export_to_postgresql(utils.table, self.uri)
        table = rows.import_from_postgresql(connection,
                                            query=('SELECT * FROM table1 '
                                                   'WHERE float_column > ?'),
                                            query_args=(3, ))
        for row in table:
            self.assertTrue(row.float_column > 3)
