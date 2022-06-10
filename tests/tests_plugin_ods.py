# coding: utf-8

# Copyright 2014-2022 Álvaro Justen <https://github.com/turicas/rows/>

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

import unittest
from decimal import Decimal

import mock

import rows
import rows.plugins.ods
import tests.utils as utils
from rows.utils import Source


class PluginOdsTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = "ods"
    filename = "tests/data/all-field-types.ods"
    assert_meta_encoding = False
    expected_meta = {
        "imported_from": "ods",
        "name": "Sheet1",
        "source": Source(uri=filename, plugin_name=plugin_name, encoding=None),
    }

    def test_imports(self):
        self.assertIs(rows.import_from_ods, rows.plugins.ods.import_from_ods)

    @mock.patch("rows.plugins.ods.create_table")
    def test_import_from_ods_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {"encoding": "test", "some_key": 123, "other": 456}
        result = rows.import_from_ods(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

    @mock.patch("rows.plugins.ods.create_table")
    def test_import_from_ods_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        rows.import_from_ods(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args, expected_meta=self.expected_meta)

        # import using fobj
        with open(self.filename, "rb") as fobj:
            rows.import_from_ods(fobj)
            call_args = mocked_create_table.call_args_list[1]
            self.assert_create_table_data(call_args, expected_meta=self.expected_meta)

    def test_meta_name(self):
        result = rows.import_from_ods(self.filename)
        # TODO: may test other sheets
        assert result.meta["name"] == "Sheet1"

    def test_issue_290_one_hundred_read_as_1(self):
        result = rows.import_from_ods("tests/data/text_in_percent_cell.ods")
        # As this test is written, file numeric file contents on first column are
        # 100%, 23.20%, 1.00%, 10.00%, 100.00%
        assert result[0][0] == Decimal("1")
        assert result[2][0] == Decimal("0.01")
        assert result[3][0] == Decimal("0.1")
        assert result[4][0] == Decimal("1")

    def test_issue_320_empty_cells(self):
        result = rows.import_from_ods("tests/data/empty-cells.ods")
        header = "f1 f2 f3 f4 f5".split()
        data = [[getattr(row, field) for field in header] for row in result]
        assert data[0] == ["r1f1", "r1f2", None, "r1f4", "r1f5"]
        assert data[1] == ["r2f1", None, "r2f3", "r2f4", "r2f5"]
        assert data[2] == [None, "r3f2", "r3f3", "r3f4", "r3f5"]
        assert data[3] == ["r4f1", "r4f2", "r4f3", "r4f4", None]
        assert data[4] == [None, None, "r5f3", "r5f4", "r5f5"]

    def test_cell_range(self):
        result = rows.import_from_ods(
            "tests/data/all-field-types.ods",
            start_row=3,
            end_row=5,
            start_column=1,
            end_column=4,
        )
        header = "field_3 field_4_56 field_4_56_2 field_12".split()
        data = [[getattr(row, field) for field in header] for row in result]
        assert len(data) == 2
        assert data[0] == [4, 7.89, 7.89, Decimal("0.1364")]
        assert data[1] == [5, 9.87, 9.87, Decimal("0.1314")]
