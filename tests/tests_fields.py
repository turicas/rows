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

import collections
import datetime
import unittest
import types

from decimal import Decimal

import rows

from rows import fields


class FieldsTestCase(unittest.TestCase):

    def test_Field(self):
        self.assertIs(fields.Field.TYPE, types.NoneType)
        self.assertIs(fields.Field.deserialize(None), None)
        self.assertEqual(fields.Field.deserialize('Álvaro'), 'Álvaro')
        self.assertEqual(fields.Field.serialize(None), '')
        self.assertIs(type(fields.Field.serialize(None)), types.UnicodeType)
        self.assertEqual(fields.Field.serialize('Álvaro'), 'Álvaro')
        self.assertIs(type(fields.Field.serialize('Álvaro')),
                      types.UnicodeType)

    def test_ByteField(self):
        serialized = 'Álvaro'.encode('utf-8')
        self.assertIs(fields.ByteField.TYPE, types.StringType)
        self.assertIs(fields.ByteField.deserialize(None), None)
        self.assertEqual(fields.ByteField.deserialize(serialized), serialized)
        self.assertIs(type(fields.ByteField.deserialize(serialized)),
                      types.StringType)
        self.assertEqual(fields.ByteField.serialize(None), '')
        self.assertIs(type(fields.ByteField.serialize(None)), types.StringType)
        self.assertEqual(fields.ByteField.serialize(serialized), serialized)
        self.assertIs(type(fields.ByteField.serialize(serialized)),
                      types.StringType)

    def test_BoolField(self):
        self.assertIs(fields.BoolField.TYPE, bool)
        self.assertEqual(fields.BoolField.serialize(None), '')
        self.assertIs(type(fields.BoolField.serialize(None)),
                      types.UnicodeType)
        self.assertIs(type(fields.BoolField.deserialize('true')),
                      fields.BoolField.TYPE)

        self.assertIs(fields.BoolField.deserialize('0'), False)
        self.assertIs(fields.BoolField.deserialize('false'), False)
        self.assertIs(fields.BoolField.deserialize('no'), False)
        self.assertIs(fields.BoolField.deserialize(None), None)
        self.assertIs(fields.BoolField.deserialize(True), True)
        self.assertIs(fields.BoolField.deserialize(False), False)
        self.assertEqual(fields.BoolField.serialize(False), 'false')
        self.assertIs(type(fields.BoolField.serialize(False)),
                      types.UnicodeType)

        self.assertIs(fields.BoolField.deserialize('1'), True)
        self.assertIs(fields.BoolField.deserialize(1), True)
        self.assertIs(fields.BoolField.deserialize('true'), True)
        self.assertIs(fields.BoolField.deserialize('yes'), True)
        self.assertEqual(fields.BoolField.serialize(True), 'true')
        self.assertIs(type(fields.BoolField.serialize(True)),
                      types.UnicodeType)

    def test_IntegerField(self):
        self.assertIs(fields.IntegerField.TYPE, int)
        self.assertEqual(fields.IntegerField.serialize(None), '')
        self.assertIs(type(fields.IntegerField.serialize(None)),
                      types.UnicodeType)
        self.assertIs(type(fields.IntegerField.deserialize('42')),
                      fields.IntegerField.TYPE)
        self.assertEqual(fields.IntegerField.deserialize('42'), 42)
        self.assertEqual(fields.IntegerField.deserialize(42), 42)
        self.assertEqual(fields.IntegerField.serialize(42), '42')
        self.assertIs(type(fields.IntegerField.serialize(42)),
                      types.UnicodeType)
        self.assertEqual(fields.IntegerField.deserialize(None), None)

        with rows.locale_context('pt_BR.UTF-8'):
            self.assertEqual(fields.IntegerField.serialize(42000), '42000')
            self.assertIs(type(fields.IntegerField.serialize(42000)),
                          types.UnicodeType)
            self.assertEqual(fields.IntegerField.serialize(42000,
                                                           grouping=True),
                             '42.000')
            self.assertEqual(fields.IntegerField.deserialize('42.000'), 42000)

        with self.assertRaises(ValueError):
            fields.IntegerField.deserialize(1.23)

    def test_FloatField(self):
        self.assertIs(fields.FloatField.TYPE, float)
        self.assertEqual(fields.FloatField.serialize(None), '')
        self.assertIs(type(fields.FloatField.serialize(None)),
                      types.UnicodeType)
        self.assertIs(type(fields.FloatField.deserialize('42.0')),
                      fields.FloatField.TYPE)
        self.assertEqual(fields.FloatField.deserialize('42.0'), 42.0)
        self.assertEqual(fields.FloatField.deserialize(42.0), 42.0)
        self.assertEqual(fields.FloatField.deserialize(None), None)
        self.assertEqual(fields.FloatField.serialize(42.0), '42.0')
        self.assertIs(type(fields.FloatField.serialize(42.0)),
                      types.UnicodeType)

        with rows.locale_context('pt_BR.UTF-8'):
            self.assertEqual(fields.FloatField.serialize(42000.0),
                             '42000,000000')
            self.assertIs(type(fields.FloatField.serialize(42000.0)),
                          types.UnicodeType)
            self.assertEqual(fields.FloatField.serialize(42000, grouping=True),
                             '42.000,000000')
            self.assertEqual(fields.FloatField.deserialize('42.000,00'),
                             42000.0)

    def test_DecimalField(self):
        deserialized = Decimal('42.010')
        self.assertIs(fields.DecimalField.TYPE, Decimal)
        self.assertEqual(fields.DecimalField.serialize(None), '')
        self.assertIs(type(fields.DecimalField.serialize(None)),
                      types.UnicodeType)
        self.assertIs(type(fields.DecimalField.deserialize('42.0')),
                      fields.DecimalField.TYPE)
        self.assertEqual(fields.DecimalField.deserialize('42.0'),
                         Decimal('42.0'))
        self.assertEqual(fields.DecimalField.deserialize(deserialized),
                         deserialized)
        self.assertEqual(fields.DecimalField.serialize(deserialized),
                         '42.010')
        self.assertEqual(type(fields.DecimalField.serialize(deserialized)),
                         types.UnicodeType)
        self.assertEqual(fields.DecimalField.deserialize('21.21657469231'),
                         Decimal('21.21657469231'))
        self.assertEqual(fields.DecimalField.deserialize(None), None)

        with rows.locale_context('pt_BR.UTF-8'):
            self.assertEqual(types.UnicodeType,
                    type(fields.DecimalField.serialize(deserialized)))
            self.assertEqual(fields.DecimalField.serialize(Decimal('4200')),
                             '4200')
            self.assertEqual(fields.DecimalField.serialize(Decimal('42.0')),
                             '42,0')
            self.assertEqual(fields.DecimalField.serialize(Decimal('42000.0')),
                             '42000,0')
            self.assertEqual(fields.DecimalField.deserialize('42.000,00'),
                             Decimal('42000.00'))
            self.assertEqual(fields.DecimalField.serialize(Decimal('42000.0'),
                                                    grouping=True),
                             '42.000,0')

    def test_PercentField(self):
        deserialized = Decimal('0.42010')
        self.assertIs(fields.PercentField.TYPE, Decimal)
        self.assertIs(type(fields.PercentField.deserialize('42.0%')),
                      fields.PercentField.TYPE)
        self.assertEqual(fields.PercentField.deserialize('42.0%'),
                         Decimal('0.420'))
        self.assertEqual(fields.PercentField.deserialize(Decimal('0.420')),
                         Decimal('0.420'))
        self.assertEqual(fields.PercentField.deserialize(deserialized),
                         deserialized)
        self.assertEqual(fields.PercentField.deserialize(None), None)
        self.assertEqual(fields.PercentField.serialize(deserialized),
                         '42.010%')
        self.assertEqual(type(fields.PercentField.serialize(deserialized)),
                         types.UnicodeType)
        self.assertEqual(fields.PercentField.serialize(Decimal('42.010')),
                         '4201.0%')
        self.assertEqual(fields.PercentField.serialize(Decimal('0.01')), '1%')

        with rows.locale_context('pt_BR.UTF-8'):
            self.assertEqual(type(fields.PercentField.serialize(deserialized)),
                            types.UnicodeType)
            self.assertEqual(fields.PercentField.serialize(Decimal('42.0')),
                             '4200%')
            self.assertEqual(fields.PercentField.serialize(Decimal('42000.0')),
                             '4200000%')
            self.assertEqual(fields.PercentField.deserialize('42.000,00%'),
                             Decimal('420.0000'))
            self.assertEqual(fields.PercentField.serialize(Decimal('42000.00'),
                                                           grouping=True),
                             '4.200.000%')
        with self.assertRaises(ValueError):
            fields.PercentField.deserialize(42)

    def test_DateField(self):
        # TODO: test timezone-aware datetime.date
        serialized = types.StringType('2015-05-27')
        deserialized = datetime.date(2015, 5, 27)
        self.assertIs(fields.DateField.TYPE, datetime.date)
        self.assertEqual(fields.DateField.serialize(None),
                         '')
        self.assertIs(type(fields.DateField.serialize(None)),
                      types.UnicodeType)
        self.assertIs(type(fields.DateField.deserialize(serialized)),
                      fields.DateField.TYPE)
        self.assertEqual(fields.DateField.deserialize(serialized),
                         deserialized)
        self.assertEqual(fields.DateField.deserialize(deserialized),
                         deserialized)
        self.assertEqual(fields.DateField.deserialize(None), None)
        self.assertEqual(fields.DateField.serialize(deserialized),
                         serialized)
        self.assertIs(type(fields.DateField.serialize(deserialized)),
                      types.UnicodeType)
        with self.assertRaises(ValueError):
            fields.DateField.deserialize(42)
        with self.assertRaises(ValueError):
            fields.DateField.deserialize(serialized + 'T00:00:00')

    def test_DatetimeField(self):
        # TODO: test timezone-aware datetime.date
        serialized = types.StringType('2015-05-27T01:02:03')
        self.assertIs(fields.DatetimeField.TYPE, datetime.datetime)
        deserialized = fields.DatetimeField.deserialize(serialized)
        self.assertIs(type(deserialized), fields.DatetimeField.TYPE)
        self.assertEqual(fields.DatetimeField.serialize(None), '')
        self.assertIs(type(fields.DatetimeField.serialize(None)),
                      types.UnicodeType)

        value = datetime.datetime(2015, 5, 27, 1, 2, 3)
        self.assertEqual(fields.DatetimeField.deserialize(serialized), value)
        self.assertEqual(fields.DatetimeField.deserialize(deserialized),
                         deserialized)
        self.assertEqual(fields.DatetimeField.deserialize(None), None)
        self.assertEqual(fields.DatetimeField.serialize(value), serialized)
        self.assertIs(type(fields.DatetimeField.serialize(value)),
                      types.UnicodeType)
        with self.assertRaises(ValueError):
            fields.DatetimeField.deserialize(42)
            fields.DatetimeField.deserialize('2015-01-01')

    def test_UnicodeField(self):
        self.assertIs(fields.UnicodeField.TYPE, unicode)
        self.assertEqual(fields.UnicodeField.serialize(None), '')
        self.assertIs(type(fields.UnicodeField.serialize(None)),
                      types.UnicodeType)
        self.assertIs(type(fields.UnicodeField.deserialize('test')),
                      fields.UnicodeField.TYPE)
        self.assertEqual(fields.UnicodeField.deserialize('Álvaro'.encode('utf-8'),
                                                         encoding='utf-8'),
                         'Álvaro')
        self.assertEqual(fields.UnicodeField.deserialize('Álvaro'),
                         'Álvaro')
        self.assertIs(fields.UnicodeField.deserialize(None), None)
        self.assertEqual(fields.UnicodeField.serialize('Álvaro'),
                         'Álvaro')
        self.assertIs(type(fields.UnicodeField.serialize('Álvaro')),
                      types.UnicodeType)


