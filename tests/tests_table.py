# coding: utf-8

# Copyright 2014-2015 Álvaro Justen <https://github.com/turicas/rows/>
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

import datetime
import unittest

import rows
import rows.fields as fields

from rows.table import Table


class TableTestCase(unittest.TestCase):

    def setUp(self):
        self.table = Table(fields={'name': rows.fields.UnicodeField,
                                   'birthdate': rows.fields.DateField, })
        self.first_row = {'name': u'Álvaro Justen',
                          'birthdate': datetime.date(1987, 4, 29)}
        self.table.append(self.first_row)
        self.table.append({'name': u'Somebody',
                           'birthdate': datetime.date(1990, 2, 1)})
        self.table.append({'name': u'Douglas Adams',
                           'birthdate': '1952-03-11'})

    def test_Table_is_present_on_main_namespace(self):
        self.assertIn('Table', dir(rows))
        self.assertIs(Table, rows.Table)

    def test_table_iteration(self):
        # TODO: may test with all field types (using tests.utils.table)

        table_rows = [row for row in self.table]
        self.assertEqual(len(table_rows), 3)
        self.assertEqual(table_rows[0].name, u'Álvaro Justen')
        self.assertEqual(table_rows[0].birthdate, datetime.date(1987, 4, 29))
        self.assertEqual(table_rows[1].name, u'Somebody')
        self.assertEqual(table_rows[1].birthdate, datetime.date(1990, 2, 1))
        self.assertEqual(table_rows[2].name, u'Douglas Adams')
        self.assertEqual(table_rows[2].birthdate, datetime.date(1952, 3, 11))

    def test_table_append_error(self):
        # TODO: may mock these validations and test only on *Field tests
        with self.assertRaises(ValueError) as context_manager:
            self.table.append({'name': 'Álvaro Justen'.encode('utf-8'),
                               'birthdate': '1987-04-29'})
        self.assertEqual(type(context_manager.exception), UnicodeDecodeError)

        with self.assertRaises(ValueError) as context_manager:
            self.table.append({'name': u'Álvaro Justen', 'birthdate': 'WRONG'})
        self.assertEqual(type(context_manager.exception), ValueError)
        self.assertIn('does not match format',
                      context_manager.exception.message)

    def test_table_getitem_error(self):
        with self.assertRaises(ValueError) as context_manager:
            self.table['test']

    def test_table_setitem(self):
        self.first_row['name'] = 'turicas'
        self.first_row['birthdate'] = datetime.date(2000, 1, 1)
        self.table[0] = self.first_row
        self.assertEqual(self.table[0].name, 'turicas')
        self.assertEqual(self.table[0].birthdate, datetime.date(2000, 1, 1))

    def test_table_delitem(self):
        table_rows = [row for row in self.table]
        before = len(self.table)
        del self.table[0]
        after = len(self.table)
        self.assertEqual(after, before - 1)
        for row, expected_row in zip(self.table, table_rows[1:]):
            self.assertEqual(row, expected_row)

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
            self.table.order_by('doesnt_exist')

        before = [row.birthdate for row in self.table]
        self.table.order_by('birthdate')
        after = [row.birthdate for row in self.table]
        self.assertNotEqual(before, after)
        self.assertEqual(sorted(before), after)

        self.table.order_by('-birthdate')
        final = [row.birthdate for row in self.table]
        self.assertEqual(final, list(reversed(after)))

        self.table.order_by('name')
        expected_rows = [
            {'name': 'Douglas Adams', 'birthdate': datetime.date(1952, 3, 11)},
            {'name': 'Somebody', 'birthdate': datetime.date(1990, 2, 1)},
            {'name': 'Álvaro Justen', 'birthdate': datetime.date(1987, 4, 29)}]
        for expected_row, row in zip(expected_rows, self.table):
            self.assertEqual(expected_row, dict(row._asdict()))
