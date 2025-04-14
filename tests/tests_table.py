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
import random
import unittest
from collections import OrderedDict
from pathlib import Path
from textwrap import dedent

import mock
import pytest

import rows
import rows.fields as fields
from rows.compat import BINARY_TYPE
from rows.table import FlexibleTable, Table
from rows.utils import Source

binary_type_name = BINARY_TYPE.__name__


class TableTestCase(unittest.TestCase):
    def setUp(self):
        self.table = Table(
            fields=OrderedDict([("name", fields.TextField), ("birthdate", fields.DateField)])
        )
        self.first_row = {
            "name": "Álvaro Justen",
            "birthdate": datetime.date(1987, 4, 29),
        }
        self.table.append(self.first_row)
        self.table.append({"name": "Somebody", "birthdate": datetime.date(1990, 2, 1)})
        self.table.append({"name": "Douglas Adams", "birthdate": "1952-03-11"})

    def test_table_init_slug_creation_on_fields(self):
        table = Table(
            fields=OrderedDict(
                [('Query Occurrence"( % ),"First Seen', fields.FloatField)]
            )
        )

        assert "query_occurrence_first_seen" in table.fields

    def test_Table_is_present_on_main_namespace(self):
        assert "Table" in dir(rows)
        assert Table is rows.Table

    def test_table_iteration(self):
        # TODO: may test with all field types (using tests.utils.table)

        table_rows = [row for row in self.table]
        assert len(table_rows) == 3
        assert table_rows[0].name == "Álvaro Justen"
        assert table_rows[0].birthdate == datetime.date(1987, 4, 29)
        assert table_rows[1].name == "Somebody"
        assert table_rows[1].birthdate == datetime.date(1990, 2, 1)
        assert table_rows[2].name == "Douglas Adams"
        assert table_rows[2].birthdate == datetime.date(1952, 3, 11)

    def test_table_slicing(self):
        assert len(self.table[::2]) == 2
        assert self.table[::2][0].name == "Álvaro Justen"

    def test_table_slicing_error(self):
        with self.assertRaises(ValueError) as context_manager:
            self.table[[1]]
        assert type(context_manager.exception) == ValueError

    def test_table_insert_row(self):
        self.table.insert(
            1, {"name": "Grace Hopper", "birthdate": datetime.date(1909, 12, 9)}
        )
        assert self.table[1].name == "Grace Hopper"

    def test_table_append_error(self):
        # TODO: may mock these validations and test only on *Field tests
        with self.assertRaises(ValueError) as context_manager:
            self.table.append(
                {"name": "Álvaro Justen".encode("utf-8"), "birthdate": "1987-04-29"}
            )
        assert type(context_manager.exception) == ValueError
        assert context_manager.exception.args[0] == "Binary is not supported"

        with self.assertRaises(ValueError) as context_manager:
            self.table.append({"name": "Álvaro Justen", "birthdate": "WRONG"})
        assert type(context_manager.exception) == ValueError
        assert "does not match format" in context_manager.exception.args[0]

    def test_table_getitem_invalid_type(self):
        with self.assertRaises(ValueError) as exception_context:
            self.table[3.14]
        assert exception_context.exception.args[0] == "Unsupported key type: float"

        with self.assertRaises(ValueError) as exception_context:
            self.table[b"name"]
        assert exception_context.exception.args[0] == "Unsupported key type: {}".format(binary_type_name)

    def test_table_getitem_column_doesnt_exist(self):
        with self.assertRaises(KeyError) as exception_context:
            self.table["doesnt-exist"]

        assert exception_context.exception.args[0] == "doesnt-exist"

    def test_table_getitem_slice_happy_path(self):
        assert list(self.table[:]) == list(self.table)
        assert self.table[:].meta == self.table.meta

        assert list(self.table[1:]) == list(self.table)[1:]
        assert list(self.table[:-1]) == list(self.table)[:-1]

    def test_table_getitem_column_happy_path(self):
        expected_values = ["Álvaro Justen", "Somebody", "Douglas Adams"]
        assert self.table["name"] == expected_values

        expected_values = [
            datetime.date(1987, 4, 29),
            datetime.date(1990, 2, 1),
            datetime.date(1952, 3, 11),
        ]
        assert self.table["birthdate"] == expected_values

    def test_table_setitem_row(self):
        self.first_row["name"] = "turicas"
        self.first_row["birthdate"] = datetime.date(2000, 1, 1)
        self.table[0] = self.first_row
        assert self.table[0].name == "turicas"
        assert self.table[0].birthdate == datetime.date(2000, 1, 1)

    def test_field_names_and_types(self):
        assert self.table.field_names == list(self.table.fields.keys())
        assert self.table.field_types == list(self.table.fields.values())

    def test_table_setitem_column_happy_path_new_column(self):
        number_of_fields = len(self.table.fields)
        assert len(self.table) == 3

        self.table["user_id"] = [4, 5, 6]

        assert len(self.table) == 3
        assert len(self.table.fields) == number_of_fields + 1

        assert "user_id" in self.table.fields
        assert self.table.fields["user_id"] is fields.IntegerField
        assert self.table[0].user_id == 4
        assert self.table[1].user_id == 5
        assert self.table[2].user_id == 6

    def test_table_setitem_column_happy_path_replace_column(self):
        number_of_fields = len(self.table.fields)
        assert len(self.table) == 3

        self.table["name"] = [4, 5, 6]  # change values *and* type

        assert len(self.table) == 3
        assert len(self.table.fields) == number_of_fields

        assert "name" in self.table.fields
        assert self.table.fields["name"] is fields.IntegerField
        assert self.table[0].name == 4
        assert self.table[1].name == 5
        assert self.table[2].name == 6

    def test_table_setitem_column_slug_field_name(self):
        self.assertNotIn("user_id", self.table.fields)
        self.table["User ID"] = [4, 5, 6]
        assert "user_id" in self.table.fields

    def test_table_setitem_column_invalid_length(self):
        number_of_fields = len(self.table.fields)
        assert len(self.table) == 3

        with self.assertRaises(ValueError) as exception_context:
            self.table["user_id"] = [4, 5]  # list len should be 3

        assert len(self.table) == 3
        assert len(self.table.fields) == number_of_fields
        assert exception_context.exception.args[0] == "Values length (2) should be the same as Table length (3)"

    def test_table_setitem_invalid_type(self):
        fields = self.table.fields.copy()
        assert len(self.table) == 3

        with self.assertRaises(ValueError) as exception_context:
            self.table[3.14] = []

        assert len(self.table) == 3  # should not add any row
        self.assertDictEqual(fields, self.table.fields)  # should not add field
        assert exception_context.exception.args[0] == "Unsupported key type: float"

        with self.assertRaises(ValueError) as exception_context:
            self.table[b"some_value"] = []

        assert len(self.table) == 3  # should not add any row
        self.assertDictEqual(fields, self.table.fields)  # should not add field
        assert exception_context.exception.args[0] == "Unsupported key type: {}".format(binary_type_name)

    def test_table_delitem_row(self):
        table_rows = [row for row in self.table]
        before = len(self.table)
        del self.table[0]
        after = len(self.table)
        assert after == before - 1
        for row, expected_row in zip(self.table, table_rows[1:]):
            assert row == expected_row

    def test_table_delitem_column_doesnt_exist(self):
        with self.assertRaises(KeyError) as exception_context:
            del self.table["doesnt-exist"]

        assert exception_context.exception.args[0] == "doesnt-exist"

    def test_table_delitem_column_happy_path(self):
        fields = self.table.fields.copy()
        assert len(self.table) == 3

        del self.table["name"]

        assert len(self.table) == 3  # should not del any row
        assert len(self.table.fields) == len(fields) - 1

        self.assertDictEqual(
            dict(self.table[0]._asdict()), {"birthdate": datetime.date(1987, 4, 29)}
        )
        self.assertDictEqual(
            dict(self.table[1]._asdict()), {"birthdate": datetime.date(1990, 2, 1)}
        )
        self.assertDictEqual(
            dict(self.table[2]._asdict()), {"birthdate": datetime.date(1952, 3, 11)}
        )

    def test_table_delitem_column_invalid_type(self):
        fields = self.table.fields.copy()
        assert len(self.table) == 3

        with self.assertRaises(ValueError) as exception_context:
            del self.table[3.14]

        assert len(self.table) == 3  # should not del any row
        self.assertDictEqual(fields, self.table.fields)  # should not del field
        assert exception_context.exception.args[0] == "Unsupported key type: float"

        with self.assertRaises(ValueError) as exception_context:
            self.table[b"name"] = []  # 'name' actually exists

        assert len(self.table) == 3  # should not del any row
        self.assertDictEqual(fields, self.table.fields)  # should not del field
        assert exception_context.exception.args[0] == "Unsupported key type: {}".format(binary_type_name)

    def test_table_add(self):
        assert self.table + 0 is self.table
        assert 0 + self.table is self.table

        new_table = self.table + self.table
        assert new_table.fields == self.table.fields
        assert len(new_table) == 2 * len(self.table)
        assert list(new_table) == list(self.table) * 2

    def test_table_add_error(self):
        with self.assertRaises(ValueError):
            self.table + 1
        with self.assertRaises(ValueError):
            1 + self.table

    def test_table_order_by(self):
        with self.assertRaises(ValueError):
            self.table.order_by("doesnt_exist")

        before = [row.birthdate for row in self.table]
        self.table.order_by("birthdate")
        after = [row.birthdate for row in self.table]
        self.assertNotEqual(before, after)
        assert sorted(before) == after

        self.table.order_by("-birthdate")
        final = [row.birthdate for row in self.table]
        assert final == list(reversed(after))

        self.table.order_by("name")
        expected_rows = [
            {"name": "Douglas Adams", "birthdate": datetime.date(1952, 3, 11)},
            {"name": "Somebody", "birthdate": datetime.date(1990, 2, 1)},
            {"name": "Álvaro Justen", "birthdate": datetime.date(1987, 4, 29)},
        ]
        for expected_row, row in zip(expected_rows, self.table):
            assert expected_row == dict(row._asdict())

    def test_table_repr(self):
        expected = "<EagerTable: 2 fields, 3 rows>"
        assert expected == repr(self.table)

    def test_table_add_should_not_iterate_over_rows(self):
        table1 = Table(
            fields=OrderedDict([("f1", fields.IntegerField), ("f2", fields.FloatField)])
        )
        table2 = Table(
            fields=OrderedDict([("f1", fields.IntegerField), ("f2", fields.FloatField)])
        )
        table1._rows = mock.Mock()
        table1._rows.__add__ = mock.Mock()
        table1._rows.__iter__ = mock.Mock()
        table2._rows = mock.Mock()
        table2._rows.__add__ = mock.Mock()
        table2._rows.__iter__ = mock.Mock()

        self.assertFalse(table1._rows.__add__.called)
        self.assertFalse(table2._rows.__add__.called)
        self.assertFalse(table1._rows.__iter__.called)
        self.assertFalse(table2._rows.__iter__.called)
        table1 + table2
        assert table1._rows.__add__.called
        self.assertFalse(table2._rows.__add__.called)
        self.assertFalse(table1._rows.__iter__.called)
        self.assertFalse(table2._rows.__iter__.called)

    def test_repr_html(self):
        table = Table(
            fields=OrderedDict([("f1", fields.IntegerField), ("f2", fields.IntegerField)]),
            meta={"name": "my table"},
        )
        for i in range(5):
            table.append({"f1": i, "f2": i ** 2})

        result = table._repr_html_()
        expected = (
            dedent(
                """
        <table>

          <caption>my_table</caption>

          <thead>
            <tr>
              <th> f1 </th>
              <th> f2 </th>
            </tr>
          </thead>

          <tbody>

            <tr class="odd">
              <td> 0 </td>
              <td> 0 </td>
            </tr>

            <tr class="even">
              <td> 1 </td>
              <td> 1 </td>
            </tr>

            <tr class="odd">
              <td> 2 </td>
              <td> 4 </td>
            </tr>

            <tr class="even">
              <td> 3 </td>
              <td> 9 </td>
            </tr>

            <tr class="odd">
              <td> 4 </td>
              <td> 16 </td>
            </tr>

          </tbody>

        </table>
        """
            ).strip()
            + "\n"
        )
        assert result == expected

        # For long tables show only header + spacer + tail
        table = Table(
            fields=OrderedDict([("f1", fields.IntegerField), ("f2", fields.IntegerField)]),
            meta={"name": "my table"},
        )
        for i in range(50):
            table.append({"f1": i, "f2": i ** 2})

        result = table._repr_html_()
        expected = (
            dedent(
                """
        <table>

          <caption>my_table (previewing 20 rows out of 50)</caption>

          <thead>
            <tr>
              <th> f1 </th>
              <th> f2 </th>
            </tr>
          </thead>

          <tbody>

            <tr class="odd">
              <td> 0 </td>
              <td> 0 </td>
            </tr>

            <tr class="even">
              <td> 1 </td>
              <td> 1 </td>
            </tr>

            <tr class="odd">
              <td> 2 </td>
              <td> 4 </td>
            </tr>

            <tr class="even">
              <td> 3 </td>
              <td> 9 </td>
            </tr>

            <tr class="odd">
              <td> 4 </td>
              <td> 16 </td>
            </tr>

            <tr class="even">
              <td> 5 </td>
              <td> 25 </td>
            </tr>

            <tr class="odd">
              <td> 6 </td>
              <td> 36 </td>
            </tr>

            <tr class="even">
              <td> 7 </td>
              <td> 49 </td>
            </tr>

            <tr class="odd">
              <td> 8 </td>
              <td> 64 </td>
            </tr>

            <tr class="even">
              <td> 9 </td>
              <td> 81 </td>
            </tr>

            <tr class="odd">
              <td> ... </td>
              <td> ... </td>
            </tr>

            <tr class="even">
              <td> 40 </td>
              <td> 1600 </td>
            </tr>

            <tr class="odd">
              <td> 41 </td>
              <td> 1681 </td>
            </tr>

            <tr class="even">
              <td> 42 </td>
              <td> 1764 </td>
            </tr>

            <tr class="odd">
              <td> 43 </td>
              <td> 1849 </td>
            </tr>

            <tr class="even">
              <td> 44 </td>
              <td> 1936 </td>
            </tr>

            <tr class="odd">
              <td> 45 </td>
              <td> 2025 </td>
            </tr>

            <tr class="even">
              <td> 46 </td>
              <td> 2116 </td>
            </tr>

            <tr class="odd">
              <td> 47 </td>
              <td> 2209 </td>
            </tr>

            <tr class="even">
              <td> 48 </td>
              <td> 2304 </td>
            </tr>

            <tr class="odd">
              <td> 49 </td>
              <td> 2401 </td>
            </tr>

          </tbody>

        </table>
        """
            ).strip()
            + "\n"
        )
        assert result == expected


