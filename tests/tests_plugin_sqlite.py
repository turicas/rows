# coding: utf-8

# Copyright 2014-2016 Álvaro Justen <https://github.com/turicas/rows/>
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

from collections import OrderedDict

import mock

import rows
import rows.plugins.sqlite
import rows.plugins.utils
import tests.utils as utils

from rows import fields


class PluginSqliteTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'sqlite'
    file_extension = 'sqlite'
    filename = 'tests/data/all-field-types.sqlite'
    assert_meta_encoding = False
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

    def test_sqlite_injection(self):
        connection = rows.export_to_sqlite(utils.table, ':memory:')
        with self.assertRaises(ValueError):
            rows.import_from_sqlite(connection,
                                    table_name='table1", "sqlite_master')

        with self.assertRaises(ValueError):
            rows.export_to_sqlite(utils.table, ':memory:',
                                  table_name='table1", "sqlite_master')

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

        rows.export_to_sqlite(first_table, temp.name)  # table1
        rows.export_to_sqlite(second_table, temp.name)  # table2

        result_first_table = rows.import_from_sqlite(temp.name,
                                                     table_name='table1')
        result_second_table = rows.import_from_sqlite(temp.name,
                                                      table_name='table2')
        self.assert_table_equal(result_first_table, first_table)
        self.assert_table_equal(result_second_table, second_table)

    def test_export_to_sqlite_forcing_table_name_appends_rows(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)

        rows.export_to_sqlite(utils.table, temp.name, table_name='rows')
        rows.export_to_sqlite(utils.table, temp.name, table_name='rows')

        result_table = rows.import_from_sqlite(temp.name, table_name='rows')

        self.assertEqual(len(result_table), 2 * len(utils.table))
        self.assert_table_equal(result_table, utils.table + utils.table)

    @mock.patch('rows.plugins.sqlite.prepare_to_export')
    def test_export_to_sqlite_uses_prepare_to_export(self,
            mocked_prepare_to_export):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        encoding = 'iso-8859-15'
        kwargs = {'test': 123, 'parameter': 3.14, }
        mocked_prepare_to_export.return_value = \
                iter(rows.plugins.utils.prepare_to_export(utils.table))

        rows.export_to_sqlite(utils.table, temp.name, encoding=encoding,
                              **kwargs)
        self.assertTrue(mocked_prepare_to_export.called)
        self.assertEqual(mocked_prepare_to_export.call_count, 1)

        call = mocked_prepare_to_export.call_args
        self.assertEqual(call[0], (utils.table, ))
        kwargs['encoding'] = encoding
        self.assertEqual(call[1], kwargs)

    def test_issue_170(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)

        table = rows.Table(fields=
                OrderedDict([('intvalue', rows.fields.IntegerField),
                             ('floatvalue', rows.fields.FloatField)]))
        table.append({'intvalue': 42, 'floatvalue': 3.14})
        table.append({'intvalue': None, 'floatvalue': None})

        # should not raise an exception
        rows.export_to_sqlite(table, temp.name)

    def test_issue_168(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        filename = '{}.{}'.format(temp.name, self.file_extension)
        self.files_to_delete.append(filename)

        table = rows.Table(fields=
                OrderedDict([('jsoncolumn', rows.fields.JSONField)]))
        table.append({'jsoncolumn': '{"python": 42}'})
        rows.export_to_sqlite(table, filename)

        table2 = rows.import_from_sqlite(filename)
        self.assert_table_equal(table, table2)
