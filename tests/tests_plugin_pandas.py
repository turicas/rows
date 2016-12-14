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
import utils
from datetime import datetime as dt
from collections import OrderedDict

class PluginPandasTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'pandas'
    data_frame = pandas.DataFrame([[1, 2, 3, 4], [5, 6, 7, 8]],
                                  columns=['A', 'B', 'C', 'D'])

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
        #  turicas on Nov 4, 2015 Owner
        #
        # Since it was not imported from a file, filename key should be None.
        # kwargs['meta'] = {'imported_from': 'pandas', 'filename': 'DataFrame'}
        kwargs['meta'] = {'imported_from': 'PANDAS', 'filename': None}
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins._pandas.pandas.DataFrame')
    def test_export_to_pandas_uses_data_frame(self, mocked_data_frame):
        mocked_data_frame.return_value = 101
        result = rows.plugins._pandas.export_to_pandas(utils.table)
        self.assertTrue(mocked_data_frame.called)
        self.assertTrue(mocked_data_frame.call_count, 1)
        self.assertEqual(result, 101)

    # Data table with several different types
    data_dict = OrderedDict((
        (u"id", [1, 2, 3, 4, 5, 6]),
        (u"name", [u"John", u"Terry", u"Eric", u"Graham", u"Terry", u"Michael"]),
        (u"birth", [dt(1977, 1, 1, 15, 15), dt(1944, 9, 1, 15, 30),
                    dt(1969, 1, 5, 15, 44), dt(1937, 1, 13, 15, 13),
                    dt(1953, 10, 1, 5, 3), dt(1981, 5, 1, 15, 3)]),
        (u"height", [3.3, 1.67, 1.24, 5.12, 1.88, 1.89]),
        (u"is_vegan", [True, False, True, False, True, False])))


    def _compare_tables(self, df, rows_table):
        """Compares a rows.Table against a pandas.DataFrame for the sake of this test"""
        for h0, h1 in zip(rows_table.field_names, list(df)):
            # Header names match?
            self.assertEqual(h0, h1, '%s != %s' % (h0, h1))
        for row0, row1 in zip(rows_table, df.values):
            for cell0, cell1 in zip(row0, row1):
                # Cell values match?

                # print cell0, cell1
                self.assertEqual(cell0, cell1, '%s != %s' % (cell0, cell1))


    def test_import_from_pandas(self):
        df = pandas.DataFrame(self.data_dict)
        rows_table = rows.import_from_pandas(df)
        self._compare_tables(df, rows_table)


    def test_export_to_pandas(self):
        # This test creates a rows.Table from a PANDAS data frame,
        # then converts it back to a PANDAS data frame.
        df0 = pandas.DataFrame(self.data_dict)
        rows_table = rows.import_from_pandas(df0)
        df = rows.export_to_pandas(rows_table)
        self._compare_tables(df, rows_table)
