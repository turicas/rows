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

import collections
import datetime
import unittest
from textwrap import dedent

import mock
import six

import rows
import rows.fields as fields
from rows.table import FlexibleTable, Table

binary_type_name = six.binary_type.__name__


class TableTestCase(unittest.TestCase):
    def setUp(self):
        self.table = Table(
            fields={"name": rows.fields.TextField, "birthdate": rows.fields.DateField}
        )
        self.first_row = {
            "name": "Álvaro Justen",
            "birthdate": datetime.date(1987, 4, 29),
        }
        self.table.append(self.first_row)
        self.table.append({"name": "Somebody", "birthdate": datetime.date(1990, 2, 1)})
        self.table.append({"name": "Douglas Adams", "birthdate": "1952-03-11"})

    def test_table_init_slug_creation_on_fields(self):
        table = rows.Table(
            fields=collections.OrderedDict(
                [('Query Occurrence"( % ),"First Seen', rows.fields.FloatField)]
            )
        )

        self.assertIn("query_occurrence_first_seen", table.fields)

    def test_Table_is_present_on_main_namespace(self):
        self.assertIn("Table", dir(rows))
        self.assertIs(Table, rows.Table)

    def test_table_iteration(self):
        # TODO: may test with all field types (using tests.utils.table)

        table_rows = [row for row in self.table]
        self.assertEqual(len(table_rows), 3)
        self.assertEqual(table_rows[0].name, "Álvaro Justen")
        self.assertEqual(table_rows[0].birthdate, datetime.date(1987, 4, 29))
        self.assertEqual(table_rows[1].name, "Somebody")
        self.assertEqual(table_rows[1].birthdate, datetime.date(1990, 2, 1))
        self.assertEqual(table_rows[2].name, "Douglas Adams")
        self.assertEqual(table_rows[2].birthdate, datetime.date(1952, 3, 11))

    def test_table_slicing(self):
        self.assertEqual(len(self.table[::2]), 2)
        self.assertEqual(self.table[::2][0].name, "Álvaro Justen")

    def test_table_slicing_error(self):
        with self.assertRaises(ValueError) as context_manager:
            self.table[[1]]
        self.assertEqual(type(context_manager.exception), ValueError)

    def test_table_insert_row(self):
        self.table.insert(
            1, {"name": "Grace Hopper", "birthdate": datetime.date(1909, 12, 9)}
        )
        self.assertEqual(self.table[1].name, "Grace Hopper")

    def test_table_append_error(self):
        # TODO: may mock these validations and test only on *Field tests
        with self.assertRaises(ValueError) as context_manager:
            self.table.append(
                {"name": "Álvaro Justen".encode("utf-8"), "birthdate": "1987-04-29"}
            )
        self.assertEqual(type(context_manager.exception), ValueError)
        self.assertEqual(context_manager.exception.args[0], "Binary is not supported")

        with self.assertRaises(ValueError) as context_manager:
            self.table.append({"name": "Álvaro Justen", "birthdate": "WRONG"})
        self.assertEqual(type(context_manager.exception), ValueError)
        self.assertIn("does not match format", context_manager.exception.args[0])

    def test_table_getitem_invalid_type(self):
        with self.assertRaises(ValueError) as exception_context:
            self.table[3.14]
        self.assertEqual(
            exception_context.exception.args[0], "Unsupported key type: float"
        )

        with self.assertRaises(ValueError) as exception_context:
            self.table[b"name"]
        self.assertEqual(
            exception_context.exception.args[0],
            "Unsupported key type: {}".format(binary_type_name),
        )

    def test_table_getitem_column_doesnt_exist(self):
        with self.assertRaises(KeyError) as exception_context:
            self.table["doesnt-exist"]

        self.assertEqual(exception_context.exception.args[0], "doesnt-exist")

    def test_table_getitem_column_happy_path(self):
        expected_values = ["Álvaro Justen", "Somebody", "Douglas Adams"]
        self.assertEqual(self.table["name"], expected_values)

        expected_values = [
            datetime.date(1987, 4, 29),
            datetime.date(1990, 2, 1),
            datetime.date(1952, 3, 11),
        ]
        self.assertEqual(self.table["birthdate"], expected_values)

    def test_table_setitem_row(self):
        self.first_row["name"] = "turicas"
        self.first_row["birthdate"] = datetime.date(2000, 1, 1)
        self.table[0] = self.first_row
        self.assertEqual(self.table[0].name, "turicas")
        self.assertEqual(self.table[0].birthdate, datetime.date(2000, 1, 1))

    def test_field_names_and_types(self):
        self.assertEqual(self.table.field_names, list(self.table.fields.keys()))
        self.assertEqual(self.table.field_types, list(self.table.fields.values()))

    def test_table_setitem_column_happy_path_new_column(self):
        number_of_fields = len(self.table.fields)
        self.assertEqual(len(self.table), 3)

        self.table["user_id"] = [4, 5, 6]

        self.assertEqual(len(self.table), 3)
        self.assertEqual(len(self.table.fields), number_of_fields + 1)

        self.assertIn("user_id", self.table.fields)
        self.assertIs(self.table.fields["user_id"], rows.fields.IntegerField)
        self.assertEqual(self.table[0].user_id, 4)
        self.assertEqual(self.table[1].user_id, 5)
        self.assertEqual(self.table[2].user_id, 6)

    def test_table_setitem_column_happy_path_replace_column(self):
        number_of_fields = len(self.table.fields)
        self.assertEqual(len(self.table), 3)

        self.table["name"] = [4, 5, 6]  # change values *and* type

        self.assertEqual(len(self.table), 3)
        self.assertEqual(len(self.table.fields), number_of_fields)

        self.assertIn("name", self.table.fields)
        self.assertIs(self.table.fields["name"], rows.fields.IntegerField)
        self.assertEqual(self.table[0].name, 4)
        self.assertEqual(self.table[1].name, 5)
        self.assertEqual(self.table[2].name, 6)

    def test_table_setitem_column_slug_field_name(self):
        self.assertNotIn("user_id", self.table.fields)
        self.table["User ID"] = [4, 5, 6]
        self.assertIn("user_id", self.table.fields)

    def test_table_setitem_column_invalid_length(self):
        number_of_fields = len(self.table.fields)
        self.assertEqual(len(self.table), 3)

        with self.assertRaises(ValueError) as exception_context:
            self.table["user_id"] = [4, 5]  # list len should be 3

        self.assertEqual(len(self.table), 3)
        self.assertEqual(len(self.table.fields), number_of_fields)
        self.assertEqual(
            exception_context.exception.args[0],
            "Values length (2) should be the same as Table " "length (3)",
        )

    def test_table_setitem_invalid_type(self):
        fields = self.table.fields.copy()
        self.assertEqual(len(self.table), 3)

        with self.assertRaises(ValueError) as exception_context:
            self.table[3.14] = []

        self.assertEqual(len(self.table), 3)  # should not add any row
        self.assertDictEqual(fields, self.table.fields)  # should not add field
        self.assertEqual(
            exception_context.exception.args[0], "Unsupported key type: float"
        )

        with self.assertRaises(ValueError) as exception_context:
            self.table[b"some_value"] = []

        self.assertEqual(len(self.table), 3)  # should not add any row
        self.assertDictEqual(fields, self.table.fields)  # should not add field
        self.assertEqual(
            exception_context.exception.args[0],
            "Unsupported key type: {}".format(binary_type_name),
        )

    def test_table_delitem_row(self):
        table_rows = [row for row in self.table]
        before = len(self.table)
        del self.table[0]
        after = len(self.table)
        self.assertEqual(after, before - 1)
        for row, expected_row in zip(self.table, table_rows[1:]):
            self.assertEqual(row, expected_row)

    def test_table_delitem_column_doesnt_exist(self):
        with self.assertRaises(KeyError) as exception_context:
            del self.table["doesnt-exist"]

        self.assertEqual(exception_context.exception.args[0], "doesnt-exist")

    def test_table_delitem_column_happy_path(self):
        fields = self.table.fields.copy()
        self.assertEqual(len(self.table), 3)

        del self.table["name"]

        self.assertEqual(len(self.table), 3)  # should not del any row
        self.assertEqual(len(self.table.fields), len(fields) - 1)

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
        self.assertEqual(len(self.table), 3)

        with self.assertRaises(ValueError) as exception_context:
            del self.table[3.14]

        self.assertEqual(len(self.table), 3)  # should not del any row
        self.assertDictEqual(fields, self.table.fields)  # should not del field
        self.assertEqual(
            exception_context.exception.args[0], "Unsupported key type: float"
        )

        with self.assertRaises(ValueError) as exception_context:
            self.table[b"name"] = []  # 'name' actually exists

        self.assertEqual(len(self.table), 3)  # should not del any row
        self.assertDictEqual(fields, self.table.fields)  # should not del field
        self.assertEqual(
            exception_context.exception.args[0],
            "Unsupported key type: {}".format(binary_type_name),
        )

    def test_table_add(self):
        self.assertIs(self.table + 0, self.table)
        self.assertIs(0 + self.table, self.table)

        new_table = self.table + self.table
        self.assertEqual(new_table.fields, self.table.fields)
        self.assertEqual(len(new_table), 2 * len(self.table))
        self.assertEqual(list(new_table), list(self.table) * 2)

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
        self.assertEqual(sorted(before), after)

        self.table.order_by("-birthdate")
        final = [row.birthdate for row in self.table]
        self.assertEqual(final, list(reversed(after)))

        self.table.order_by("name")
        expected_rows = [
            {"name": "Douglas Adams", "birthdate": datetime.date(1952, 3, 11)},
            {"name": "Somebody", "birthdate": datetime.date(1990, 2, 1)},
            {"name": "Álvaro Justen", "birthdate": datetime.date(1987, 4, 29)},
        ]
        for expected_row, row in zip(expected_rows, self.table):
            self.assertEqual(expected_row, dict(row._asdict()))

    def test_table_repr(self):
        expected = "<rows.Table 2 fields, 3 rows>"
        self.assertEqual(expected, repr(self.table))

    def test_table_add_should_not_iterate_over_rows(self):
        table1 = rows.Table(
            fields={"f1": rows.fields.IntegerField, "f2": rows.fields.FloatField}
        )
        table2 = rows.Table(
            fields={"f1": rows.fields.IntegerField, "f2": rows.fields.FloatField}
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
        self.assertTrue(table1._rows.__add__.called)
        self.assertFalse(table2._rows.__add__.called)
        self.assertFalse(table1._rows.__iter__.called)
        self.assertFalse(table2._rows.__iter__.called)


class TestFlexibleTable(unittest.TestCase):
    def setUp(self):
        self.table = FlexibleTable()

    def test_FlexibleTable_is_present_on_main_namespace(self):
        self.assertIn("FlexibleTable", dir(rows))
        self.assertIs(FlexibleTable, rows.FlexibleTable)

    def test_inheritance(self):
        self.assertTrue(issubclass(FlexibleTable, Table))

    def test_flexible_append_detect_field_type(self):
        self.assertEqual(len(self.table.fields), 0)

        self.table.append({"a": 123, "b": 3.14})
        self.assertEqual(self.table[0].a, 123)
        self.assertEqual(self.table[0].b, 3.14)
        self.assertEqual(self.table.fields["a"], fields.IntegerField)
        self.assertEqual(self.table.fields["b"], fields.FloatField)

        # Values are checked based on field types when appending
        with self.assertRaises(ValueError):
            self.table.append({"a": "spam", "b": 1.23})  # invalid value for 'a'
        with self.assertRaises(ValueError):
            self.table.append({"a": 42, "b": "ham"})  # invalid value or 'b'

        # Values are converted
        self.table.append({"a": "42", "b": "2.71"})
        self.assertEqual(self.table[1].a, 42)
        self.assertEqual(self.table[1].b, 2.71)

    def test_flexible_insert_row(self):
        self.table.append({"a": 123, "b": 3.14})
        self.table.insert(0, {"a": 2357, "b": 1123})
        self.assertEqual(self.table[0].a, 2357)

    def test_flexible_update_row(self):
        self.table.append({"a": 123, "b": 3.14})
        self.table[0] = {"a": 2357, "b": 1123}
        self.assertEqual(self.table[0].a, 2357)

    def test_table_slicing(self):
        self.table.append({"a": 123, "b": 3.14})
        self.table.append({"a": 2357, "b": 1123})
        self.table.append({"a": 8687, "b": 834798})
        self.assertEqual(len(self.table[::2]), 2)
        self.assertEqual(self.table[::2][0].a, 123)

    def test_table_slicing_error(self):
        self.table.append({"a": 123, "b": 3.14})
        self.table.append({"a": 2357, "b": 1123})
        self.table.append({"a": 8687, "b": 834798})
        with self.assertRaises(ValueError) as context_manager:
            self.table[[1]]
        self.assertEqual(type(context_manager.exception), ValueError)

    def test_table_iadd(self):
        table = rows.Table(
            fields={"f1": rows.fields.IntegerField, "f2": rows.fields.FloatField}
        )
        table.append({"f1": 1, "f2": 2})
        table.append({"f1": 3, "f2": 4})

        self.assertEqual(len(table), 2)
        table += table
        self.assertEqual(len(table), 4)
        data_rows = list(table)
        self.assertEqual(data_rows[0], data_rows[2])
        self.assertEqual(data_rows[1], data_rows[3])

    def test_table_name(self):
        table = rows.Table(fields=collections.OrderedDict([("a", fields.TextField)]))

        self.assertTrue("filename" not in table.meta)
        self.assertEqual(table.name, "table1")

        table.meta["filename"] = "This is THE name.csv"
        self.assertTrue("filename" in table.meta)
        self.assertEqual(table.name, "this_is_the_name")

    def test_head(self):
        table = rows.Table(
            fields={"f1": rows.fields.IntegerField, "f2": rows.fields.IntegerField}
        )
        for i in range(50):
            table.append({"f1": i, "f2": i ** 2})
        t2 = table.head()
        assert len(t2) == 10
        t2 = table.head(n=15)
        assert len(t2) == 15
        assert list(t2) == list(table[:15])

    def test_tail(self):
        table = rows.Table(
            fields={"f1": rows.fields.IntegerField, "f2": rows.fields.IntegerField}
        )
        for i in range(50):
            table.append({"f1": i, "f2": i ** 2})
        t2 = table.tail()
        assert len(t2) == 10
        t2 = table.tail(n=15)
        assert len(t2) == 15
        assert list(t2) == list(table[-15:])

    def test_repr_html(self):
        table = rows.Table(
            fields={"f1": rows.fields.IntegerField, "f2": rows.fields.IntegerField}
        )
        for i in range(5):
            table.append({"f1": i, "f2": i ** 2})

        result = table._repr_html_()
        expected = dedent("""
        <table>

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
        """).strip() + "\n"
        self.assertEqual(result, expected)
