# coding: utf-8

# Copyright 2014-2017 Álvaro Justen <https://github.com/turicas/rows/>

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

import sys
import tempfile
import unittest
from collections import OrderedDict

import mock
import six

import rows
import rows.plugins.txt
import tests.utils as utils


class PluginTxtTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = "txt"
    file_extension = "txt"
    filename = "tests/data/all-field-types.txt"
    encoding = "utf-8"

    def test_imports(self):
        self.assertIs(rows.import_from_txt, rows.plugins.txt.import_from_txt)
        self.assertIs(rows.export_to_txt, rows.plugins.txt.export_to_txt)

    @mock.patch("rows.plugins.txt.create_table")
    def test_import_from_txt_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {"some_key": 123, "other": 456}
        result = rows.import_from_txt(self.filename, encoding=self.encoding, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        called_data = call[1]
        meta = called_data.pop("meta")
        self.assertEqual(call[1], kwargs)

        source = meta.pop("source")
        self.assertEqual(source.uri, self.filename)

        expected_meta = {
            "imported_from": "txt",
            "frame_style": "ascii",
        }
        self.assertDictEqual(expected_meta, meta)

    @mock.patch("rows.plugins.txt.create_table")
    def test_import_from_txt_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        rows.import_from_txt(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args)

        # import using fobj
        with open(self.filename, mode="rb") as fobj:
            rows.import_from_txt(fobj)
            call_args = mocked_create_table.call_args_list[1]
            self.assert_create_table_data(call_args)

    @mock.patch("rows.plugins.txt.serialize")
    def test_export_to_txt_uses_serialize(self, mocked_serialize):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        kwargs = {"test": 123, "parameter": 3.14}
        mocked_serialize.return_value = iter([utils.table.fields.keys()])

        rows.export_to_txt(utils.table, temp.name, encoding=self.encoding, **kwargs)
        self.assertTrue(mocked_serialize.called)
        self.assertEqual(mocked_serialize.call_count, 1)

        call = mocked_serialize.call_args
        self.assertEqual(call[0], (utils.table,))
        self.assertEqual(call[1], kwargs)

    @mock.patch("rows.plugins.txt.export_data")
    def test_export_to_txt_uses_export_data(self, mocked_export_data):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        kwargs = {"test": 123, "parameter": 3.14}
        mocked_export_data.return_value = 42

        result = rows.export_to_txt(
            utils.table, temp.name, encoding=self.encoding, **kwargs
        )
        self.assertTrue(mocked_export_data.called)
        self.assertEqual(mocked_export_data.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_export_data.call_args
        self.assertEqual(call[0][0], temp.name)
        self.assertEqual(call[1], {"mode": "wb"})

    def test_export_to_txt_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_txt(utils.table, temp.name, encoding="utf-8")

        table = rows.import_from_txt(temp.name, encoding="utf-8")
        self.assert_table_equal(table, utils.table)

        with open(temp.name, mode="rb") as fobj:
            content = fobj.read()
        self.assertEqual(content[-10:].count(b"\n"), 1)

    def test_export_to_txt_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_txt(utils.table, temp.file, encoding="utf-8")

        table = rows.import_from_txt(temp.name, encoding="utf-8")
        self.assert_table_equal(table, utils.table)

    def test_issue_168(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        filename = "{}.{}".format(temp.name, self.file_extension)
        self.files_to_delete.append(filename)

        table = rows.Table(fields=OrderedDict([("jsoncolumn", rows.fields.JSONField)]))
        table.append({"jsoncolumn": '{"python": 42}'})
        rows.export_to_txt(table, filename, encoding="utf-8")

        table2 = rows.import_from_txt(filename, encoding="utf-8")
        self.assert_table_equal(table, table2)

    def test_export_to_text_should_return_unicode(self):
        result = rows.export_to_txt(utils.table)
        self.assertEqual(type(result), six.text_type)

    def _test_export_to_txt_frame_style(self, frame_style, chars, positive=True):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_txt(
            utils.table, temp.file, encoding="utf-8", frame_style=frame_style
        )

        if sys.version_info.major < 3:
            from io import open as open_
        else:
            open_ = open

        file_data = open_(temp.name, "rt", encoding="utf-8").read()

        for char in chars:
            if positive:
                self.assertIn(char, file_data)
            else:
                self.assertNotIn(char, file_data)

    def test_export_to_txt_frame_style_ASCII(self):
        self._test_export_to_txt_frame_style(frame_style="ASCII", chars="+-|")

    def test_export_to_txt_frame_style_single(self):
        self._test_export_to_txt_frame_style(frame_style="single", chars="│┤┐└┬├─┼┘┌")

    def test_export_to_txt_frame_style_double(self):
        self._test_export_to_txt_frame_style(frame_style="double", chars="╣║╗╝╚╔╩╦╠═╬")

    def test_export_to_txt_frame_style_none(self):
        self._test_export_to_txt_frame_style(
            frame_style="None", chars="|│┤┐└┬├─┼┘┌╣║╗╝╚╔╩╦╠═╬", positive=False
        )

    @staticmethod
    def _reset_txt_plugin():
        # The txt plugin makes (or can make use) of 'defaultdict's
        # and perform certain operations against their existing values.
        # Those existing values may change if certain txt operations
        # are performed in the same proccess.
        # Therefore, some tests have to run against
        # pristine copies of rows.plugins.txt
        try:
            from imp import reload
        except ImportError:
            pass
        import rows.plugins.txt

        original_txt_plugin = rows.plugins.txt
        reload(rows.plugins.txt)
        rows.import_from_txt = rows.plugins.txt.import_from_txt
        rows.export_to_txt = rows.plugins.txt.export_to_txt
        original_txt_plugin.FRAME_SENTINEL = rows.plugins.txt.FRAME_SENTINEL

    def _test_import_from_txt_works_with_custom_frame(self, frame_style):
        temp = tempfile.NamedTemporaryFile(delete=False)

        original_data = rows.import_from_txt(self.filename)
        rows.export_to_txt(
            utils.table, temp.file, encoding="utf-8", frame_style=frame_style
        )

        self._reset_txt_plugin()
        new_data = rows.import_from_txt(temp.name)

        self.assertEqual(
            list(new_data),
            list(original_data),
            msg='failed to read information with frame_style == "{0}"'.format(
                frame_style
            ),
        )

    def test_import_from_txt_works_with_ASCII_frame(self):
        self._test_import_from_txt_works_with_custom_frame("ASCII")

    def test_import_from_txt_works_with_unicode_single_frame(self):
        self._test_import_from_txt_works_with_custom_frame("single")

    def test_import_from_txt_works_with_unicode_double_frame(self):
        self._test_import_from_txt_works_with_custom_frame("double")

    def test_import_from_txt_works_with_no_frame(self):
        self._test_import_from_txt_works_with_custom_frame("None")

    def test__parse_col_positions(self):
        result1 = rows.plugins.txt._parse_col_positions("ASCII", "|----|----|")
        self.assertEqual(result1, [0, 5, 10])
        result2 = rows.plugins.txt._parse_col_positions("None", "  col1   col2  ")
        self.assertEqual(result2, [0, 7, 14])
