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
import os
import tempfile
import textwrap
import unittest

from collections import OrderedDict
from decimal import Decimal

import rows


class TableTestCase(unittest.TestCase):

    def test_table(self):
        table = rows.Table(fields={'name': rows.fields.UnicodeField,
                                   'birthdate': rows.fields.DateField, })
        table.append({'name': u'Álvaro Justen',
                      'birthdate': datetime.date(1987, 4, 29)})
        table.append({'name': u'Somebody',
                      'birthdate': datetime.date(1990, 2, 1)})
        table.append({'name': u'Douglas Adams',
                      'birthdate': '1952-03-11'})

        table_rows = [row for row in table]
        self.assertEqual(len(table_rows), 3)
        self.assertEqual(table_rows[0].name, u'Álvaro Justen')
        self.assertEqual(table_rows[0].birthdate, datetime.date(1987, 4, 29))
        self.assertEqual(table_rows[1].name, u'Somebody')
        self.assertEqual(table_rows[1].birthdate, datetime.date(1990, 2, 1))
        self.assertEqual(table_rows[2].name, u'Douglas Adams')
        self.assertEqual(table_rows[2].birthdate, datetime.date(1952, 3, 11))

        # TODO: may mock these validations and test only on *Field tests
        with self.assertRaises(ValueError) as context_manager:
            table.append({'name': 'Álvaro Justen', 'birthdate': '1987-04-29'})
        self.assertEqual(type(context_manager.exception), UnicodeDecodeError)

        with self.assertRaises(ValueError) as context_manager:
            table.append({'name': u'Álvaro Justen', 'birthdate': 'WRONG'})
        self.assertEqual(type(context_manager.exception), ValueError)
        self.assertIn('does not match format',
                      context_manager.exception.message)

    def setUp(self):
        self.files_to_delete = []

    def tearDown(self):
        for filename in self.files_to_delete:
            os.unlink(filename)

    def test_import_from_csv(self):
        fobj = tempfile.NamedTemporaryFile(delete=False)
        contents = textwrap.dedent(u'''
        name,birthdate
        Álvaro Justen,1987-04-29
        Somebody,1990-02-01
        Douglas Adams,1952-03-11
        ''').strip().encode('utf-8')
        fobj.write(contents)
        fobj.close()
        self.files_to_delete.append(fobj.name)

        # TODO: should support file object also?
        table = rows.import_from_csv(fobj.name, encoding='utf-8')
        expected_fields = {'name': rows.fields.UnicodeField,
                           'birthdate': rows.fields.DateField, }
        self.assertDictEqual(OrderedDict(expected_fields), table.fields)

        table_rows = [row for row in table]
        self.assertEqual(3, len(table))
        self.assertEqual(3, len(table_rows))

        self.assertEqual(table_rows[0].name, u'Álvaro Justen')
        self.assertEqual(table_rows[0].birthdate,
                         datetime.date(1987, 4, 29))
        self.assertEqual(table_rows[1].name, u'Somebody')
        self.assertEqual(table_rows[1].birthdate,
                         datetime.date(1990, 2, 1))
        self.assertEqual(table_rows[2].name, u'Douglas Adams')
        self.assertEqual(table_rows[2].birthdate,
                         datetime.date(1952, 3, 11))

    def test_locale_context(self):
        import locale

        with rows.locale_context('pt_BR.UTF-8'):
            inside_context = locale.getlocale(locale.LC_ALL)
        self.assertEqual(('pt_BR', 'UTF-8'), inside_context)

        with rows.locale_context('en_US.UTF-8'):
            inside_context = locale.getlocale(locale.LC_ALL)
        self.assertEqual(('en_US', 'UTF-8'), inside_context)


