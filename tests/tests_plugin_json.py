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

import itertools
import json
import tempfile
import unittest

from textwrap import dedent

import mock

import rows
import utils


class PluginJsonTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'json'
    filename = 'tests/data/all-field-types.json'
    encoding = 'utf-8'

    def test_imports(self):
        self.assertIs(rows.import_from_json,
                      rows.plugins._json.import_from_json)
        self.assertIs(rows.export_to_json,
                      rows.plugins._json.export_to_json)

    @mock.patch('rows.plugins._json.create_table')
    def test_import_from_json_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'encoding': self.encoding, 'some_key': 123, 'other': 456, }
        result = rows.import_from_json(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'json', 'filename': self.filename, }
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins._json.create_table')
    def test_import_from_json_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        table_1 = rows.import_from_json(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args, field_ordering=False)

        # import using fobj
        with open(self.filename, 'rb') as fobj:
            table_2 = rows.import_from_json(fobj)
            call_args = mocked_create_table.call_args_list[1]
            self.assert_create_table_data(call_args, field_ordering=False)

    @mock.patch('rows.plugins._json.create_table')
    def test_import_from_json_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'encoding': 'iso-8859-15', 'some_key': 123, 'other': 456, }
        result = rows.import_from_json(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'json', 'filename': self.filename, }
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins._json.prepare_to_export')
    def test_export_to_json_uses_prepare_to_export(self,
            mocked_prepare_to_export):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        kwargs = {'test': 123, 'parameter': 3.14, }
        mocked_prepare_to_export.return_value = \
                iter([utils.table.fields.keys()])

        rows.export_to_json(utils.table, temp.name, **kwargs)
        self.assertTrue(mocked_prepare_to_export.called)
        self.assertEqual(mocked_prepare_to_export.call_count, 1)

        call = mocked_prepare_to_export.call_args
        self.assertEqual(call[0], (utils.table, ))
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins._json.export_data')
    def test_export_to_json_uses_export_data(self, mocked_export_data):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        kwargs = {'test': 123, 'parameter': 3.14, }
        mocked_export_data.return_value = 42

        result = rows.export_to_json(utils.table, temp.name, **kwargs)
        self.assertTrue(mocked_export_data.called)
        self.assertEqual(mocked_export_data.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_export_data.call_args
        self.assertEqual(call[0][0], temp.name)
        self.assertEqual(call[1], {})

    def test_export_to_json_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_json(utils.table, temp.name)
        table = rows.import_from_json(temp.name)
        self.assert_table_equal(table, utils.table)

    def test_export_to_json_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_json(utils.table, temp.file)

        table = rows.import_from_json(temp.name)
        self.assert_table_equal(table, utils.table)

    def test_export_to_json_filename_save_data_in_correct_format(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)

        rows.export_to_json(utils.table, temp.name)

        with open(temp.name, 'rb') as fobj:
            imported_json = json.load(fobj)

        for row in imported_json:
            self.assertEqual(type(row['float_column']), float)
            self.assertEqual(type(row['decimal_column']), float)
            self.assertEqual(type(row['bool_column']), bool)
            self.assertEqual(type(row['integer_column']), int)
            self.assertEqual(type(row['date_column']), unicode)
            self.assertEqual(type(row['datetime_column']), unicode)
            self.assertEqual(type(row['percent_column']), unicode)
            self.assertEqual(type(row['unicode_column']), unicode)
            self.assertEqual(type(row['null_column']), unicode)

    def test_export_to_json_indent(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)

        table = rows.Table(fields=utils.table.fields)
        table.append(utils.table[0]._asdict())
        rows.export_to_json(table, temp.name, indent=2)

        temp.file.seek(0)
        result = temp.file.read().strip().replace('\r\n', '\n').splitlines()
        self.assertEqual(result[0], '[')
        self.assertEqual(result[1], '  {')
        for line in result[2:-2]:
            self.assertTrue(line.startswith('    '))
        self.assertEqual(result[-2], '  }')
        self.assertEqual(result[-1], ']')