class TestFlexibleTable(unittest.TestCase):
    def setUp(self):
        self.table = FlexibleTable()

    def test_FlexibleTable_is_present_on_main_namespace(self):
        assert "FlexibleTable" in dir(rows)
        assert FlexibleTable is rows.FlexibleTable

    def test_inheritance(self):
        assert issubclass(FlexibleTable, Table)

    def test_flexible_append_detect_field_type(self):
        assert len(self.table.fields) == 0

        self.table.append({"a": 123, "b": 3.14})
        assert self.table[0].a == 123
        assert self.table[0].b == 3.14
        assert self.table.fields["a"] == fields.IntegerField
        assert self.table.fields["b"] == fields.FloatField

        # Values are checked based on field types when appending
        with self.assertRaises(ValueError):
            self.table.append({"a": "spam", "b": 1.23})  # invalid value for 'a'
        with self.assertRaises(ValueError):
            self.table.append({"a": 42, "b": "ham"})  # invalid value or 'b'

        # Values are converted
        self.table.append({"a": "42", "b": "2.71"})
        assert self.table[1].a == 42
        assert self.table[1].b == 2.71

    def test_flexible_insert_row(self):
        self.table.append({"a": 123, "b": 3.14})
        self.table.insert(0, {"a": 2357, "b": 1123})
        assert self.table[0].a == 2357

    def test_flexible_update_row(self):
        self.table.append({"a": 123, "b": 3.14})
        self.table[0] = {"a": 2357, "b": 1123}
        assert self.table[0].a == 2357

    def test_table_slicing(self):
        self.table.append({"a": 123, "b": 3.14})
        self.table.append({"a": 2357, "b": 1123})
        self.table.append({"a": 8687, "b": 834798})
        assert len(self.table[::2]) == 2
        assert self.table[::2][0].a == 123

    def test_table_slicing_error(self):
        self.table.append({"a": 123, "b": 3.14})
        self.table.append({"a": 2357, "b": 1123})
        self.table.append({"a": 8687, "b": 834798})
        with self.assertRaises(ValueError) as context_manager:
            self.table[[1]]
        assert type(context_manager.exception) == ValueError

    def test_table_iadd(self):
        table = FlexibleTable(
            fields=OrderedDict([("f1", fields.IntegerField), ("f2", fields.FloatField)])
        )
        table.append({"f1": 1, "f2": 2})
        table.append({"f1": 3, "f2": 4})

        assert len(table) == 2
        table += table
        assert len(table) == 4
        data_rows = list(table)
        assert data_rows[0] == data_rows[2]
        assert data_rows[1] == data_rows[3]

    def test_table_name(self):
        table = FlexibleTable(fields=OrderedDict([("a", fields.TextField)]))

        assert "name" not in table.meta
        assert table.name == "table1"

        table.meta["source"] = Source(
            uri=Path("This is THE name.csv"), plugin_name="csv", encoding="utf-8"
        )
        assert table.name == "this_is_the_name"

    def test_head(self):
        table = FlexibleTable(
            fields=OrderedDict([("f1", fields.IntegerField), ("f2", fields.IntegerField)])
        )
        for i in range(50):
            table.append({"f1": i, "f2": i ** 2})
        t2 = table.head()
        assert len(t2) == 10
        t2 = table.head(n=15)
        assert len(t2) == 15
        assert list(t2) == list(table[:15])

    def test_tail(self):
        table = FlexibleTable(
            fields=OrderedDict([("f1", fields.IntegerField), ("f2", fields.IntegerField)])
        )
        for i in range(50):
            table.append({"f1": i, "f2": i ** 2})
        t2 = table.tail()
        assert len(t2) == 10
        t2 = table.tail(n=15)
        assert len(t2) == 15
        assert list(t2) == list(table[-15:])


