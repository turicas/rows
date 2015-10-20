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

import tempfile
import unittest

from io import BytesIO

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

    def test_export_to_xlsx_filename(self):
        temp = tempfile.NamedTemporaryFile()
        filename = temp.name + '.xlsx'
        temp.close()
        self.files_to_delete.append(filename)
        rows.export_to_xlsx(utils.table, filename)

        table = rows.import_from_xlsx(filename)
        self.assert_table_equal(table, utils.table)

        export_in_memory = rows.export_to_xlsx(utils.table, None)
        result_fobj = BytesIO()
        result_fobj.write(export_in_memory)
        result_fobj.seek(0)
        result_table = rows.import_from_xlsx(result_fobj)
        self.assert_table_equal(result_table, utils.table)

    def test_export_to_xlsx_fobj(self):
        temp = tempfile.NamedTemporaryFile()
        filename = temp.name + '.xlsx'
        temp.close()
        fobj = open(filename, 'wb')
        self.files_to_delete.append(filename)

        rows.export_to_xlsx(utils.table, fobj)
        fobj.close()

        table = rows.import_from_xlsx(filename)
        self.assert_table_equal(table, utils.table)

    @mock.patch('rows.plugins.xlsx.prepare_to_export')
    def test_export_to_xlsx_uses_prepare_to_export(self,
                                                   mocked_prepare_to_export):
        temp = tempfile.NamedTemporaryFile()
        filename = temp.name + '.xlsx'
        temp.file.close()
        fobj = open(filename, 'wb')
        self.files_to_delete.append(filename)

        kwargs = {'test': 123, 'parameter': 3.14, }
        mocked_prepare_to_export.return_value = \
                iter([utils.table.fields.keys()])

        rows.export_to_xlsx(utils.table, temp.name, **kwargs)
        self.assertTrue(mocked_prepare_to_export.called)
        self.assertEqual(mocked_prepare_to_export.call_count, 1)

        call = mocked_prepare_to_export.call_args
        self.assertEqual(call[0], (utils.table, ))
        self.assertEqual(call[1], kwargs)
