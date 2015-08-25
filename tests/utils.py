# coding: utf-8

from __future__ import unicode_literals

import datetime

from collections import OrderedDict
from decimal import Decimal

import rows.fields


expected_fields = OrderedDict([('bool_column', rows.fields.BoolField),
                               ('integer_column', rows.fields.IntegerField),
                               ('float_column', rows.fields.FloatField),
                               ('decimal_column', rows.fields.FloatField),
                               ('percent_column', rows.fields.PercentField),
                               ('date_column', rows.fields.DateField),
                               ('datetime_column', rows.fields.DatetimeField),
                               ('unicode_column', rows.fields.UnicodeField),
                               ('null_column', rows.fields.ByteField),])

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


class ExpectedTableMixIn(object):

    maxDiff = None

    def assert_expected_table(self, table):
        self.assertEqual(table.fields, expected_fields)

        for expected_row, row in zip(expected_rows, table):
            row = dict(row._asdict())
            self.assertEqual(set(expected_row.keys()), set(row.keys()))
            for key in expected_row:
                expected_value = expected_row[key]
                value = row[key]
                self.assertEqual(type(expected_value), type(value))
                self.assertEqual(expected_value, value)
