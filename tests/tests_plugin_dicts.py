# coding: utf-8

# Copyright 2014-2025 Álvaro Justen <https://github.com/turicas/rows/>
#    This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
#    Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
#    any later version.
#    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
#    warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
#    more details.
#    You should have received a copy of the GNU Lesser General Public License along with this program.  If not, see
#    <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import random
import string
import unittest
from collections import OrderedDict

try:
    import mock
except ImportError:
    from unittest import mock

import rows
import tests.utils as utils

ALIAS_IMPORT, ALIAS_EXPORT = rows.import_from_dicts, rows.export_to_dicts  # Lazy functions (just aliases)


class PluginDictTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = "dicts"
    data = [
        {"name": "Álvaro", "ids": 123, "number": 3},
        {"name": "Test", "ids": "456"},  # missing 'number', 'ids' as str
        {"name": "Python", "ids": "123, 456", "other": 3.14},
    ]

    def test_imports(self):
        # Force the plugin to load
        original_import, original_export = rows.plugins.dicts.import_from_dicts, rows.plugins.dicts.export_to_dicts
        assert id(ALIAS_IMPORT) != id(original_import)
        assert id(ALIAS_EXPORT) != id(original_export)
        new_alias_import, new_alias_export = rows.import_from_dicts, rows.export_to_dicts
        assert id(new_alias_import) == id(original_import)  # Function replaced with loaded one
        assert id(new_alias_export) == id(original_export)  # Function replaced with loaded one

    @mock.patch("rows.plugins.utils.create_table")
    def test_import_from_dicts_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {"some_key": 123, "other": 456}

        result = rows.import_from_dicts(self.data, **kwargs)

        assert mocked_create_table.called
        assert mocked_create_table.call_count == 1
        assert result == 42

        call = mocked_create_table.call_args
        kwargs["meta"] = {"imported_from": "dicts"}
        kwargs["samples"] = rows.compat.DEFAULT_SAMPLE_ROWS
        assert call[1] == kwargs

    def test_import_from_dicts_return_desired_data(self):
        table = rows.import_from_dicts(self.data)

        assert len(table) == 3
        assert len(table.fields) == 4
        assert set(table.field_names) == set(["ids", "name", "number", "other"])
        assert table.fields["name"] == rows.fields.TextField
        assert table.fields["ids"] == rows.fields.TextField
        assert table.fields["number"] == rows.fields.IntegerField
        assert table.fields["other"] == rows.fields.FloatField

        assert table[0].name == "Álvaro"
        assert table[0].ids == "123"
        assert table[0].number == 3
        assert table[0].other is None
        assert table[1].name == "Test"
        assert table[1].ids == "456"
        assert table[1].number is None
        assert table[1].other is None
        assert table[2].name == "Python"
        assert table[2].ids == "123, 456"
        assert table[2].number is None
        assert table[2].other == 3.14

    def test_import_from_dicts_accepts_generator(self):
        max_size = 1000
        samples = 200
        generator = utils.LazyDictGenerator(max_size)
        datagen = iter(generator)
        table = rows.import_from_dicts(datagen, lazy=True, samples=samples)
        # `create_table` will consume the whole generator
        assert generator.last == max_size - 1

        data = list(table)
        assert len(data) == max_size
        assert generator.last == max_size - 1

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
        assert table.field_names == headers

    def test_export_to_dicts(self):
        table = rows.import_from_dicts(self.data)
        result = rows.export_to_dicts(table)
        full_data = [
            {"name": "Álvaro", "ids": "123", "number": 3, "other": None},
            {"name": "Test", "ids": "456", "number": None, "other": None},
            {"name": "Python", "ids": "123, 456", "number": None, "other": 3.14},
        ]

        assert len(result) == len(table)
        for expected, actual in zip(full_data, result):
            self.assertDictEqual(expected, actual)
