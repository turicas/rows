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


class TableMergeTestCase(utils.RowsTestMixIn, unittest.TestCase):

    def test_join_imports(self):
        self.assertIs(rows.join, rows.operations.join)

    def test_join_feature(self):
        tables = [rows.import_from_csv('tests/data/to-merge-1.csv'),
                  rows.import_from_csv('tests/data/to-merge-2.csv'),
                  rows.import_from_csv('tests/data/to-merge-3.csv'),]
        merged = rows.join(keys=('id', 'username'), tables=tables)
        expected = rows.import_from_csv('tests/data/merged.csv')
        self.assert_table_equal(merged, expected)
