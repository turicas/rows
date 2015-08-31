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

import unittest

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
