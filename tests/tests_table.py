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

import datetime
import unittest

import rows
import rows.fields as fields

from rows.table import Table


class TableTestCase(unittest.TestCase):

    def test_Table_is_present_on_main_namespace(self):
        self.assertIn('Table', dir(rows))
        self.assertIs(Table, rows.Table)

    def test_table(self):
        table = Table(fields={'name': rows.fields.UnicodeField,
                              'birthdate': rows.fields.DateField, })
        table.append({'name': u'Álvaro Justen',
                      'birthdate': datetime.date(1987, 4, 29)})
        table.append({'name': u'Somebody',
                      'birthdate': datetime.date(1990, 2, 1)})
        table.append({'name': u'Douglas Adams',
                      'birthdate': '1952-03-11'})

        table_rows = [row for row in table]
        self.assertEqual(len(table_rows), 3)
        self.assertEqual(table_rows[0].name, u'Álvaro Justen')
        self.assertEqual(table_rows[0].birthdate, datetime.date(1987, 4, 29))
        self.assertEqual(table_rows[1].name, u'Somebody')
        self.assertEqual(table_rows[1].birthdate, datetime.date(1990, 2, 1))
        self.assertEqual(table_rows[2].name, u'Douglas Adams')
        self.assertEqual(table_rows[2].birthdate, datetime.date(1952, 3, 11))

        # TODO: may mock these validations and test only on *Field tests
        with self.assertRaises(ValueError) as context_manager:
            table.append({'name': 'Álvaro Justen', 'birthdate': '1987-04-29'})
        self.assertEqual(type(context_manager.exception), UnicodeDecodeError)

        with self.assertRaises(ValueError) as context_manager:
            table.append({'name': u'Álvaro Justen', 'birthdate': 'WRONG'})
        self.assertEqual(type(context_manager.exception), ValueError)
        self.assertIn('does not match format',
                      context_manager.exception.message)