def test_fields_with_python_keywords():
    some_keywords = ("def", "try", "if", "for", "while", "def ")
    # Should not raise an exception
    table = Table(fields=OrderedDict([(key, fields.TextField) for key in some_keywords]))
    assert table.field_names == ["def_1", "try_1", "if_1", "for_1", "while_1", "def_2"]


def test_replacing_column_must_use_slug():
    table = Table(fields=OrderedDict([(key, fields.IntegerField) for key in ("f1", "f2", "f3")]))
    for i in range(10):
        table.append({"f1": i, "f2": i * 2, "f3": i ** 2})
    new_values = list(range(10))
    table["F2!!!"] = new_values
    assert table.field_names == ["f1", "f2", "f3"]
    assert table["f2"] == new_values


def row_source(n):
    for i in range(n):
        yield [i, random.choice(["Bob", "Álvaro", "Alice"]), i ** 2]


@pytest.mark.parametrize("mode,filled", [
    ("eager", True),
    ("incremental", False),
    ("incremental", True),
    ("stream", None),
])
def test_repr_html_modes(mode, filled):
    table_rows = row_source(25)
    table_fields = OrderedDict([("f1", fields.IntegerField), ("f2", fields.TextField), ("f3", fields.IntegerField)])
    table = Table(fields=table_fields, mode=mode, data=table_rows)
    if mode == "incremental" and filled:
        list(table)  # consume all rows

    html = table._repr_html_()
    assert html.startswith("<table") or "<table" in html
    assert "f1" in html  # field name
    assert "..." in html
    if mode == "eager" or (mode == "incremental" and filled):
        assert "out of 25" in html
    else:
        assert "out of ?" in html


