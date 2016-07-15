# coding: utf-8

# Copyright 2014-2016 Álvaro Justen <https://github.com/turicas/rows/>
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
import rows.plugins.ofx
import utils


class PluginOfxTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'ofx'
    filename = 'tests/data/sample.ofx'  # TODO: may use also sample2.ofx

    def test_imports(self):
        self.assertIs(rows.import_from_ofx, rows.plugins.ofx.import_from_ofx)

    @mock.patch('rows.plugins.ofx.create_table')
    def test_import_from_ofx_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'some_key': 123, 'other': 456, }
        result = rows.import_from_ofx(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'ofx', 'filename': self.filename, }
        self.assertEqual(call[1], kwargs)

    def assert_row_data(self, data):
        # TODO: implement
        pass

    @mock.patch('rows.plugins.ofx.create_table')
    def test_import_from_ofx_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        table_1 = rows.import_from_ofx(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_table_meta_data(call_args)
        self.assert_row_data(call_args[0][0])

        # import using fobj
        with open(self.filename, 'rb') as fobj:
            table_2 = rows.import_from_ofx(fobj)
            call_args = mocked_create_table.call_args_list[1]
            self.assert_table_meta_data(call_args)
            self.assert_row_data(call_args[0][0])
