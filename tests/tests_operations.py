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

from collections import OrderedDict

import rows
import rows.operations

import utils


class OperationsTestCase(utils.RowsTestMixIn, unittest.TestCase):

    def test_join_imports(self):
        self.assertIs(rows.join, rows.operations.join)

    def test_join_feature(self):
        tables = [rows.import_from_csv('tests/data/to-merge-1.csv'),
                  rows.import_from_csv('tests/data/to-merge-2.csv'),
                  rows.import_from_csv('tests/data/to-merge-3.csv'),]
        merged = rows.join(keys=('id', 'username'), tables=tables)
        expected = rows.import_from_csv('tests/data/merged.csv')
        self.assert_table_equal(merged, expected)

    def test_transform_imports(self):
        self.assertIs(rows.transform, rows.operations.transform)

    def test_transform_feature(self):

        def transformation_function(row, table):
            if row.percent_column < 0.1269:
                return None  # discard this row

            new = row._asdict()
            new['meta'] = ', '.join(['{} => {}'.format(key, value)
                                     for key, value in table._meta.items()])
            return new

        fields = utils.table.fields.copy()
        fields.update({'meta': rows.fields.UnicodeField})
        tables = [utils.table] * 3
        result = rows.transform(fields, transformation_function, *tables)
        self.assertEqual(result.fields, fields)
        not_discarded = [transformation_function(row, utils.table)
                         for row in utils.table] * 3
        not_discarded = [row for row in not_discarded if row is not None]
        self.assertEqual(len(result), len(not_discarded))

        for expected_row, row in zip(not_discarded, result):
            self.assertEqual(expected_row, dict(row._asdict()))

    def test_serialize_imports(self):
        self.assertIs(rows.serialize, rows.operations.serialize)

    def test_serialize_feature(self):
        result = rows.serialize(utils.table)
        field_types = utils.table.fields.values()
        self.assertEqual(result.next(), utils.table.fields.keys())

        for row, expected_row in zip(result, utils.table._rows):
            values = [field_type.serialize(value)
                      for field_type, value in zip(field_types, expected_row)]
            self.assertEqual(values, row)

    def test_transpose_imports(self):
        self.assertIs(rows.transpose, rows.operations.transpose)

    def test_transpose_feature(self):
        new_fields = OrderedDict([('key', rows.fields.UnicodeField),
                                  ('value_1', rows.fields.UnicodeField),
                                  ('value_2', rows.fields.UnicodeField)])
        table = rows.Table(fields=new_fields)
        table.append({'key': 'first_key', 'value_1': 'first_value_1',
                      'value_2': 'first_value_2', })
        table.append({'key': 'second_key', 'value_1': 1,
                      'value_2': 2, })
        table.append({'key': 'third_key', 'value_1': 3.14,
                      'value_2': 2.71, })
        table.append({'key': 'fourth_key', 'value_1': '2015-09-04',
                      'value_2': '2015-08-29', })

        new_table = rows.transpose(table, fields_column='key')

        self.assertEqual(len(new_table), 2)
        self.assertEqual(len(new_table.fields), len(table))
        self.assertEqual(new_table.fields.keys(), [row.key for row in table])
        self.assertEqual(new_table[0].first_key, 'first_value_1')
        self.assertEqual(new_table[0].second_key, 1)
        self.assertEqual(new_table[0].third_key, 3.14)
        self.assertEqual(new_table[0].fourth_key, datetime.date(2015, 9, 4))
        self.assertEqual(new_table[1].first_key, 'first_value_2')
        self.assertEqual(new_table[1].second_key, 2)
        self.assertEqual(new_table[1].third_key, 2.71)
        self.assertEqual(new_table[1].fourth_key, datetime.date(2015, 8, 29))
