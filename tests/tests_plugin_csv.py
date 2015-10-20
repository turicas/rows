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
import rows.plugins.csv
import utils


def make_csv_data(quote_char, field_delimiter, line_delimiter):
    data = [['field1', 'field2', 'field3'],
            ['value1', 'value2', 'value3']]
    lines = [['{}{}{}'.format(quote_char, value, quote_char)
              for value in line]
             for line in data]
    lines = line_delimiter.join([field_delimiter.join(line)
                                 for line in data])
    return data, lines


class PluginCsvTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'csv'
    filename = 'tests/data/all-field-types.csv'
    encoding = 'utf-8'

    def test_imports(self):
        self.assertIs(rows.import_from_csv, rows.plugins.csv.import_from_csv)
        self.assertIs(rows.export_to_csv, rows.plugins.csv.export_to_csv)

    @mock.patch('rows.plugins.csv.create_table')
    def test_import_from_csv_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'encoding': 'utf-8', 'some_key': 123, 'other': 456, }
        result = rows.import_from_csv(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'csv', 'filename': self.filename, }
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins.csv.create_table')
    def test_import_from_csv_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        table_1 = rows.import_from_csv(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args)

        # import using fobj
        with open(self.filename, 'rb') as fobj:
            table_2 = rows.import_from_csv(fobj)
            call_args = mocked_create_table.call_args_list[1]
            self.assert_create_table_data(call_args)

    @mock.patch('rows.plugins.csv.create_table')
    def test_import_from_csv_discover_dialect(self, mocked_create_table):
        data, lines = make_csv_data(quote_char="'",
                                    field_delimiter=";",
                                    line_delimiter="\r\n")
        fobj = BytesIO()
        fobj.write(lines.encode('utf-8'))
        fobj.seek(0)

        rows.import_from_csv(fobj)
        call_args = mocked_create_table.call_args_list[0]
        self.assertEqual(data, list(call_args[0][0]))

    @mock.patch('rows.plugins.csv.create_table')
    def test_import_from_csv_force_dialect(self, mocked_create_table):
        data, lines = make_csv_data(quote_char="'",
                                    field_delimiter="\t",
                                    line_delimiter="\r\n")
        fobj = BytesIO()
        fobj.write(lines.encode('utf-8'))
        fobj.seek(0)

        rows.import_from_csv(fobj, dialect='excel-tab')
        call_args = mocked_create_table.call_args_list[0]
        self.assertEqual(data, list(call_args[0][0]))

    @mock.patch('rows.plugins.csv.serialize')
    def test_export_to_csv_uses_serialize(self, mocked_serialize):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        kwargs = {'test': 123, 'parameter': 3.14, 'encoding': 'utf-8', }
        mocked_serialize.return_value = iter([utils.table.fields.keys()])

        rows.export_to_csv(utils.table, temp.name, **kwargs)
        self.assertTrue(mocked_serialize.called)
        self.assertEqual(mocked_serialize.call_count, 1)

        call = mocked_serialize.call_args
        self.assertEqual(call[0], (utils.table, ))
        self.assertEqual(call[1], kwargs)

    def test_export_to_csv_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_csv(utils.table, temp.name)

        table = rows.import_from_csv(temp.name)
        self.assert_table_equal(table, utils.table)

        temp.file.seek(0)
        result = temp.file.read()
        export_in_memory = rows.export_to_csv(utils.table, None)
        self.assertEqual(result, export_in_memory)

    def test_export_to_csv_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_csv(utils.table, temp.file)

        table = rows.import_from_csv(temp.name)
        self.assert_table_equal(table, utils.table)
