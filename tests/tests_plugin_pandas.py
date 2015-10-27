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

import rows.plugins.pandas
import utils

class PluginPandasTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'xls'
    filename = 'tests/data/all-field-types.csv'

    def test_imports(self):
        self.assertIs(rows.import_from_pandas,
                rows.plugins.pandas.import_from_pandas)

    def test_import_from_pandas(self):
        pass

