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

import itertools
import random
import unittest

from collections import OrderedDict

import mock

import rows.plugins.utils as plugins_utils
from rows import fields

import utils


def possible_field_names_errors(error_fields):
    error_fields = ['"{}"'.format(field_name) for field_name in error_fields]
    fields_permutations = itertools.permutations(error_fields,
                                                 len(error_fields))
    fields_permutations_str = [', '.join(field_names)
                               for field_names in fields_permutations]
    return ['Invalid field names {}'.format(field_names)
            for field_names in fields_permutations_str]


class PluginUtilsTestCase(unittest.TestCase):

    def test_create_table_skip_header(self):
        field_types = OrderedDict([('integer', fields.IntegerField),
                                   ('string', fields.TextField),])
        data = [['1', 'Álvaro'], ['2', 'turicas'], ['3', 'Justen']]
        table_1 = plugins_utils.create_table(data, fields=field_types,
                                             skip_header=True)
        table_2 = plugins_utils.create_table(data, fields=field_types,
                                             skip_header=False)

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

    def test_create_table_import_fields(self):
        header = ['field1', 'field2', 'field3']
        table_rows = [['1', 3.14, 'Álvaro'],
                      ['2', 2.71, 'turicas'],
                      ['3', 1.23, 'Justen']]
        table = plugins_utils.create_table([header] + table_rows,
                                           import_fields=None)
        self.assertEqual(table.fields.keys(), header)
        self.assertEqual(table[0].field1, 1)
        self.assertEqual(table[0].field2, 3.14)
        self.assertEqual(table[0].field3, 'Álvaro')

        import_fields = ['field3', 'field2']
        table = plugins_utils.create_table([header] + table_rows,
                                           import_fields=import_fields)
        self.assertEqual(table.fields.keys(), import_fields)
        self.assertEqual(table[0]._asdict(),
                         OrderedDict([('field3', 'Álvaro'), ('field2', 3.14)]))

    def test_create_table_import_fields_dont_exist(self):
        header = ['field1', 'field2', 'field3']
        table_rows = [['1', 3.14, 'Álvaro'],
                      ['2', 2.71, 'turicas'],
                      ['3', 1.23, 'Justen']]

        error_fields = ['doesnt_exist', 'ruby']
        import_fields = list(header)[:-1] + error_fields
        with self.assertRaises(ValueError) as exception_context:
            plugins_utils.create_table([header] + table_rows,
                                       import_fields=import_fields)

        self.assertIn(exception_context.exception.message,
                      possible_field_names_errors(error_fields))

    def test_create_table_repeated_field_names(self):
        header = ['first', 'first', 'first']
        table_rows = [['1', 3.14, 'Álvaro'],
                      ['2', 2.71, 'turicas'],
                      ['3', 1.23, 'Justen']]
        table = plugins_utils.create_table([header] + table_rows)
        self.assertEqual(table.fields.keys(), ['first', 'first_2', 'first_3'])
        self.assertEqual(table[0].first, 1)
        self.assertEqual(table[0].first_2, 3.14)
        self.assertEqual(table[0].first_3, 'Álvaro')

        header = ['field', '', 'field']
        table_rows = [['1', 3.14, 'Álvaro'],
                      ['2', 2.71, 'turicas'],
                      ['3', 1.23, 'Justen']]
        table = plugins_utils.create_table([header] + table_rows)
        self.assertEqual(table.fields.keys(), ['field', 'field_1', 'field_2'])
        self.assertEqual(table[0].field, 1)
        self.assertEqual(table[0].field_1, 3.14)
        self.assertEqual(table[0].field_2, 'Álvaro')

    def test_prepare_to_export_all_fields(self):
        result = plugins_utils.prepare_to_export(utils.table,
                                                 export_fields=None)

        self.assertEqual(utils.table.fields.keys(), result.next())

        for row in utils.table._rows:
            self.assertEqual(row, result.next())

        with self.assertRaises(StopIteration):
            result.next()

    def test_prepare_to_export_some_fields(self):
        field_names = utils.table.fields.keys()
        number_of_fields = random.randint(2, len(field_names) - 1)
        some_fields = [field_names[index] for index in range(number_of_fields)]
        random.shuffle(some_fields)
        result = plugins_utils.prepare_to_export(utils.table,
                                                 export_fields=some_fields)

        self.assertEqual(some_fields, result.next())

        for row in utils.table:
            expected_row = [getattr(row, field_name)
                            for field_name in some_fields]
            self.assertEqual(expected_row, result.next())

        with self.assertRaises(StopIteration):
            result.next()

    def test_prepare_to_export_some_fields_dont_exist(self):
        field_names = utils.table.fields.keys()
        error_fields = ['does_not_exist', 'java']
        export_fields = field_names + error_fields
        result = plugins_utils.prepare_to_export(utils.table,
                                                 export_fields=export_fields)
        with self.assertRaises(ValueError) as exception_context:
            result.next()

        self.assertIn(exception_context.exception.message,
                      possible_field_names_errors(error_fields))

    @mock.patch('rows.plugins.utils.prepare_to_export')
    def test_serialize_should_call_prepare_to_export(self,
            mocked_prepare_to_export):
        table = utils.table
        kwargs = {'export_fields': 123, 'other_parameter': 3.14, }
        result = plugins_utils.serialize(table, **kwargs)
        self.assertFalse(mocked_prepare_to_export.called)
        field_names = result.next()
        table_rows = list(result)
        self.assertTrue(mocked_prepare_to_export.called)
        self.assertEqual(mocked_prepare_to_export.call_count, 1)
        self.assertEqual(mock.call(table, **kwargs),
                         mocked_prepare_to_export.call_args)

    def test_serialize(self):
        result = plugins_utils.serialize(utils.table)
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
