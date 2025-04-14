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

import io
import sys
import tempfile
import unittest
from collections import OrderedDict
from pathlib import Path

import mock
import pytest

import rows
import tests.utils as utils
from rows.utils import Source
from rows.compat import TEXT_TYPE

ALIAS_IMPORT, ALIAS_EXPORT = rows.import_from_txt, rows.export_to_txt  # Lazy functions (just aliases)

class PluginTxtTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = "txt"
    file_extension = "txt"
    filename = "tests/data/all-field-types.txt"
    encoding = "utf-8"
    expected_meta = {
        "imported_from": "txt",
        "frame_style": "ascii",
        "source": Source(uri=filename, plugin_name=plugin_name, encoding=encoding),
    }

    def test_imports(self):
        # Force the plugin to load
        original_import, original_export = rows.plugins.txt.import_from_txt, rows.plugins.txt.export_to_txt
        assert id(ALIAS_IMPORT) != id(original_import)
        assert id(ALIAS_EXPORT) != id(original_export)
        new_alias_import, new_alias_export = rows.import_from_txt, rows.export_to_txt
        assert id(new_alias_import) == id(original_import)  # Function replaced with loaded one
        assert id(new_alias_export) == id(original_export)  # Function replaced with loaded one

    @mock.patch("rows.plugins.utils.create_table")
    def test_import_from_txt_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {"some_key": 123, "other": 456}
        result = rows.import_from_txt(self.filename, encoding=self.encoding, **kwargs)
        assert mocked_create_table.called
        assert mocked_create_table.call_count == 1
        assert result == 42

        call = mocked_create_table.call_args
        called_data = call[1]
        meta = called_data.pop("meta")
        assert call[1] == kwargs

        source = meta.pop("source")
        assert source.uri == Path(self.filename)

        expected_meta = {
            "imported_from": "txt",
            "frame_style": "ascii",
        }
        self.assertDictEqual(expected_meta, meta)

    @mock.patch("rows.plugins.utils.create_table")
    def test_import_from_txt_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        rows.import_from_txt(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args, expected_meta=self.expected_meta)

        # import using fobj
        with open(self.filename, mode="rb") as fobj:
            rows.import_from_txt(fobj)
            call_args = mocked_create_table.call_args_list[1]
            self.assert_create_table_data(call_args, expected_meta=self.expected_meta)

    @mock.patch("rows.plugins.utils.serialize")
    def test_export_to_txt_uses_serialize(self, mocked_serialize):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        kwargs = {"test": 123, "parameter": 3.14}
        mocked_serialize.return_value = iter([utils.table.fields.keys()])

        rows.export_to_txt(utils.table, temp.name, encoding=self.encoding, **kwargs)
        assert mocked_serialize.called
        assert mocked_serialize.call_count == 1

        call = mocked_serialize.call_args
        assert call[0] == (utils.table,)
        assert call[1] == kwargs

    def test_export_to_txt_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_txt(utils.table, temp.name, encoding="utf-8")

        table = rows.import_from_txt(temp.name, encoding="utf-8")
        self.assert_table_equal(table, utils.table)

        with open(temp.name, mode="rb") as fobj:
            content = fobj.read()
        assert content[-10:].count(b"\n") == 1

    def test_export_to_txt_fobj_binary(self):
        temp = tempfile.NamedTemporaryFile(delete=False, mode="wb")
        self.files_to_delete.append(temp.name)
        fobj = temp.file
        result = rows.export_to_txt(utils.table, fobj, encoding="utf-8")
        assert result is fobj
        assert not fobj.closed
        # TODO: test file contents instead of this side-effect
        table = rows.import_from_txt(temp.name, encoding="utf-8")
        self.assert_table_equal(table, utils.table)

    def test_export_to_txt_fobj_text(self):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.close()
        temp = io.TextIOWrapper(io.open(tmp.name, mode="wb"), encoding="utf-8")
        self.files_to_delete.append(tmp.name)
        result = rows.export_to_txt(utils.table, temp)
        assert result is temp
        assert not temp.closed
        # TODO: test file contents instead of this side-effect
        table = rows.import_from_txt(tmp.name, encoding="utf-8")
        self.assert_table_equal(table, utils.table)

    def test_export_to_txt_fobj_text_with_encoding(self):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.close()
        temp = io.TextIOWrapper(io.open(tmp.name, mode="wb"), encoding="utf-8")
        self.files_to_delete.append(tmp.name)
        with pytest.raises(ValueError, match="export_to_txt must not receive an encoding when file is in text mode"):
            rows.export_to_txt(utils.table, temp, encoding="utf-8")

    def test_export_to_txt_fobj_binary_without_encoding(self):
        temp = tempfile.NamedTemporaryFile(delete=False, mode="wb")
        self.files_to_delete.append(temp.name)
        fobj = temp.file
        with pytest.raises(ValueError, match="export_to_txt must receive an encoding when file is in binary mode"):
            rows.export_to_txt(utils.table, fobj, encoding=None)

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
        assert type(result) == TEXT_TYPE

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
                assert char in file_data
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

    def _test_import_from_txt_works_with_custom_frame(self, frame_style):
        temp = tempfile.NamedTemporaryFile(delete=False)
        original_data = rows.import_from_txt(self.filename)
        rows.export_to_txt(
            utils.table, temp.file, encoding="utf-8", frame_style=frame_style
        )
        new_data = rows.import_from_txt(temp.name)
        assert list(new_data) == list(original_data)

    def test_import_from_txt_works_with_ASCII_frame(self):
        self._test_import_from_txt_works_with_custom_frame("ASCII")

    def test_import_from_txt_works_with_unicode_single_frame(self):
        self._test_import_from_txt_works_with_custom_frame("single")

    def test_import_from_txt_works_with_unicode_double_frame(self):
        self._test_import_from_txt_works_with_custom_frame("double")

    def test_import_from_txt_works_with_no_frame(self):
        self._test_import_from_txt_works_with_custom_frame("None")

    def test__parse_col_positions(self):
        result1 = rows.plugins.txt._parse_col_positions("ascii", "|----|----|")
        assert result1 == [0, 5, 10]
        result2 = rows.plugins.txt._parse_col_positions("none", "  col1   col2  ")
        assert result2 == [0, 7, 14]
