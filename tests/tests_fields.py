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
import json
import platform
import unittest

from base64 import b64encode
from decimal import Decimal

import rows
import six

from rows import fields


if platform.system() == 'Windows':
    locale_name = 'ptb_bra'
else:
    locale_name = 'pt_BR.UTF-8'


class FieldsTestCase(unittest.TestCase):

    def test_Field(self):
        self.assertEqual(fields.Field.TYPE, (type(None), ))
        self.assertIs(fields.Field.deserialize(None), None)
        self.assertEqual(fields.Field.deserialize('Álvaro'), 'Álvaro')
        self.assertEqual(fields.Field.serialize(None), '')
        self.assertIs(type(fields.Field.serialize(None)), six.text_type)
        self.assertEqual(fields.Field.serialize('Álvaro'), 'Álvaro')
        self.assertIs(type(fields.Field.serialize('Álvaro')), six.text_type)

    def test_BinaryField(self):
        deserialized = 'Álvaro'.encode('utf-8')
        serialized = b64encode(deserialized).decode('ascii')

        self.assertEqual(type(deserialized), six.binary_type)
        self.assertEqual(type(serialized), six.text_type)

        self.assertEqual(fields.BinaryField.TYPE, (bytes, ))

        self.assertEqual(fields.BinaryField.serialize(None), '')
        self.assertIs(type(fields.BinaryField.serialize(None)), six.text_type)
        self.assertEqual(fields.BinaryField.serialize(deserialized),
                         serialized)
        self.assertIs(type(fields.BinaryField.serialize(deserialized)),
                      six.text_type)
        with self.assertRaises(ValueError):
            fields.BinaryField.serialize(42)
        with self.assertRaises(ValueError):
            fields.BinaryField.serialize(3.14)
        with self.assertRaises(ValueError):
            fields.BinaryField.serialize('Álvaro')
        with self.assertRaises(ValueError):
            fields.BinaryField.serialize('123')

        self.assertIs(fields.BinaryField.deserialize(None), b'')
        self.assertEqual(fields.BinaryField.deserialize(serialized),
                         deserialized)
        self.assertIs(type(fields.BinaryField.deserialize(serialized)),
                      six.binary_type)
        with self.assertRaises(ValueError):
            fields.BinaryField.deserialize(42)
        with self.assertRaises(ValueError):
            fields.BinaryField.deserialize(3.14)
        with self.assertRaises(ValueError):
            fields.BinaryField.deserialize('Álvaro')

        self.assertEqual(fields.BinaryField.deserialize(deserialized),
                         deserialized)
        self.assertEqual(fields.BinaryField.deserialize(serialized),
                         deserialized)
        self.assertEqual(
                fields.BinaryField.deserialize(serialized.encode('ascii')),
                serialized.encode('ascii')
            )

    def test_BoolField(self):
        self.assertEqual(fields.BoolField.TYPE, (bool, ))
        self.assertEqual(fields.BoolField.serialize(None), '')

        false_values = ('False', 'false', 'no', False)
        for value in false_values:
            self.assertIs(fields.BoolField.deserialize(value), False)

        self.assertIs(fields.BoolField.deserialize(None), None)
        self.assertEqual(fields.BoolField.deserialize(''), None)

        true_values = ('True', 'true', 'yes', True)
        for value in true_values:
            self.assertIs(fields.BoolField.deserialize(value), True)

        self.assertEqual(fields.BoolField.serialize(False), 'false')
        self.assertIs(type(fields.BoolField.serialize(False)), six.text_type)

        self.assertEqual(fields.BoolField.serialize(True), 'true')
        self.assertIs(type(fields.BoolField.serialize(True)), six.text_type)

        # '0' and '1' should be not accepted as boolean values because the
        # sample could not contain other integers but the actual type could be
        # integer
        with self.assertRaises(ValueError):
            fields.BoolField.deserialize('0')
        with self.assertRaises(ValueError):
            fields.BoolField.deserialize(b'0')
        with self.assertRaises(ValueError):
            fields.BoolField.deserialize('1')
        with self.assertRaises(ValueError):
            fields.BoolField.deserialize(b'1')

    def test_IntegerField(self):
        self.assertEqual(fields.IntegerField.TYPE, (int, ))
        self.assertEqual(fields.IntegerField.serialize(None), '')
        self.assertIs(type(fields.IntegerField.serialize(None)), six.text_type)
        self.assertIn(type(fields.IntegerField.deserialize('42')),
                      fields.IntegerField.TYPE)
        self.assertEqual(fields.IntegerField.deserialize('42'), 42)
        self.assertEqual(fields.IntegerField.deserialize(42), 42)
        self.assertEqual(fields.IntegerField.serialize(42), '42')
        self.assertIs(type(fields.IntegerField.serialize(42)), six.text_type)
        self.assertEqual(fields.IntegerField.deserialize(None), None)
        self.assertEqual(fields.IntegerField.deserialize('10152709355006317'),
                         10152709355006317)

        with rows.locale_context(locale_name):
            self.assertEqual(fields.IntegerField.serialize(42000), '42000')
            self.assertIs(type(fields.IntegerField.serialize(42000)),
                          six.text_type)
            self.assertEqual(fields.IntegerField.serialize(42000,
                                                           grouping=True),
                             '42.000')
            self.assertEqual(fields.IntegerField.deserialize('42.000'), 42000)
            self.assertEqual(fields.IntegerField.deserialize(42), 42)
            self.assertEqual(fields.IntegerField.deserialize(42.0), 42)

        with self.assertRaises(ValueError):
            fields.IntegerField.deserialize(1.23)

    def test_FloatField(self):
        self.assertEqual(fields.FloatField.TYPE, (float, ))
        self.assertEqual(fields.FloatField.serialize(None), '')
        self.assertIs(type(fields.FloatField.serialize(None)), six.text_type)
        self.assertIn(type(fields.FloatField.deserialize('42.0')),
                      fields.FloatField.TYPE)
        self.assertEqual(fields.FloatField.deserialize('42.0'), 42.0)
        self.assertEqual(fields.FloatField.deserialize(42.0), 42.0)
        self.assertEqual(fields.FloatField.deserialize(42), 42.0)
        self.assertEqual(fields.FloatField.deserialize(None), None)
        self.assertEqual(fields.FloatField.serialize(42.0), '42.0')
        self.assertIs(type(fields.FloatField.serialize(42.0)), six.text_type)

        with rows.locale_context(locale_name):
            self.assertEqual(fields.FloatField.serialize(42000.0),
                             '42000,000000')
            self.assertIs(type(fields.FloatField.serialize(42000.0)),
                          six.text_type)
            self.assertEqual(fields.FloatField.serialize(42000, grouping=True),
                             '42.000,000000')
            self.assertEqual(fields.FloatField.deserialize('42.000,00'),
                             42000.0)
            self.assertEqual(fields.FloatField.deserialize(42), 42.0)
            self.assertEqual(fields.FloatField.deserialize(42.0), 42.0)

    def test_DecimalField(self):
        deserialized = Decimal('42.010')
        self.assertEqual(fields.DecimalField.TYPE, (Decimal, ))
        self.assertEqual(fields.DecimalField.serialize(None), '')
        self.assertIs(type(fields.DecimalField.serialize(None)), six.text_type)
        self.assertEqual(fields.DecimalField.deserialize(''), None)
        self.assertIn(type(fields.DecimalField.deserialize('42.0')),
                      fields.DecimalField.TYPE)
        self.assertEqual(fields.DecimalField.deserialize('42.0'),
                         Decimal('42.0'))
        self.assertEqual(fields.DecimalField.deserialize(deserialized),
                         deserialized)
        self.assertEqual(fields.DecimalField.serialize(deserialized),
                         '42.010')
        self.assertEqual(type(fields.DecimalField.serialize(deserialized)),
                         six.text_type)
        self.assertEqual(fields.DecimalField.deserialize('21.21657469231'),
                         Decimal('21.21657469231'))
        self.assertEqual(fields.DecimalField.deserialize('-21.34'),
                         Decimal('-21.34'))
        self.assertEqual(fields.DecimalField.serialize(Decimal('-21.34')),
                         '-21.34')
        self.assertEqual(fields.DecimalField.deserialize(None), None)

        with rows.locale_context(locale_name):
            self.assertEqual(
                six.text_type,
                type(fields.DecimalField.serialize(deserialized))
            )
            self.assertEqual(fields.DecimalField.serialize(Decimal('4200')),
                             '4200')
            self.assertEqual(fields.DecimalField.serialize(Decimal('42.0')),
                             '42,0')
            self.assertEqual(fields.DecimalField.serialize(Decimal('42000.0')),
                             '42000,0')
            self.assertEqual(fields.DecimalField.serialize(Decimal('-42.0')),
                             '-42,0')
            self.assertEqual(fields.DecimalField.deserialize('42.000,00'),
                             Decimal('42000.00'))
            self.assertEqual(fields.DecimalField.deserialize('-42.000,00'),
                             Decimal('-42000.00'))
            self.assertEqual(
                fields.DecimalField.serialize(
                    Decimal('42000.0'),
                    grouping=True
                ),
                '42.000,0'
            )
            self.assertEqual(fields.DecimalField.deserialize(42000),
                             Decimal('42000'))
            self.assertEqual(fields.DecimalField.deserialize(42000.0),
                             Decimal('42000'))

    def test_PercentField(self):
        deserialized = Decimal('0.42010')
        self.assertEqual(fields.PercentField.TYPE, (Decimal, ))
        self.assertIn(type(fields.PercentField.deserialize('42.0%')),
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
                         six.text_type)
        self.assertEqual(fields.PercentField.serialize(Decimal('42.010')),
                         '4201.0%')
        self.assertEqual(fields.PercentField.serialize(Decimal('0')),
                         '0.00%')
        self.assertEqual(fields.PercentField.serialize(None), '')
        self.assertEqual(fields.PercentField.serialize(Decimal('0.01')), '1%')
        with rows.locale_context(locale_name):
            self.assertEqual(
                type(fields.PercentField.serialize(deserialized)),
                six.text_type
            )
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
        serialized = '2015-05-27'
        deserialized = datetime.date(2015, 5, 27)
        self.assertEqual(fields.DateField.TYPE, (datetime.date, ))
        self.assertEqual(fields.DateField.serialize(None),
                         '')
        self.assertIs(type(fields.DateField.serialize(None)),
                      six.text_type)
        self.assertIn(type(fields.DateField.deserialize(serialized)),
                      fields.DateField.TYPE)
        self.assertEqual(fields.DateField.deserialize(serialized),
                         deserialized)
        self.assertEqual(fields.DateField.deserialize(deserialized),
                         deserialized)
        self.assertEqual(fields.DateField.deserialize(None), None)
        self.assertEqual(fields.DateField.deserialize(''), None)
        self.assertEqual(fields.DateField.serialize(deserialized),
                         serialized)
        self.assertIs(type(fields.DateField.serialize(deserialized)),
                      six.text_type)
        with self.assertRaises(ValueError):
            fields.DateField.deserialize(42)
        with self.assertRaises(ValueError):
            fields.DateField.deserialize(serialized + 'T00:00:00')
        with self.assertRaises(ValueError):
            fields.DateField.deserialize('Álvaro')
        with self.assertRaises(ValueError):
            fields.DateField.deserialize(serialized.encode('utf-8'))

    def test_DatetimeField(self):
        # TODO: test timezone-aware datetime.date
        serialized = '2015-05-27T01:02:03'
        self.assertEqual(fields.DatetimeField.TYPE, (datetime.datetime, ))
        deserialized = fields.DatetimeField.deserialize(serialized)
        self.assertIn(type(deserialized), fields.DatetimeField.TYPE)
        self.assertEqual(fields.DatetimeField.serialize(None), '')
        self.assertIs(type(fields.DatetimeField.serialize(None)),
                      six.text_type)

        value = datetime.datetime(2015, 5, 27, 1, 2, 3)
        self.assertEqual(fields.DatetimeField.deserialize(serialized), value)
        self.assertEqual(fields.DatetimeField.deserialize(deserialized),
                         deserialized)
        self.assertEqual(fields.DatetimeField.deserialize(None), None)
        self.assertEqual(fields.DatetimeField.serialize(value), serialized)
        self.assertIs(type(fields.DatetimeField.serialize(value)),
                      six.text_type)
        with self.assertRaises(ValueError):
            fields.DatetimeField.deserialize(42)
        with self.assertRaises(ValueError):
            fields.DatetimeField.deserialize('2015-01-01')
        with self.assertRaises(ValueError):
            fields.DatetimeField.deserialize('Álvaro')
        with self.assertRaises(ValueError):
            fields.DatetimeField.deserialize(serialized.encode('utf-8'))

    def test_EmailField(self):
        # TODO: accept spaces also
        serialized = 'test@domain.com'
        self.assertEqual(fields.EmailField.TYPE, (six.text_type, ))
        deserialized = fields.EmailField.deserialize(serialized)
        self.assertIn(type(deserialized), fields.EmailField.TYPE)
        self.assertEqual(fields.EmailField.serialize(None), '')
        self.assertIs(type(fields.EmailField.serialize(None)), six.text_type)

        self.assertEqual(fields.EmailField.serialize(serialized), serialized)
        self.assertEqual(fields.EmailField.deserialize(serialized), serialized)
        self.assertEqual(fields.EmailField.deserialize(None), None)
        self.assertEqual(fields.EmailField.deserialize(''), None)
        self.assertIs(type(fields.EmailField.serialize(serialized)),
                      six.text_type)

        with self.assertRaises(ValueError):
            fields.EmailField.deserialize(42)
        with self.assertRaises(ValueError):
            fields.EmailField.deserialize('2015-01-01')
        with self.assertRaises(ValueError):
            fields.EmailField.deserialize('Álvaro')
        with self.assertRaises(ValueError):
            fields.EmailField.deserialize('test@example.com'.encode('utf-8'))

    def test_TextField(self):
        self.assertEqual(fields.TextField.TYPE, (six.text_type, ))
        self.assertEqual(fields.TextField.serialize(None), '')
        self.assertIs(type(fields.TextField.serialize(None)), six.text_type)
        self.assertIn(type(fields.TextField.deserialize('test')),
                      fields.TextField.TYPE)

        self.assertEqual(fields.TextField.deserialize('Álvaro'),
                         'Álvaro')
        self.assertIs(fields.TextField.deserialize(None), None)
        self.assertIs(fields.TextField.deserialize(''), '')
        self.assertEqual(fields.TextField.serialize('Álvaro'),
                         'Álvaro')
        self.assertIs(type(fields.TextField.serialize('Álvaro')),
                      six.text_type)

        with self.assertRaises(ValueError) as exception_context:
            fields.TextField.deserialize('Álvaro'.encode('utf-8'))
        self.assertEqual(exception_context.exception.args[0],
                         'Binary is not supported')

    def test_JSONField(self):
        self.assertEqual(fields.JSONField.TYPE, (list, dict))
        self.assertEqual(type(fields.JSONField.deserialize('[]')), list)
        self.assertEqual(type(fields.JSONField.deserialize('{}')), dict)

        deserialized = {'a': 123, 'b': 3.14, 'c': [42, 24], }
        serialized = json.dumps(deserialized)
        self.assertEqual(fields.JSONField.deserialize(serialized),
                         deserialized)


