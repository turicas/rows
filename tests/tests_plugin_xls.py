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

import datetime
import tempfile
import time
import unittest

import mock

import rows
import rows.fields as fields
import rows.plugins.xls
import utils


def date_to_datetime(value):
    return datetime.datetime.fromtimestamp(time.mktime(value.timetuple()))


class PluginXlsTestCase(utils.RowsTestMixIn, unittest.TestCase):

    filename = 'tests/data/all-field-types.xls'

    def test_imports(self):
        self.assertIs(rows.import_from_xls, rows.plugins.xls.import_from_xls)
        self.assertIs(rows.export_to_xls, rows.plugins.xls.export_to_xls)

    def test_import_from_xls_filename(self):
        table = rows.import_from_xls(self.filename)

        self.assert_table_equal(table, utils.table)

        expected_meta = {'imported_from': 'xls', 'filename': self.filename,}
        self.assertEqual(table.meta, expected_meta)

    def test_import_from_xls_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        with open(self.filename, 'rb') as fobj:
            table = rows.import_from_xls(fobj)

        self.assert_table_equal(table, utils.table)

        expected_meta = {'imported_from': 'xls', 'filename': self.filename,}
        self.assertEqual(table.meta, expected_meta)

    @mock.patch('rows.plugins.xls.create_table')
    def test_import_from_xls_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'encoding': 'iso-8859-15', 'some_key': 123, 'other': 456, }
        result = rows.import_from_xls(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'xls', 'filename': self.filename, }
        self.assertEqual(call[1], kwargs)

    def test_export_to_xls_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_xls(utils.table, temp.name)

        table = rows.import_from_xls(temp.name)
        self.assert_table_equal(table, utils.table)

    def test_export_to_xls_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False, mode='wb')
        self.files_to_delete.append(temp.name)
        rows.export_to_xls(utils.table, temp.file)
        temp.file.close()

        table = rows.import_from_xls(temp.name)
        self.assert_table_equal(table, utils.table)