class FieldsTestCase(unittest.TestCase):

    def test_IntegerField(self):
        from rows.fields import IntegerField

        self.assertEqual(IntegerField.TYPE, int)
        self.assertIs(type(IntegerField.deserialize('42')),
                      IntegerField.TYPE)
        self.assertEqual(IntegerField.deserialize('42'), 42)
        self.assertEqual(IntegerField.serialize(42), '42')

        with rows.locale_context('pt_BR.UTF-8'):
            self.assertEqual(IntegerField.serialize(42000), '42000')
            self.assertEqual(IntegerField.serialize(42000, grouping=True),
                             '42.000')
            self.assertEqual(IntegerField.deserialize('42.000'), 42000)

    def test_FloatField(self):
        from rows.fields import FloatField

        self.assertEqual(FloatField.TYPE, float)
        self.assertIs(type(FloatField.deserialize('42.0')),
                      FloatField.TYPE)
        self.assertEqual(FloatField.deserialize('42.0'), 42.0)
        self.assertEqual(FloatField.serialize(42.0), '42.000000')

        with rows.locale_context('pt_BR.UTF-8'):
            self.assertEqual(FloatField.serialize(42000.0),
                             '42000,000000')
            self.assertEqual(FloatField.serialize(42000, grouping=True),
                             '42.000,000000')
            self.assertEqual(FloatField.deserialize('42.000,00'), 42000.0)

    def test_DateField(self):
        from rows.fields import DateField

        # TODO: test timezone-aware datetime.date
        # TODO: should use a locale-aware converter?
        self.assertEqual(DateField.TYPE, datetime.date)
        self.assertIs(type(DateField.deserialize('2015-05-27')),
                      DateField.TYPE)
        self.assertEqual(DateField.deserialize('2015-05-27'),
                         datetime.date(2015, 5, 27))
        self.assertEqual(DateField.serialize(datetime.date(2015, 5, 27)),
                         '2015-05-27')

    def test_UnicodeField(self):
        from rows.fields import UnicodeField

        self.assertEqual(UnicodeField.TYPE, unicode)
        self.assertIs(type(UnicodeField.deserialize('test')),
                      UnicodeField.TYPE)
        self.assertEqual(UnicodeField.deserialize('Álvaro', encoding='utf-8'),
                         u'Álvaro')
        self.assertEqual(UnicodeField.serialize(u'Álvaro', encoding='utf-8'),
                         'Álvaro')

    def test_StringField(self):
        from rows.fields import StringField

        self.assertEqual(StringField.TYPE, str)
        self.assertIs(type(StringField.deserialize('test')),
                      StringField.TYPE)
        self.assertIs(StringField.deserialize('Álvaro'), 'Álvaro')
        self.assertIs(StringField.serialize('Álvaro'), 'Álvaro')

    def test_BoolField(self):
        from rows.fields import BoolField

        self.assertEqual(BoolField.TYPE, bool)
        self.assertIs(type(BoolField.deserialize('true')),
                      BoolField.TYPE)

        self.assertIs(BoolField.deserialize('0'), False)
        self.assertIs(BoolField.deserialize('false'), False)
        self.assertIs(BoolField.deserialize('no'), False)
        self.assertEqual(BoolField.serialize(False), 'false')

        self.assertIs(BoolField.deserialize('1'), True)
        self.assertIs(BoolField.deserialize('true'), True)
        self.assertIs(BoolField.deserialize('yes'), True)
        self.assertEqual(BoolField.serialize(True), 'true')

    def test_DatetimeField(self):
        from rows.fields import DatetimeField

        # TODO: test timezone-aware datetime.date
        # TODO: should use a locale-aware converter?
        self.assertEqual(DatetimeField.TYPE, datetime.datetime)
        self.assertIs(type(DatetimeField.deserialize('2015-05-27T01:02:03')),
                      DatetimeField.TYPE)

        value = datetime.datetime(2015, 5, 27, 1, 2, 3)
        serialized = '2015-05-27T01:02:03'
        self.assertEqual(DatetimeField.deserialize(serialized), value)
        self.assertEqual(DatetimeField.serialize(value), serialized)

    def test_DecimalField(self):
        from rows.fields import DecimalField

        self.assertEqual(DecimalField.TYPE, Decimal)
        self.assertIs(type(DecimalField.deserialize('42.0')),
                      DecimalField.TYPE)
        self.assertEqual(DecimalField.deserialize('42.0'), Decimal('42.0'))
        self.assertEqual(DecimalField.serialize(Decimal('42.010')), '42.010')

        with rows.locale_context('pt_BR.UTF-8'):
            self.assertEqual(DecimalField.serialize(Decimal('4200')),
                             '4200')
            self.assertEqual(DecimalField.serialize(Decimal('42.0')),
                             '42,0')
            self.assertEqual(DecimalField.serialize(Decimal('42000.0')),
                             '42000,0')
            self.assertEqual(DecimalField.deserialize('42.000,00'),
                             Decimal('42000.00'))
            self.assertEqual(DecimalField.serialize(Decimal('42000.0'),
                                                    grouping=True),
                             '42.000,0')

    def test_PercentField(self):
        from rows.fields import PercentField

        self.assertEqual(PercentField.TYPE, Decimal)
        self.assertIs(type(PercentField.deserialize('42.0%')),
                      PercentField.TYPE)
        self.assertEqual(PercentField.deserialize('42.0%'), Decimal('0.420'))
        self.assertEqual(PercentField.serialize(Decimal('0.42010')), '42.010%')
        self.assertEqual(PercentField.serialize(Decimal('42.010')), '4201.0%')

        with rows.locale_context('pt_BR.UTF-8'):
            self.assertEqual(PercentField.serialize(Decimal('42.0')),
                             '4200%')
            self.assertEqual(PercentField.serialize(Decimal('42000.0')),
                             '4200000%')
            self.assertEqual(PercentField.deserialize('42.000,00%'),
                             Decimal('420.0000'))
            self.assertEqual(PercentField.serialize(Decimal('42000.00'),
                                                    grouping=True),
                             '4.200.000%')
