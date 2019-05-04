# coding: utf-8

# Copyright 2014-2019 Álvaro Justen <https://github.com/turicas/rows/>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import json
import tempfile
import unittest
from collections import Counter, OrderedDict, defaultdict

import mock
import six

import rows
import tests.utils as utils
from rows.utils import Source


class PluginJsonTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = "json"
    file_extension = "json"
    filename = "tests/data/all-field-types.json"
    encoding = "utf-8"
    expected_meta = {
        "imported_from": "json",
        "source": Source(uri=filename, plugin_name=plugin_name, encoding=encoding)
    }

    def test_imports(self):
        self.assertIs(rows.import_from_json, rows.plugins.plugin_json.import_from_json)
        self.assertIs(rows.export_to_json, rows.plugins.plugin_json.export_to_json)

    @mock.patch("rows.plugins.plugin_json.create_table")
    def test_import_from_json_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {"some_key": 123, "other": 456}
        result = rows.import_from_json(self.filename, encoding=self.encoding, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

    @mock.patch("rows.plugins.plugin_json.create_table")
    def test_import_from_json_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        rows.import_from_json(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args, field_ordering=False, expected_meta=self.expected_meta)

        # import using fobj
        with open(self.filename) as fobj:
            rows.import_from_json(fobj)
            call_args = mocked_create_table.call_args_list[1]
            self.assert_create_table_data(call_args, field_ordering=False, expected_meta=self.expected_meta)

    @mock.patch("rows.plugins.plugin_json.prepare_to_export")
    def test_export_to_json_uses_prepare_to_export(self, mocked_prepare_to_export):
        temp = tempfile.NamedTemporaryFile(delete=False, mode="wb")
        self.files_to_delete.append(temp.name)
        kwargs = {"test": 123, "parameter": 3.14}
        mocked_prepare_to_export.return_value = iter([utils.table.fields.keys()])

        rows.export_to_json(utils.table, temp.name, **kwargs)
        self.assertTrue(mocked_prepare_to_export.called)
        self.assertEqual(mocked_prepare_to_export.call_count, 1)

        call = mocked_prepare_to_export.call_args
        self.assertEqual(call[0], (utils.table,))
        self.assertEqual(call[1], kwargs)

    def test_export_to_json_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False, mode="wb")
        self.files_to_delete.append(temp.name)
        rows.export_to_json(utils.table, temp.name)
        table = rows.import_from_json(temp.name)
        self.assert_table_equal(table, utils.table)

    def test_export_to_json_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False, mode="wb")
        self.files_to_delete.append(temp.name)
        rows.export_to_json(utils.table, temp.file)

        table = rows.import_from_json(temp.name)
        self.assert_table_equal(table, utils.table)

    def test_export_to_json_filename_save_data_in_correct_format(self):
        temp = tempfile.NamedTemporaryFile(delete=False, mode="wb")
        self.files_to_delete.append(temp.name)

        rows.export_to_json(utils.table, temp.name)

        with open(temp.name) as fobj:
            imported_json = json.load(fobj)

        COLUMN_TYPE = {
            "float_column": float,
            "decimal_column": float,
            "bool_column": bool,
            "integer_column": int,
            "date_column": six.text_type,
            "datetime_column": six.text_type,
            "percent_column": six.text_type,
            "unicode_column": six.text_type,
        }
        field_types = defaultdict(list)
        for row in imported_json:
            for field_name, value in row.items():
                field_types[field_name].append(type(value))
        # We test if the JSON was created serializing all the fields correctly
        # (some as native JSON values, like int and float) and others needed to
        # be serialized, like date, datetime etc.
        for field_name, value_types in field_types.items():
            if field_name != "unicode_column":
                self.assertEqual(
                    Counter(value_types),
                    Counter({type(None): 1, COLUMN_TYPE[field_name]: 6}),
                )
            else:
                self.assertEqual(
                    Counter(value_types), Counter({COLUMN_TYPE[field_name]: 7})
                )

    def test_export_to_json_indent(self):
        temp = tempfile.NamedTemporaryFile(delete=False, mode="rb+")
        self.files_to_delete.append(temp.name)

        table = rows.Table(fields=utils.table.fields)
        table.append(utils.table[0]._asdict())
        rows.export_to_json(table, temp.name, indent=2)

        temp.file.seek(0)
        result = temp.file.read().strip().replace(b"\r\n", b"\n").splitlines()
        self.assertEqual(result[0], b"[")
        self.assertEqual(result[1], b"  {")
        for line in result[2:-2]:
            self.assertTrue(line.startswith(b"    "))
        self.assertEqual(result[-2], b"  }")
        self.assertEqual(result[-1], b"]")

    def test_issue_168(self):
        temp = tempfile.NamedTemporaryFile(delete=False, mode="wb")
        filename = "{}.{}".format(temp.name, self.file_extension)
        self.files_to_delete.append(filename)

        table = rows.Table(fields=OrderedDict([("jsoncolumn", rows.fields.JSONField)]))
        table.append({"jsoncolumn": '{"python": 42}'})
        rows.export_to_json(table, filename)

        table2 = rows.import_from_json(filename)
        self.assert_table_equal(table, table2)
