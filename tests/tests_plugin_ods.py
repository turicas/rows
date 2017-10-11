# coding: utf-8

"""Copyright 2014-2017 Álvaro Justen <https://github.com/turicas/rows/>

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU Lesser General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU Lesser General Public License for more details.

   You should have received a copy of the GNU Lesser General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>."""

from __future__ import unicode_literals

import unittest

import mock

import rows
import rows.plugins.ods
import tests.utils as utils


class PluginOdsTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'ods'
    filename = 'tests/data/all-field-types.ods'
    assert_meta_encoding = False

    def test_imports(self):
        self.assertIs(rows.import_from_ods, rows.plugins.ods.import_from_ods)

    @mock.patch('rows.plugins.ods.create_table')
    def test_import_from_ods_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'encoding': 'test', 'some_key': 123, 'other': 456, }
        result = rows.import_from_ods(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'ods', 'filename': self.filename, }
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins.ods.create_table')
    def test_import_from_ods_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        rows.import_from_ods(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args)

        # import using fobj
        with open(self.filename, 'rb') as fobj:
            rows.import_from_ods(fobj)
            call_args = mocked_create_table.call_args_list[1]
            self.assert_create_table_data(call_args)
