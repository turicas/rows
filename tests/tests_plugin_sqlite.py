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

import sqlite3
import tempfile
import unittest

import mock

import rows
import rows.plugins.sqlite
import rows.plugins.utils
import utils

from rows import fields


class PluginSqliteTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'sqlite'
    filename = 'tests/data/all-field-types.sqlite'
    override_fields = {'percent_column': fields.FloatField,
                       'bool_column': fields.IntegerField, }
    # SQLite does not support "Decimal" type, so `PercentField` will be
    # identified as a float and also does not support "boolean" type, so it's
    # saved as integer internally

    def test_imports(self):
        self.assertIs(rows.import_from_sqlite,
                      rows.plugins.sqlite.import_from_sqlite)
        self.assertIs(rows.export_to_sqlite,
                      rows.plugins.sqlite.export_to_sqlite)

    @mock.patch('rows.plugins.sqlite.create_table')
    def test_import_from_sqlite_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'encoding': 'test', 'some_key': 123, 'other': 456, }
        result = rows.import_from_sqlite(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'sqlite',
                          'filename': self.filename, }
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins.sqlite.create_table')
    def test_import_from_sqlite_retrieve_desired_data(self,
                                                      mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        table_1 = rows.import_from_sqlite(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args)

        # import using connection
        connection = sqlite3.connect(self.filename)
        table_2 = rows.import_from_sqlite(connection)
        call_args = mocked_create_table.call_args_list[1]
        self.assert_create_table_data(call_args, filename=connection)
        connection.close()

    def test_export_to_sqlite_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_sqlite(utils.table, temp.name)

        table = rows.import_from_sqlite(temp.name)
        self.assert_table_equal(table, utils.table)

    def test_export_to_sqlite_connection(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False, mode='wb')
        self.files_to_delete.append(temp.name)
        connection = sqlite3.connect(temp.name)
        rows.export_to_sqlite(utils.table, connection)
        connection.close()

        table = rows.import_from_sqlite(temp.name)
        self.assert_table_equal(table, utils.table)

    def test_export_to_sqlite_create_unique_table_name(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)

        first_table = utils.table
        second_table = utils.table + utils.table
        third_table = utils.table + utils.table + utils.table
        fourth_table = utils.table + utils.table + utils.table

        rows.export_to_sqlite(first_table, temp.name, table_name='rows')
        rows.export_to_sqlite(second_table, temp.name, table_name='rows')
        rows.export_to_sqlite(third_table, temp.name, table_name='test')
        rows.export_to_sqlite(fourth_table, temp.name, table_name='test')

        result_first_table = rows.import_from_sqlite(temp.name,
                                                     table_name='rows')
        result_second_table = rows.import_from_sqlite(temp.name,
                                                      table_name='rows_2')
        result_third_table = rows.import_from_sqlite(temp.name,
                                                     table_name='test')
        result_fourth_table = rows.import_from_sqlite(temp.name,
                                                      table_name='test_2')
        self.assert_table_equal(result_first_table, first_table)
        self.assert_table_equal(result_second_table, second_table)
        self.assert_table_equal(result_third_table, third_table)
        self.assert_table_equal(result_fourth_table, fourth_table)

    @mock.patch('rows.plugins.sqlite.serialize')
    def test_export_to_sqlite_uses_serialize(self, mocked_serialize):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        encoding = 'iso-8859-15'
        kwargs = {'test': 123, 'parameter': 3.14, }
        mocked_serialize.return_value = \
                iter(rows.plugins.utils.serialize(utils.table))

        rows.export_to_sqlite(utils.table, temp.name, encoding=encoding,
                              **kwargs)
        self.assertTrue(mocked_serialize.called)
        self.assertEqual(mocked_serialize.call_count, 1)

        call = mocked_serialize.call_args
        self.assertEqual(call[0], (utils.table, ))
        kwargs['encoding'] = encoding
        self.assertEqual(call[1], kwargs)
