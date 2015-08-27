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
import os

from collections import OrderedDict
from decimal import Decimal

import rows.fields as fields

from rows.table import Table


expected_fields = OrderedDict([('bool_column', fields.BoolField),
                               ('integer_column', fields.IntegerField),
                               ('float_column', fields.FloatField),
                               ('decimal_column', fields.FloatField),
                               ('percent_column', fields.PercentField),
                               ('date_column', fields.DateField),
                               ('datetime_column', fields.DatetimeField),
                               ('unicode_column', fields.UnicodeField),
                               ('null_column', fields.ByteField),])
expected_rows = [
        {'float_column': 3.141592,
         'decimal_column': 3.141592,
         'bool_column': True,
         'integer_column': 1,
         'date_column': datetime.date(2015, 1, 1),
         'datetime_column': datetime.datetime(2015, 8, 18, 15, 10),
         'percent_column': Decimal('0.01'),
         'unicode_column': 'Álvaro',
         'null_column': ''.encode('utf-8')},
        {'float_column': 1.234,
         'decimal_column': 1.234,
         'bool_column': False,
         'integer_column': 2,
         'date_column': datetime.date(1999, 2, 3),
         'datetime_column': datetime.datetime(1999, 2, 3, 0, 1, 2),
         'percent_column': Decimal('0.1169'),
         'unicode_column': 'àáãâä¹²³',
         'null_column': '-'.encode('utf-8')},
        {'float_column': 4.56,
         'decimal_column': 4.56,
         'bool_column': True,
         'integer_column': 3,
         'date_column': datetime.date(2050, 1, 2),
         'datetime_column': datetime.datetime(2050, 1, 2, 23, 45, 31),
         'percent_column': Decimal('0.12'),
         'unicode_column': 'éèẽêë',
         'null_column': 'null'.encode('utf-8')},
        {'float_column': 7.89,
         'decimal_column': 7.89,
         'bool_column': False,
         'integer_column': 4,
         'date_column': datetime.date(2015, 8, 18),
         'datetime_column': datetime.datetime(2015, 8, 18, 22, 21, 33),
         'percent_column': Decimal('0.1364'),
         'unicode_column': '~~~~',
         'null_column': 'nil'.encode('utf-8')},
        {'float_column': 9.87,
         'decimal_column': 9.87,
         'bool_column': True,
         'integer_column': 5,
         'date_column': datetime.date(2015, 3, 4),
         'datetime_column': datetime.datetime(2015, 3, 4, 16, 0, 1),
         'percent_column': Decimal('0.1314'),
         'unicode_column': 'álvaro',
         'null_column': 'none'.encode('utf-8')},
        {'float_column': 1.2345,
         'decimal_column': 1.2345,
         'bool_column': False,
         'integer_column': 6,
         'date_column': datetime.date(2015, 5, 6),
         'datetime_column': datetime.datetime(2015, 5, 6, 12, 1, 2),
         'percent_column': Decimal('0.02'),
         'unicode_column': 'test',
         'null_column': ''.encode('utf-8')},]
table = Table(fields=expected_fields)
for row in expected_rows:
    table.append(row)


class RowsTestMixIn(object):

    maxDiff = None

    def setUp(self):
        self.files_to_delete = []

    def tearDown(self):
        for filename in self.files_to_delete:
            os.unlink(filename)

    def assert_table_equal(self, first, second):
        self.assertEqual(first.fields, second.fields)
        self.assertEqual(len(first), len(second))

        for first_row, second_row in zip(first, second):
            self.assertEqual(first_row, second_row)

    def assert_file_contents_equal(self, first_filename, second_filename):
        with open(first_filename, 'rb') as fobj:
            first = fobj.read()
        with open(second_filename, 'rb') as fobj:
            second = fobj.read()
        self.assertEqual(first, second)
