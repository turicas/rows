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

import mock

import rows
import rows.plugins.txt
from . import utils


class PluginTxtTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'txt'
    filename = 'tests/data/all-field-types.txt'
    encoding = 'utf-8'

    def test_imports(self):
        self.assertIs(rows.import_from_txt, rows.plugins.txt.import_from_txt)
        self.assertIs(rows.export_to_txt, rows.plugins.txt.export_to_txt)

    @mock.patch('rows.plugins.txt.create_table')
    def test_import_from_txt_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'encoding': self.encoding, 'some_key': 123, 'other': 456, }
        result = rows.import_from_txt(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'txt', 'filename': self.filename, }
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins.txt.create_table')
    def test_import_from_txt_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        table_1 = rows.import_from_txt(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args)

        # import using fobj
        with open(self.filename, 'rb') as fobj:
            table_2 = rows.import_from_txt(fobj)
            call_args = mocked_create_table.call_args_list[1]
            self.assert_create_table_data(call_args)

    @mock.patch('rows.plugins.txt.serialize')
    def test_export_to_txt_uses_serialize(self, mocked_serialize):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        kwargs = {'encoding': 'utf-8', 'test': 123, 'parameter': 3.14, }
        mocked_serialize.return_value = iter([list(utils.table.fields.keys())])

        rows.export_to_txt(utils.table, temp.name, **kwargs)
        self.assertTrue(mocked_serialize.called)
        self.assertEqual(mocked_serialize.call_count, 1)

        call = mocked_serialize.call_args
        self.assertEqual(call[0], (utils.table, ))
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins.txt.export_data')
    def test_export_to_txt_uses_export_data(self, mocked_export_data):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        kwargs = {'encoding': 'utf-8', 'test': 123, 'parameter': 3.14, }
        mocked_export_data.return_value = 42

        result = rows.export_to_txt(utils.table, temp.name, **kwargs)
        self.assertTrue(mocked_export_data.called)
        self.assertEqual(mocked_export_data.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_export_data.call_args
        self.assertEqual(call[0][0], temp.name)
        self.assertEqual(call[1], {})

    def test_export_to_txt_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_txt(utils.table, temp.name)

        table = rows.import_from_txt(temp.name)
        self.assert_table_equal(table, utils.table)

        with open(temp.name) as fobj:
            content = fobj.read()
        self.assertEqual(content[-10:].count('\n'), 1)

    def test_export_to_txt_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_txt(utils.table, temp.file)

        table = rows.import_from_txt(temp.name)
        self.assert_table_equal(table, utils.table)