def test_repr_html_small_eager():
    table_rows = row_source(5)
    table_fields = OrderedDict([("f1", fields.IntegerField), ("f2", fields.TextField), ("f3", fields.IntegerField)])
    table = Table(fields=table_fields, mode="eager", data=table_rows)
    html = table._repr_html_()
    assert html.count("<tr") == 6  # 1 header + 5 rows
    assert "out of" not in html  # shouldn't show preview count


def test_repr_html_incremental_partial():
    table_rows = row_source(30)
    table_fields = OrderedDict([("f1", fields.IntegerField), ("f2", fields.TextField), ("f3", fields.IntegerField)])
    table = Table(fields=table_fields, mode="incremental", data=table_rows)
    _ = table[:5]  # consume only head
    html = table._repr_html_()
    assert "..." in html
    assert "out of ?" in html
    _ = table[:]  # consume everything
    html2 = table._repr_html_()
    assert "out of ?" not in html2


def test_repr_html_stream():
    table_rows = row_source(30)
    table_fields = OrderedDict([("f1", fields.IntegerField), ("f2", fields.TextField), ("f3", fields.IntegerField)])
    table = Table(fields=table_fields, mode="incremental", data=table_rows)
    html = table._repr_html_()
    assert "..." in html
    assert "out of ?" in html
    # accessing again should still show truncated info
    html2 = table._repr_html_()
    assert "out of ?" in html2
    _ = table[:]  # consume everything
    html3 = table._repr_html_()
    assert "out of ?" not in html3



