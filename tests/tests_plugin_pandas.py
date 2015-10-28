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
import unittest
import mock

import pandas

import rows.plugins._pandas
import rows.plugins.csv
import utils

class PluginPandasTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'xls'
    filename = 'tests/data/all-field-types.csv'
    data_frame = pandas.read_csv(filename)
    table = rows.plugins.csv.import_from_csv(filename)

    def test_imports(self):
        self.assertIs(rows.import_from_pandas,
                rows.plugins._pandas.import_from_pandas)

    @mock.patch('rows.plugins._pandas.create_table')
    def test_import_from_pandas_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 101
        kwargs = {'encoding': 'test', 'some_key': 123, 'other': 456, }
        result = rows.import_from_pandas(self.data_frame, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 101)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'pandas', 'filename': 'DataFrame'}
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins._pandas.pandas.DataFrame')
    def test_export_to_pandas_uses_data_frame(self, mocked_data_frame):
        mocked_data_frame.return_value = 101
        result = rows.plugins._pandas.export_to_pandas(self.table)
        self.assertTrue(mocked_data_frame.called)
        self.assertTrue(mocked_data_frame.call_count, 1)
        self.assertEqual(result, 101)