class FieldUtilsTestCase(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        with open('tests/data/all-field-types.csv', 'rb') as fobj:
            data = fobj.read().decode('utf-8')
        lines = [line.split(',') for line in data.splitlines()]

        self.fields = lines[0]
        self.data = lines[1:]
        self.expected = {
                'bool_column': fields.BoolField,
                'integer_column': fields.IntegerField,
                'float_column': fields.FloatField,
                'decimal_column': fields.FloatField,
                'percent_column': fields.PercentField,
                'date_column': fields.DateField,
                'datetime_column': fields.DatetimeField,
                'unicode_column': fields.TextField,
        }

    def test_detect_types_no_sample(self):
        expected = {key: fields.BinaryField for key in self.expected.keys()}
        result = fields.detect_types(self.fields, [])
        self.assertDictEqual(dict(result), expected)

    def test_detect_types_binary(self):

        # first, try values as (`bytes`/`str`)
        expected = {key: fields.BinaryField for key in self.expected.keys()}
        values = [[value.encode('utf-8') for value in row]
                  for row in self.data]
        result = fields.detect_types(self.fields, values)
        self.assertDictEqual(dict(result), expected)

        # second, try base64-encoded values (as `str`/`unicode`)
        expected = {key: fields.TextField for key in self.expected.keys()}
        values = [[b64encode(value.encode('utf-8')).decode('ascii')
                   for value in row]
                  for row in self.data]
        result = fields.detect_types(self.fields, values)
        self.assertDictEqual(dict(result), expected)

    def test_detect_types(self):
        result = fields.detect_types(self.fields, self.data)
        self.assertDictEqual(dict(result), self.expected)

    def test_precedence(self):
        field_types = [
                ('bool', fields.BoolField),
                ('integer', fields.IntegerField),
                ('float', fields.FloatField),
                ('datetime', fields.DatetimeField),
                ('date', fields.DateField),
                ('float', fields.FloatField),
                ('percent', fields.PercentField),
                ('json', fields.JSONField),
                ('email', fields.EmailField),
                ('binary1', fields.BinaryField),
                ('binary2', fields.BinaryField),
                ('text', fields.TextField),
            ]
        data = [
                [
                    'false',
                    '42',
                    '3.14',
                    '2016-08-15T05:21:10',
                    '2016-08-15',
                    '2.71',
                    '76.38%',
                    '{"key": "value"}',
                    'test@example.com',
                    b'cHl0aG9uIHJ1bGVz',
                    b'python rules',
                    'Álvaro Justen'
                ]
            ]
        result = fields.detect_types([item[0] for item in field_types], data)
        self.assertDictEqual(dict(result), dict(field_types))


class FieldsFunctionsTestCase(unittest.TestCase):

    def test_is_null(self):
        self.assertTrue(fields.is_null(None))
        self.assertTrue(fields.is_null(''))
        self.assertTrue(fields.is_null(' \t '))
        self.assertTrue(fields.is_null('null'))
        self.assertTrue(fields.is_null('nil'))
        self.assertTrue(fields.is_null('none'))
        self.assertTrue(fields.is_null('-'))

        self.assertFalse(fields.is_null('Álvaro'))
        self.assertFalse(fields.is_null('Álvaro'.encode('utf-8')))

    def test_as_string(self):
        self.assertEqual(fields.as_string(None), 'None')
        self.assertEqual(fields.as_string(42), '42')
        self.assertEqual(fields.as_string(3.141592), '3.141592')
        self.assertEqual(fields.as_string('Álvaro'), 'Álvaro')

        with self.assertRaises(ValueError) as exception_context:
            fields.as_string('Álvaro'.encode('utf-8'))
        self.assertEqual(exception_context.exception.args[0],
                         'Binary is not supported')
