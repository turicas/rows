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


NONE_VALUES = list(fields.NULL) + ['', None]
FIELDS = OrderedDict([('bool_column', fields.BoolField),
                      ('integer_column', fields.IntegerField),
                      ('float_column', fields.FloatField),
                      ('decimal_column', fields.FloatField),
                      ('percent_column', fields.PercentField),
                      ('date_column', fields.DateField),
                      ('datetime_column', fields.DatetimeField),
                      ('unicode_column', fields.UnicodeField),
                      ('null_column', fields.ByteField),])
FIELD_NAMES = FIELDS.keys()
EXPECTED_ROWS = [
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
         'null_column': 'n/a'.encode('utf-8')},]
table = Table(fields=FIELDS)
for row in EXPECTED_ROWS:
    table.append(row)
table._meta = {'test': 123}


class RowsTestMixIn(object):

    maxDiff = None

    def setUp(self):
        self.files_to_delete = []

    def tearDown(self):
        for filename in self.files_to_delete:
            os.unlink(filename)

    def assert_table_equal(self, first, second):
        self.assertDictEqual(dict(first.fields), dict(second.fields))
        self.assertEqual(len(first), len(second))

        for first_row, second_row in zip(first, second):
            self.assertDictEqual(dict(first_row._asdict()),
                                 dict(second_row._asdict()))

    def assert_file_contents_equal(self, first_filename, second_filename):
        with open(first_filename, 'rb') as fobj:
            first = fobj.read()
        with open(second_filename, 'rb') as fobj:
            second = fobj.read()
        self.assertEqual(first, second)

    def assert_create_table_data(self, call_args, field_ordering=True):
        kwargs = call_args[1]
        expected_meta = {'imported_from': self.plugin_name,
                         'filename': self.filename, }
        self.assertEqual(kwargs['meta'], expected_meta)
        del kwargs['meta']
        self.assert_table_data(call_args[0][0], args=[], kwargs=kwargs,
                               field_ordering=field_ordering)

    def assert_table_data(self, data, args, kwargs, field_ordering):
        field_types = {field_name: field_type.TYPE
                       for field_name, field_type in FIELDS.items()}
        data = list(data)
        if field_ordering:
            self.assertEqual(data[0], FIELD_NAMES)

            for row_index, row in enumerate(data[1:]):
                for column_index, value in enumerate(row):
                    field_name = FIELD_NAMES[column_index]
                    expected_value = EXPECTED_ROWS[row_index][field_name]
                    self.field_assert(field_name, expected_value, value, *args,
                                      **kwargs)
        else:
            self.assertEqual(set(data[0]), set(FIELD_NAMES))
            for row_index, row in enumerate(data[1:]):
                for column_index, value in enumerate(row):
                    field_name = data[0][column_index]
                    expected_value = EXPECTED_ROWS[row_index][field_name]
                    self.field_assert(field_name, expected_value, value, *args,
                                      **kwargs)

    # Fields asserts: input values we expect from plugins

    def field_assert(self, field_name, expected_value, value, *args, **kwargs):
        asserts = {'bool_column': self.assert_BoolField,
                   'integer_column': self.assert_IntegerField,
                   'float_column': self.assert_FloatField,
                   'decimal_column': self.assert_DecimalField,
                   'percent_column': self.assert_PercentField,
                   'date_column': self.assert_DateField,
                   'datetime_column': self.assert_DatetimeField,
                   'unicode_column': self.assert_UnicodeField,
                   'null_column': self.assert_None_value, }
        return asserts[field_name](expected_value, value, *args, **kwargs)

    def assert_BoolField(self, expected_value, value, *args, **kwargs):
        if expected_value is True:
            assert value in (True, 1, '1', 'true', 'yes')
        elif expected_value is False:
            assert value in (False, 0, '0', 'false', 'no')
        else:
            # TODO: what about None?
            raise ValueError('expected_value is not True or False')

    def assert_IntegerField(self, expected_value, value, *args, **kwargs):
        self.assertIn(value, (expected_value, str(expected_value)))


    def assert_FloatField(self, expected_value, value, *args, **kwargs):
        if type(value) != type(expected_value):
            self.assertEqual(value, str(expected_value))
        else:
            self.assertAlmostEqual(expected_value, value, places=5)


    def assert_DecimalField(self, expected_value, value, *args, **kwargs):
        return self.assert_FloatField(expected_value, value)


    def assert_PercentField(self, expected_value, value, *args, **kwargs):
        float_value = float(expected_value) * 100
        possible_values = [str(float_value) + '%',
                           str(float_value) + '.0%',
                           str(float_value) + '.00%']
        if int(float_value) == float_value:
            possible_values.append(str(int(float_value)) + '%')
        self.assertIn(value, possible_values)


    def assert_DateField(self, expected_value, value, *args, **kwargs):
        self.assertEqual(str(expected_value), value)


    def assert_DatetimeField(self, expected_value, value, *args, **kwargs):
        self.assertEqual(str(expected_value).replace(' ', 'T'), value)


    def assert_UnicodeField(self, expected_value, value, *args, **kwargs):
        self.assertEqual(expected_value, value)


    def assert_None_value(self, expected_value, value, *args, **kwargs):
        self.assertIn(value, NONE_VALUES)
