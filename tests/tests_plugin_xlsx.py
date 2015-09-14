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

import rows
import utils
import rows.plugins.xlsx

class PluginXlsxTestCase(utils.RowsTestMixIn, unittest.TestCase):

    filename = 'tests/data/all-field-types.xlsx'

    def test_imports(self):
        self.assertIs(rows.import_from_xlsx, rows.plugins.xlsx.import_from_xlsx)

    def test_import_from_xlsx_filename(self):
        table = rows.import_from_xlsx(self.filename)

#        self.assert_table_equal(table, utils.table)

    def test_export_to_xlsix_fobj(self):
        export_filename = 'tests/data/all-field-types-export.xlsx'
        rows.export_to_xlsx(utils.table, export_filename)

        table = rows.import_from_xlsx(export_filename, sheet_name='Sheet1')
        self.assert_table_equal(table, utils.table)
