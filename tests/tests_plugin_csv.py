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
import locale
import os
import tempfile
import textwrap
import unittest

from collections import OrderedDict

import rows


class TableTestCase(unittest.TestCase):

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

    # TODO: test export_to_csv
