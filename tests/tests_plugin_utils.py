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

from collections import OrderedDict

from rows import fields
from rows.plugins.utils import create_table, serialize

import utils


class PluginUtilsTestCase(unittest.TestCase):

    def test_create_table_skip_header(self):
        field_types = OrderedDict([('integer', fields.IntegerField),
                                   ('string', fields.UnicodeField),])
        data = [['1', 'Álvaro'], ['2', 'turicas'], ['3', 'Justen']]
        table_1 = create_table(data, fields=field_types, skip_header=True)
        table_2 = create_table(data, fields=field_types, skip_header=False)

        self.assertEqual(field_types, table_1.fields)
        self.assertEqual(table_1.fields, table_2.fields)
        self.assertEqual(len(table_1), 2)
        self.assertEqual(len(table_2), 3)

        first_row = {'integer': 1, 'string': 'Álvaro'}
        second_row = {'integer': 2, 'string': 'turicas'}
        third_row = {'integer': 3, 'string': 'Justen'}
        self.assertEqual(dict(table_1[0]._asdict()), second_row)
        self.assertEqual(dict(table_2[0]._asdict()), first_row)
        self.assertEqual(dict(table_1[1]._asdict()), third_row)
        self.assertEqual(dict(table_2[1]._asdict()), second_row)
        self.assertEqual(dict(table_2[2]._asdict()), third_row)

    def test_serialize(self):
        result = serialize(utils.table)
        field_types = utils.table.fields.values()
        self.assertEqual(result.next(), utils.table.fields.keys())

        for row, expected_row in zip(result, utils.table._rows):
            values = [field_type.serialize(value)
                      for field_type, value in zip(field_types, expected_row)]
            self.assertEqual(values, row)

    # TODO: test make_header
    # TODO: test all features of create_table
    # TODO: test if error is raised if len(row) != len(fields)
    # TODO: test get_fobj_and_filename (BytesIO should return filename = None)
