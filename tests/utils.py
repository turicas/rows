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

import copy
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
                      ('unicode_column', fields.TextField),
                      ('null_column', fields.BinaryField),])
FIELD_NAMES = list(FIELDS.keys())
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
    override_fields = None

    def setUp(self):
        self.files_to_delete = []

    def tearDown(self):
        for filename in self.files_to_delete:
            os.unlink(filename)

    def assert_table_equal(self, first, second):
        expected_fields = dict(second.fields)
        if self.override_fields is None:
            override_fields = {}
        else:
            override_fields = self.override_fields
            expected_fields = copy.deepcopy(expected_fields)
            expected_fields.update(override_fields)

        self.assertDictEqual(dict(first.fields), expected_fields)
        self.assertEqual(len(first), len(second))

        for first_row, second_row in zip(first, second):
            first_row = dict(first_row._asdict())
            second_row = dict(second_row._asdict())
            for field_name, field_type in list(expected_fields.items()):
                value = first_row[field_name]
                expected_value = second_row[field_name]
                if field_name in override_fields:
                    expected_value = override_fields[field_name]\
                            .deserialize(expected_value)
                if float not in (type(value), type(expected_value)):
                    self.assertEqual(value, expected_value)
                else:
                    self.assertAlmostEqual(value, expected_value)

    def assert_file_contents_equal(self, first_filename, second_filename):
        with open(first_filename, 'rb') as fobj:
            first = fobj.read()
        with open(second_filename, 'rb') as fobj:
            second = fobj.read()
        self.assertEqual(first, second)

    def assert_create_table_data(self, call_args, field_ordering=True,
                                 filename=None):
        if filename is None:
            filename = self.filename
        kwargs = call_args[1]
        expected_meta = {'imported_from': self.plugin_name,
                         'filename': filename, }
        self.assertEqual(kwargs['meta'], expected_meta)
        del kwargs['meta']
        self.assert_table_data(call_args[0][0], args=[], kwargs=kwargs,
                               field_ordering=field_ordering)

    def assert_table_data(self, data, args, kwargs, field_ordering):
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
                   'unicode_column': self.assert_TextField,
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
        value = str(value)
        if value.endswith('00:00:00'):
            value = value[:-9]
        self.assertEqual(str(expected_value), value)


    def assert_DatetimeField(self, expected_value, value, *args, **kwargs):
        if type(value) is datetime.datetime and \
                type(expected_value) is datetime.datetime:
            # if both types are datetime, check delta
            # XLSX plugin has not a good precision and will change milliseconds
            delta_1 = expected_value - value
            delta_2 = value - expected_value
            self.assertTrue(str(delta_1).startswith('0:00:00') or
                            str(delta_2).startswith('0:00:00'))
        else:
            # if not, convert values to string and verify if are equal
            value = str(value)
            self.assertEqual(str(expected_value).replace(' ', 'T'), value)


    def assert_TextField(self, expected_value, value, *args, **kwargs):
        self.assertEqual(expected_value, value)


    def assert_None_value(self, expected_value, value, *args, **kwargs):
        self.assertIn(value, NONE_VALUES)
