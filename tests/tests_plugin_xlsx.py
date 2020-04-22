# coding: utf-8

# Copyright 2014-2020 Álvaro Justen <https://github.com/turicas/rows/>

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

import datetime
import tempfile
import unittest
from collections import OrderedDict
from decimal import Decimal
from io import BytesIO

import mock

import rows
import rows.plugins.xlsx
import tests.utils as utils
from rows.utils import Source


class PluginXlsxTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = "xlsx"
    file_extension = "xlsx"
    filename = "tests/data/all-field-types.xlsx"
    expected_meta = {
        "imported_from": "xlsx",
        "name": "Sheet1",
        "source": Source(uri=filename, plugin_name=plugin_name, encoding=None),
    }

    def get_temp_filename(self):
        temp = tempfile.NamedTemporaryFile(suffix=f".{self.file_extension}", delete=False)
        filename = temp.name
        temp.close()
        self.files_to_delete.append(filename)
        return filename

    def test_imports(self):
        self.assertIs(rows.import_from_xlsx, rows.plugins.xlsx.import_from_xlsx)
        self.assertIs(rows.export_to_xlsx, rows.plugins.xlsx.export_to_xlsx)

    @mock.patch("rows.plugins.xlsx.create_table")
    def test_import_from_xlsx_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {"encoding": "iso-8859-15", "some_key": 123, "other": 456}
        result = rows.import_from_xlsx(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

    @mock.patch("rows.plugins.xlsx.create_table")
    def test_import_from_xlsx_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        rows.import_from_xlsx(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args, expected_meta=self.expected_meta)

        # import using fobj
        with open(self.filename, "rb") as fobj:
            rows.import_from_xlsx(fobj)
        call_args = mocked_create_table.call_args_list[1]
        self.assert_create_table_data(call_args, expected_meta=self.expected_meta)

    def test_export_to_xlsx_filename(self):
        filename = self.get_temp_filename()
        rows.export_to_xlsx(utils.table, filename)

        table = rows.import_from_xlsx(filename)
        self.assert_table_equal(table, utils.table)

        export_in_memory = rows.export_to_xlsx(utils.table, None)
        result_fobj = BytesIO()
        result_fobj.write(export_in_memory)
        result_fobj.seek(0)
        result_table = rows.import_from_xlsx(result_fobj)
        self.assert_table_equal(result_table, utils.table)

    def test_export_to_xlsx_fobj(self):
        filename = self.get_temp_filename()
        fobj = open(filename, "wb")

        rows.export_to_xlsx(utils.table, fobj)
        fobj.close()

        table = rows.import_from_xlsx(filename)
        self.assert_table_equal(table, utils.table)

    @mock.patch("rows.plugins.xlsx.prepare_to_export")
    def test_export_to_xlsx_uses_prepare_to_export(self, mocked_prepare_to_export):
        filename = self.get_temp_filename()

        kwargs = {"test": 123, "parameter": 3.14}
        mocked_prepare_to_export.return_value = iter([utils.table.fields.keys()])

        rows.export_to_xlsx(utils.table, filename, **kwargs)
        self.assertTrue(mocked_prepare_to_export.called)
        self.assertEqual(mocked_prepare_to_export.call_count, 1)

        call = mocked_prepare_to_export.call_args
        self.assertEqual(call[0], (utils.table,))
        self.assertEqual(call[1], kwargs)

    def test_issue_168(self):
        filename = self.get_temp_filename()

        table = rows.Table(fields=OrderedDict([("jsoncolumn", rows.fields.JSONField)]))
        table.append({"jsoncolumn": '{"python": 42}'})
        rows.export_to_xlsx(table, filename)

        table2 = rows.import_from_xlsx(filename)
        self.assert_table_equal(table, table2)

    @mock.patch("rows.plugins.xlsx.create_table")
    def test_start_and_end_row(self, mocked_create_table):
        rows.import_from_xlsx(
            self.filename, start_row=6, end_row=8, start_column=4, end_column=7
        )
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        call_args = mocked_create_table.call_args_list[0]
        expected_data = [
            [4.56, 4.56, "12%", datetime.datetime(2050, 1, 2, 0, 0)],
            [7.89, 7.89, "13.64%", datetime.datetime(2015, 8, 18, 0, 0)],
            [9.87, 9.87, "13.14%", datetime.datetime(2015, 3, 4, 0, 0)],
        ]
        self.assertEqual(expected_data, call_args[0][0])

    def test_issue_290_can_read_sheet(self):
        rows.import_from_xlsx("tests/data/text_in_percent_cell.xlsx")
        # Before fixing the first part of #290, this would simply crash
        assert True

    def test_issue_290_one_hundred_read_as_1(self):
        result = rows.import_from_xlsx("tests/data/text_in_percent_cell.xlsx")
        # As this test is written, file numeric file contents on first column are
        # 100%, 23.20%, 1.00%, 10.00%, 100.00%
        assert result[0][0] == Decimal("1")
        assert result[1][0] == Decimal("0.2320")
        assert result[2][0] == Decimal("0.01")
        assert result[3][0] == Decimal("0.1")
        assert result[4][0] == Decimal("1")

    def test_issue_290_textual_value_in_percent_col_is_preserved(self):
        result = rows.import_from_xlsx("tests/data/text_in_percent_cell.xlsx")
        # As this test is written, file contents on first column are
        # 100%, 23.20%, 1.00%, 10.00%, 100.00%
        assert result[5][1] == "text"

    # TODO: add test when sheet.min_row/max_row/min_col/max_col is None
    # (happens when file is downloaded from Google Spreadsheets).

    def test_define_sheet_name(self):
        define_sheet_name = rows.plugins.xlsx.define_sheet_name

        self.assertEqual(define_sheet_name(["Sheet1"]), "Sheet2")
        self.assertEqual(define_sheet_name(["Test", "Test2"]), "Sheet1")
        self.assertEqual(define_sheet_name(["Sheet1", "Sheet2"]), "Sheet3")
        self.assertEqual(define_sheet_name(["Sheet1", "Sheet3"]), "Sheet2")

    def test_is_existing_spreadsheet(self):
        is_existing_spreadsheet = rows.plugins.xlsx.is_existing_spreadsheet

        def get_source(filename_or_fobj):
            return Source.from_file(filename_or_fobj, mode="a+b", plugin_name="xlsx")

        filename = "this-file-doesnt-exist.xxx"
        self.files_to_delete.append(filename)
        self.assertFalse(is_existing_spreadsheet(get_source(filename)))

        filename = __file__
        self.assertFalse(is_existing_spreadsheet(get_source(filename)))

        filename = self.filename
        self.assertTrue(is_existing_spreadsheet(get_source(filename)))

        data = BytesIO()
        with open(self.filename, mode="rb") as fobj:
            data.write(fobj.read())
        self.assertTrue(is_existing_spreadsheet(get_source(data)))

    def test_write_multiple_sheets(self):
        filename = self.get_temp_filename()

        table1 = rows.import_from_dicts([{"f1": 1, "f2": 2}, {"f1": 3, "f2": 4}])
        table2 = rows.import_from_dicts([{"f1": -1, "f2": -2}, {"f1": -3, "f2": -4}])
        table3 = rows.import_from_dicts([{"f1": 0, "f2": 1}, {"f1": 2, "f2": 3}])

        rows.export_to_xlsx(table1, filename, sheet_name="Test1")
        rows.export_to_xlsx(table2, filename)
        rows.export_to_xlsx(table3, filename)

        result = rows.plugins.xlsx.sheet_names(filename)
        self.assertEqual(result, ["Test1", "Sheet1", "Sheet2"])

        self.assertEqual(
            list(table1),
            list(rows.import_from_xlsx(filename, sheet_name="Test1"))
        )
        self.assertEqual(
            list(table2),
            list(rows.import_from_xlsx(filename, sheet_name="Sheet1"))
        )
        self.assertEqual(
            list(table3),
            list(rows.import_from_xlsx(filename, sheet_name="Sheet2"))
        )
