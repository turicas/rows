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
import tempfile
import unittest

import mock

import rows
import rows.plugins.xlsx
import utils


class PluginXlsxTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'xlsx'
    filename = 'tests/data/all-field-types.xlsx'

    def test_imports(self):
        self.assertIs(rows.import_from_xlsx, rows.plugins.xlsx.import_from_xlsx)

    @mock.patch('rows.plugins.xlsx.create_table')
    def test_import_from_xlsx_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'encoding': 'iso-8859-15', 'some_key': 123, 'other': 456, }
        result = rows.import_from_xlsx(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'xlsx', 'filename': self.filename, }
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins.xlsx.create_table')
    def test_import_from_xlsx_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        table_1 = rows.import_from_xlsx(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args)

        # import using fobj
        with open(self.filename, 'rb') as fobj:
            table_2 = rows.import_from_xlsx(fobj)
        call_args = mocked_create_table.call_args_list[1]
        self.assert_create_table_data(call_args)

#    def test_export_to_xlsx_fobj(self):
#        export_filename = 'tests/data/all-field-types-export.xlsx'
#        rows.export_to_xlsx(utils.table, export_filename)
#
#        table = rows.import_from_xlsx(export_filename, sheet_name='Sheet1')
#        self.assert_table_equal(table, utils.table)

    def test_export_to_xlsx_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name + ".xlsx")
        rows.export_to_xlsx(utils.table, temp.name + ".xlsx")

        table = rows.import_from_xlsx(temp.name + ".xlsx")
        self.assert_table_equal(table, utils.table)

    def test_export_to_xlsx_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False, mode='wb')
        file_name = temp.name + ".xlsx"
        fobj = open(file_name, 'wb')
        self.files_to_delete.append(temp.name + ".xlsx")
        self.files_to_delete.append(temp.name)
        rows.export_to_xlsx(utils.table, fobj)
        temp.file.close()
        fobj.close()
        table = rows.import_from_xlsx(file_name)
        self.assert_table_equal(table, utils.table)
