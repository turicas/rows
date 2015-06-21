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

from decimal import Decimal

import rows

from rows import fields


class FieldsTestCase(unittest.TestCase):

    def byte_asserts(self, field_class):
        # Field and ByteField are actually the same thing
        self.assertEqual(field_class.TYPE, str)
        self.assertIs(type(field_class.deserialize('test')),
                      field_class.TYPE)
        self.assertIs(field_class.deserialize('Álvaro'), 'Álvaro')
        self.assertIs(field_class.serialize('Álvaro'), 'Álvaro')

    def test_Field(self):
        self.byte_asserts(fields.Field)

    def test_ByteField(self):
        self.byte_asserts(fields.ByteField)

    def test_BoolField(self):
        self.assertEqual(fields.BoolField.TYPE, bool)
        self.assertIs(type(fields.BoolField.deserialize('true')),
                      fields.BoolField.TYPE)

        self.assertIs(fields.BoolField.deserialize('0'), False)
        self.assertIs(fields.BoolField.deserialize('false'), False)
        self.assertIs(fields.BoolField.deserialize('no'), False)
        self.assertEqual(fields.BoolField.serialize(False), 'false')

        self.assertIs(fields.BoolField.deserialize('1'), True)
        self.assertIs(fields.BoolField.deserialize('true'), True)
        self.assertIs(fields.BoolField.deserialize('yes'), True)
        self.assertEqual(fields.BoolField.serialize(True), 'true')

    def test_IntegerField(self):
        self.assertEqual(fields.IntegerField.TYPE, int)
        self.assertIs(type(fields.IntegerField.deserialize('42')),
                      fields.IntegerField.TYPE)
        self.assertEqual(fields.IntegerField.deserialize('42'), 42)
        self.assertEqual(fields.IntegerField.serialize(42), '42')

        with rows.locale_context('pt_BR.UTF-8'):
            self.assertEqual(fields.IntegerField.serialize(42000), '42000')
            self.assertEqual(fields.IntegerField.serialize(42000,
                                                           grouping=True),
                             '42.000')
            self.assertEqual(fields.IntegerField.deserialize('42.000'), 42000)

    def test_FloatField(self):
        self.assertEqual(fields.FloatField.TYPE, float)
        self.assertIs(type(fields.FloatField.deserialize('42.0')),
                      fields.FloatField.TYPE)
        self.assertEqual(fields.FloatField.deserialize('42.0'), 42.0)
        self.assertEqual(fields.FloatField.serialize(42.0), '42.000000')

        with rows.locale_context('pt_BR.UTF-8'):
            self.assertEqual(fields.FloatField.serialize(42000.0),
                             '42000,000000')
            self.assertEqual(fields.FloatField.serialize(42000, grouping=True),
                             '42.000,000000')
            self.assertEqual(fields.FloatField.deserialize('42.000,00'),
                             42000.0)

    def test_DateField(self):
        # TODO: test timezone-aware datetime.date
        # TODO: should use a locale-aware converter?
        self.assertEqual(fields.DateField.TYPE, datetime.date)
        self.assertIs(type(fields.DateField.deserialize('2015-05-27')),
                      fields.DateField.TYPE)
        self.assertEqual(fields.DateField.deserialize('2015-05-27'),
                         datetime.date(2015, 5, 27))
        self.assertEqual(fields.DateField.serialize(datetime.date(2015, 5, 27)),
                         '2015-05-27')

    def test_UnicodeField(self):
        self.assertEqual(fields.UnicodeField.TYPE, unicode)
        self.assertIs(type(fields.UnicodeField.deserialize('test')),
                      fields.UnicodeField.TYPE)
        self.assertEqual(fields.UnicodeField.deserialize('Álvaro',
                                                         encoding='utf-8'),
                         u'Álvaro')
        self.assertEqual(fields.UnicodeField.serialize(u'Álvaro',
                                                       encoding='utf-8'),
                         'Álvaro')

    def test_DatetimeField(self):
        # TODO: test timezone-aware datetime.date
        # TODO: should use a locale-aware converter?
        self.assertEqual(fields.DatetimeField.TYPE, datetime.datetime)
        self.assertIs(type(fields.DatetimeField.deserialize('2015-05-27T01:02:03')),
                      fields.DatetimeField.TYPE)

        value = datetime.datetime(2015, 5, 27, 1, 2, 3)
        serialized = '2015-05-27T01:02:03'
        self.assertEqual(fields.DatetimeField.deserialize(serialized), value)
        self.assertEqual(fields.DatetimeField.serialize(value), serialized)

    def test_DecimalField(self):
        self.assertEqual(fields.DecimalField.TYPE, Decimal)
        self.assertIs(type(fields.DecimalField.deserialize('42.0')),
                      fields.DecimalField.TYPE)
        self.assertEqual(fields.DecimalField.deserialize('42.0'), Decimal('42.0'))
        self.assertEqual(fields.DecimalField.serialize(Decimal('42.010')), '42.010')
        self.assertEqual(fields.DecimalField.deserialize('21.21657469231'),
                         Decimal('21.21657469231'))

        with rows.locale_context('pt_BR.UTF-8'):
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
        self.assertEqual(fields.PercentField.TYPE, Decimal)
        self.assertIs(type(fields.PercentField.deserialize('42.0%')),
                      fields.PercentField.TYPE)
        self.assertEqual(fields.PercentField.deserialize('42.0%'),
                         Decimal('0.420'))
        self.assertEqual(fields.PercentField.serialize(Decimal('0.42010')),
                         '0.42010')
        self.assertEqual(fields.PercentField.serialize(Decimal('42.010')),
                         '42.010')

        with rows.locale_context('pt_BR.UTF-8'):
            self.assertEqual(fields.PercentField.serialize(Decimal('42.0')),
                             '42,0')
            self.assertEqual(fields.PercentField.serialize(Decimal('42000.0')),
                             '42000,0')
            self.assertEqual(fields.PercentField.deserialize('42.000,00%'),
                             Decimal('420.0000'))
            self.assertEqual(fields.PercentField.serialize(Decimal('42000.00'),
                                                           grouping=True),
                             '42.000,00')