class FieldUtilsTestCase(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        with open('tests/data/all-field-types.csv') as fobj:
            lines = fobj.read().splitlines()
        lines = [line.split(','.encode('utf-8')) for line in lines]
        self.fields = lines[0]
        self.data = lines[1:]
        self.expected = {'bool_column': fields.BoolField,
                         'integer_column': fields.IntegerField,
                         'float_column': fields.FloatField,
                         'decimal_column': fields.FloatField,
                         'percent_column': fields.PercentField,
                         'date_column': fields.DateField,
                         'datetime_column': fields.DatetimeField,
                         'unicode_column': fields.UnicodeField,
                         'null_column': fields.ByteField,}

    def test_detect_types_utf8(self):
        result = fields.detect_types(self.fields, self.data,
                                           encoding='utf-8')
        self.assertEqual(type(result), collections.OrderedDict)
        self.assertEqual(result.keys(), self.fields)
        self.assertDictEqual(dict(result), self.expected)

    def test_detect_types_unicode(self):
        data = [[field.decode('utf-8') for field in row] for row in self.data]
        result = fields.detect_types(self.fields, data)
        self.assertDictEqual(dict(result), self.expected)


class FieldsFunctionsTestCase(unittest.TestCase):

    def test_is_null(self):
        self.assertEqual(fields.is_null(None), True)
        self.assertEqual(fields.is_null(''), True)
        self.assertEqual(fields.is_null(' \t '), True)
        self.assertEqual(fields.is_null('null'), True)
        self.assertEqual(fields.is_null('nil'), True)
        self.assertEqual(fields.is_null('none'), True)
        self.assertEqual(fields.is_null('-'), True)

        self.assertEqual(fields.is_null('Álvaro'), False)
        self.assertEqual(fields.is_null('Álvaro'.encode('utf-8')), False)

    def test_as_string(self):
        self.assertEqual(fields.as_string(None), 'None')
        self.assertEqual(fields.as_string(42), '42')
        self.assertEqual(fields.as_string(3.141592), '3.141592')
        self.assertEqual(fields.as_string('Álvaro'), 'Álvaro')
        self.assertEqual(fields.as_string('Álvaro'.encode('utf-8')),
                         'Álvaro'.encode('utf-8'))
