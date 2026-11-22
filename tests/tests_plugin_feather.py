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

import datetime
import io
import os
import tempfile
import unittest
from collections import OrderedDict
from decimal import Decimal
from pathlib import Path

try:
    import mock
except ImportError:
    from unittest import mock

import pytest

import rows

try:
    import pyarrow
    from pyarrow import feather

    pyarrow_imported = True
except ImportError:
    pyarrow_imported = False


@pytest.mark.skipif(not pyarrow_imported, reason="pyarrow not installed")
class PluginFeatherTestCase(unittest.TestCase):

    plugin_name = "feather"

    def setUp(self):
        self.files_to_delete = []
        self.arrow_table = pyarrow.table(
            OrderedDict(
                [
                    ("Bool Column", pyarrow.array([True, False, None], type=pyarrow.bool_())),
                    ("integer", pyarrow.array([1, -2, None], type=pyarrow.int32())),
                    ("float", pyarrow.array([1.5, 2.25, None], type=pyarrow.float64())),
                    (
                        "decimal",
                        pyarrow.array([Decimal("1.23"), Decimal("-4.56"), None], type=pyarrow.decimal128(5, 2)),
                    ),
                    ("text", pyarrow.array(["álvaro", "rows", None], type=pyarrow.string())),
                    ("binary", pyarrow.array([b"\x00\x01", b"rows", None], type=pyarrow.binary())),
                    (
                        "date",
                        pyarrow.array(
                            [datetime.date(2019, 1, 2), datetime.date(2020, 3, 4), None], type=pyarrow.date32()
                        ),
                    ),
                    (
                        "datetime",
                        pyarrow.array(
                            [datetime.datetime(2019, 1, 2, 3, 4, 5), datetime.datetime(2020, 3, 4, 5, 6, 7), None],
                            type=pyarrow.timestamp("us"),
                        ),
                    ),
                ]
            )
        )
        self.filename = self.get_temp_filename()
        feather.write_feather(self.arrow_table, self.filename)

    def tearDown(self):
        for filename in self.files_to_delete:
            if os.path.exists(filename):
                os.unlink(filename)

    def get_temp_filename(self):
        temp = tempfile.NamedTemporaryFile(suffix=".feather", delete=False)
        filename = temp.name
        temp.close()
        self.files_to_delete.append(filename)
        return filename

    def test_imports(self):
        # Force the plugin to load (lazy aliases are replaced by the original functions)
        original_import = rows.plugins.feather.import_from_feather
        original_export = rows.plugins.feather.export_to_feather
        assert rows.import_from_feather is original_import
        assert rows.export_to_feather is original_export

    @mock.patch("rows.plugins.plugin_feather.create_table")
    def test_import_from_feather_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {"some_key": 123, "other": 456}
        result = rows.import_from_feather(self.filename, **kwargs)
        assert mocked_create_table.called
        assert mocked_create_table.call_count == 1
        assert result == 42

        call = mocked_create_table.call_args
        for key, value in kwargs.items():
            assert call[1][key] == value
        expected_force_types = OrderedDict(
            [
                ("bool_column", rows.fields.BoolField),
                ("integer", rows.fields.IntegerField),
                ("float", rows.fields.FloatField),
                ("decimal", rows.fields.DecimalField),
                ("text", rows.fields.TextField),
                ("binary", rows.fields.BinaryField),
                ("date", rows.fields.DateField),
                ("datetime", rows.fields.DatetimeField),
            ]
        )
        self.assertDictEqual(dict(call[1]["force_types"]), dict(expected_force_types))
        assert list(call[1]["force_types"].keys()) == list(expected_force_types.keys())

        expected_meta = {"imported_from": "feather"}
        meta = call[1]["meta"].copy()
        source = meta.pop("source")
        assert meta == expected_meta
        assert source.uri == Path(self.filename)

    def test_import_from_feather_retrieve_desired_data(self):
        table = rows.import_from_feather(self.filename)
        assert table.field_names == [
            "bool_column",
            "integer",
            "float",
            "decimal",
            "text",
            "binary",
            "date",
            "datetime",
        ]
        assert len(table) == 3
        first, second, third = table
        assert first.bool_column is True
        assert first.integer == 1
        assert first.float == 1.5
        assert first.decimal == Decimal("1.23")
        assert first.text == "álvaro"
        assert first.binary == b"\x00\x01"
        assert first.date == datetime.date(2019, 1, 2)
        assert first.datetime == datetime.datetime(2019, 1, 2, 3, 4, 5)
        assert second.bool_column is False
        assert second.integer == -2
        assert second.decimal == Decimal("-4.56")
        assert third.bool_column is None
        assert third.integer is None
        assert third.float is None
        assert third.decimal is None
        assert third.text is None
        assert third.date is None
        assert third.datetime is None

    def test_import_from_feather_fobj_binary(self):
        with open(self.filename, mode="rb") as fobj:
            table = rows.import_from_feather(fobj)
        assert len(table) == 3
        assert table[0].text == "álvaro"

    def test_import_from_feather_fobj_text(self):
        with pytest.raises(ValueError, match="import_from_feather must not receive a file-like object in text mode"):
            fobj = io.TextIOWrapper(io.open(self.filename, mode="rb"), encoding="utf-8")
            rows.import_from_feather(fobj)

    def test_export_to_feather_fobj_text(self):
        table = rows.import_from_feather(self.filename)
        filename = self.get_temp_filename()
        with io.open(filename, mode="w", encoding="utf-8") as fobj:
            with pytest.raises(ValueError, match="export_to_feather must receive a file-object open in binary mode"):
                rows.export_to_feather(table, fobj)

    def assert_same_table(self, first, second):
        assert first.field_names == second.field_names
        for field_name in first.field_names:
            assert first.fields[field_name] is second.fields[field_name]
        assert [list(row) for row in first] == [list(row) for row in second]

    def test_export_import_filename(self):
        table = rows.import_from_feather(self.filename)
        filename = self.get_temp_filename()
        rows.export_to_feather(table, filename)
        self.assert_same_table(table, rows.import_from_feather(filename))

    def test_export_import_fobj(self):
        table = rows.import_from_feather(self.filename)
        filename = self.get_temp_filename()
        with open(filename, mode="wb") as fobj:
            result = rows.export_to_feather(table, fobj)
            assert result is fobj
        self.assert_same_table(table, rows.import_from_feather(filename))

    def test_export_returns_bytes(self):
        table = rows.import_from_feather(self.filename)
        result = rows.export_to_feather(table)
        assert isinstance(result, bytes)
        self.assert_same_table(table, rows.import_from_feather(io.BytesIO(result)))

    def test_export_to_feather_export_fields(self):
        table = rows.import_from_feather(self.filename)
        result = rows.export_to_feather(table, export_fields=["text", "integer"])
        new_table = rows.import_from_feather(io.BytesIO(result))
        assert new_table.field_names == ["text", "integer"]
        assert [(row.text, row.integer) for row in new_table] == [("álvaro", 1), ("rows", -2), (None, None)]

    def test_export_to_feather_non_native_types_as_text(self):
        table = rows.Table(fields=OrderedDict([("id", rows.fields.UUIDField), ("name", rows.fields.TextField)]))
        table.append({"id": "c1b2e94a-0d5e-4c6f-9a0b-6d1b0c4a5e1f", "name": "rows"})
        result = rows.export_to_feather(table)
        arrow_table = feather.read_table(io.BytesIO(result))
        assert arrow_table.schema.field("id").type == pyarrow.string()
        assert arrow_table.column("id").to_pylist() == ["c1b2e94a-0d5e-4c6f-9a0b-6d1b0c4a5e1f"]