import pytest
from collections import OrderedDict
from rows import Table, EagerTable, IncrementalTable, StreamTable, FlexibleTable, fields

@pytest.fixture
def fields_():
    return OrderedDict([
        ("name", fields.TextField),
        ("age", fields.IntegerField),
    ])

@pytest.fixture
def tuples_data():
    return [
        ("Alice", 30),
        ("Bob", 25),
        ("Álvaro", 37),
    ]

@pytest.fixture
def dicts_data():
    return [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Álvaro", "age": 37},
    ]

def test_eager_iteration(fields_, tuples_data):
    table = Table(fields=fields_, data=tuples_data, mode="eager")
    assert isinstance(table, EagerTable)
    assert [row.name for row in table] == ["Alice", "Bob", "Álvaro"]

def test_eager_getitem_setitem(fields_, tuples_data):
    table = Table(fields=fields_, data=tuples_data, mode="eager")
    table[1] = {"name": "João", "age": 99}
    assert table[1].name == "João"

def test_eager_slice(fields_, tuples_data):
    table = Table(fields=fields_, data=tuples_data, mode="eager")
    assert len(table) == 3
    table2 = table[1:]
    assert isinstance(table2, EagerTable)
    assert len(table2) == 2

def test_incremental_iteration(fields_, tuples_data):
    table = Table(fields=fields_, data=iter(tuples_data), mode="incremental")
    data = list(table)
    assert data[2].name == "Álvaro"

