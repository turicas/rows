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
import rows.plugins.csv
import utils


class PluginCsvTestCase(utils.RowsTestMixIn, unittest.TestCase):

    filename = 'tests/data/all-field-types.csv'
    encoding = 'utf-8'

    def test_imports(self):
        self.assertIs(rows.import_from_csv, rows.plugins.csv.import_from_csv)
        self.assertIs(rows.export_to_csv, rows.plugins.csv.export_to_csv)

    def test_import_from_csv_filename(self):
        table = rows.import_from_csv(self.filename, encoding=self.encoding)
        self.assert_table_equal(table, utils.table)

        expected_meta = {'imported_from': 'csv', 'filename': self.filename,}
        self.assertEqual(table.meta, expected_meta)

    def test_import_from_csv_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        with open(self.filename) as fobj:
            table = rows.import_from_csv(fobj, encoding=self.encoding)
        self.assert_table_equal(table, utils.table)

        expected_meta = {'imported_from': 'csv', 'filename': self.filename,}
        self.assertEqual(table.meta, expected_meta)

    @mock.patch('rows.plugins.csv.create_table')
    def test_import_from_csv_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'encoding': 'test', 'some_key': 123, 'other': 456, }
        result = rows.import_from_csv(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'csv', 'filename': self.filename, }
        self.assertEqual(call[1], kwargs)

    def test_export_to_csv_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_csv(utils.table, temp.name)

        table = rows.import_from_csv(temp.name)
        self.assert_table_equal(table, utils.table)

    def test_export_to_csv_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_csv(utils.table, temp.file)

        table = rows.import_from_csv(temp.name)
        self.assert_table_equal(table, utils.table)

    @mock.patch('rows.plugins.csv.serialize')
    def test_export_to_csv_uses_serialize(self, mocked_serialize):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        encoding = 'iso-8859-15'
        kwargs = {'test': 123, 'parameter': 3.14, }
        mocked_serialize.return_value = iter([['field1', 'field2']])

        rows.export_to_csv(utils.table, temp.name, encoding=encoding,
                           **kwargs)
        self.assertTrue(mocked_serialize.called)
        self.assertEqual(mocked_serialize.call_count, 1)

        call = mocked_serialize.call_args
        self.assertEqual(call[0], (utils.table, ))
        kwargs['encoding'] = encoding
        self.assertEqual(call[1], kwargs)
