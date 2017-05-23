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

import string
import random
import tempfile
import unittest

from collections import OrderedDict
from io import BytesIO

import mock

import rows
import rows.plugins.dicts

from rows.table import LazyTable

import tests.utils as utils


class PluginDictTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'dicts'
    data = [{'name': 'Álvaro', 'ids': 123, 'number': 3, },
            {'name': 'Test', 'ids': '456', },  # missing 'number', 'ids' as str
            {'name': 'Python', 'ids': '123, 456', 'other': 3.14, },]

    def test_imports(self):
        self.assertIs(rows.import_from_dicts,
                      rows.plugins.dicts.import_from_dicts)
        self.assertIs(rows.export_to_dicts, rows.plugins.dicts.export_to_dicts)

    @mock.patch('rows.plugins.dicts.create_table')
    def test_import_from_dicts_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'some_key': 123, 'other': 456, }

        result = rows.import_from_dicts(self.data, **kwargs)

        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'dicts', }
        kwargs['samples'] = 1000
        self.assertEqual(call[1], kwargs)

    def test_import_from_dicts_return_desired_data(self):
        table = rows.import_from_dicts(self.data)

        self.assertEqual(len(table), 3)
        self.assertEqual(len(table.fields), 4)
        self.assertEqual(set(table.field_names),
                         set(['ids', 'name', 'number', 'other']))
        self.assertEqual(table.fields['name'], rows.fields.TextField)
        self.assertEqual(table.fields['ids'], rows.fields.TextField)
        self.assertEqual(table.fields['number'], rows.fields.IntegerField)
        self.assertEqual(table.fields['other'], rows.fields.FloatField)

        self.assertEqual(table[0].name, 'Álvaro')
        self.assertEqual(table[0].ids, '123')
        self.assertEqual(table[0].number, 3)
        self.assertEqual(table[0].other, None)
        self.assertEqual(table[1].name, 'Test')
        self.assertEqual(table[1].ids, '456')
        self.assertEqual(table[1].number, None)
        self.assertEqual(table[1].other, None)
        self.assertEqual(table[2].name, 'Python')
        self.assertEqual(table[2].ids, '123, 456')
        self.assertEqual(table[2].number, None)
        self.assertEqual(table[2].other, 3.14)

    def test_import_from_dicts_is_lazy(self):
        max_size = 1000
        samples = 200
        generator = utils.LazyDictGenerator(max_size)
        datagen = iter(generator)
        table = rows.import_from_dicts(datagen, lazy=True, samples=samples)
        self.assertTrue(isinstance(table, LazyTable))
        self.assertEqual(generator.last, samples - 1)

        data = list(table)
        self.assertTrue(len(data), max_size)
        self.assertEqual(generator.last, max_size - 1)

    def test_import_from_dicts_maintains_header_order(self):
        headers = list(string.ascii_lowercase)
        random.shuffle(headers)

        data = [
                OrderedDict([(header, 1) for header in headers]),
                OrderedDict([(header, 2) for header in headers]),
                OrderedDict([(header, 3) for header in headers]),
                OrderedDict([(header, 4) for header in headers]),
                OrderedDict([(header, 5) for header in headers]),
        ]
        table = rows.import_from_dicts(data)
        self.assertEqual(table.field_names, headers)

    def test_export_to_dicts(self):
        table = rows.import_from_dicts(self.data)
        result = rows.export_to_dicts(table)
        full_data = [
                {'name': 'Álvaro',
                 'ids': '123',
                 'number': 3,
                 'other': None, },
                {'name': 'Test',
                 'ids': '456',
                 'number': None,
                 'other': None, },
                {'name': 'Python',
                 'ids': '123, 456',
                 'number': None,
                 'other': 3.14, },]

        self.assertEqual(len(result), len(table))
        for expected, actual in zip(full_data, result):
            self.assertDictEqual(expected, actual)