def test_incremental_getitem(fields_, tuples_data):
    table = Table(fields=fields_, data=iter(tuples_data), mode="incremental")
    assert table[1].name == "Bob"
    assert not table._filled

def test_incremental_append_extend(fields_):
    table = Table(fields=fields_, data=[], mode="incremental")
    table.append({"name": "X", "age": 50})
    table.extend([{"name": "Y", "age": 60}])
    assert table[0].name == "X"
    assert table[1].name == "Y"

def test_stream_iteration(fields_, tuples_data):
    table = Table(fields=fields_, data=iter(tuples_data), mode="stream")
    names = [row.name for row in table]
    assert names == ["Alice", "Bob", "Álvaro"]

def test_stream_non_indexable(fields_, tuples_data):
    table = Table(fields=fields_, data=iter(tuples_data), mode="stream")
    with pytest.raises(TypeError):
        _ = table[0]
    with pytest.raises(TypeError):
        table.append({"name": "Z", "age": 9})
    with pytest.raises(TypeError):
        len(table)

def test_flexible_dynamic_fields():
    data = [{"a": 1}, {"b": 2}]
    table = Table(fields={}, data=data, mode="flexible")
    assert table[0].a == 1
    assert table[1].b == 2
    table.append({"c": 3})
    assert table[2].c == 3
    exported = list(table.export())
    assert len(exported[0]) == len(exported[1]) == len(exported[2]) == 3
    assert exported[0][0] == 1
    assert exported[2][2] == 3

def test_repr_and_mode(fields_, tuples_data, dicts_data):
    for mode in ("eager", "incremental", "stream", "flexible"):
        table = Table(fields=fields_, data=tuples_data if mode != "flexible" else dicts_data, mode=mode)
        assert repr(table).startswith("<{}Table".format(mode.capitalize()))
        assert table.mode == mode
