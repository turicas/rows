# coding: utf-8

# Copyright 2014-2017 Álvaro Justen <https://github.com/turicas/rows/>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import io
import itertools
import random
import tempfile
import types
import unittest
from collections import OrderedDict

import mock
import six

import rows
import rows.plugins.utils as plugins_utils
import tests.utils as utils
from rows import fields


get_filename_and_fobj = plugins_utils.get_filename_and_fobj

class GenericUtilsTestCase(unittest.TestCase):

    def test_slug(self):
        self.assertEqual(plugins_utils.slug(None), '')
        self.assertEqual(plugins_utils.slug('Álvaro Justen'), 'alvaro_justen')
        self.assertEqual(plugins_utils.slug("Moe's Bar"), 'moes_bar')
        self.assertEqual(plugins_utils.slug("-----te-----st------"), 'te_st')
        # As in <https://github.com/turicas/rows/issues/179>
        self.assertEqual(
                plugins_utils.slug('Query Occurrence"( % ),"First Seen'),
                'query_occurrence_first_seen')
        self.assertEqual(plugins_utils.slug(' ÁLVARO  justen% '),
                         'alvaro_justen')
        self.assertEqual(plugins_utils.slug(42), '42')

    def test_ipartition(self):
        iterable = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = plugins_utils.ipartition(iterable, 3)
        self.assertEqual(type(result), types.GeneratorType)
        self.assertEqual(list(result), [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]])

        result = plugins_utils.ipartition(iterable, 2)
        self.assertEqual(type(result), types.GeneratorType)
        self.assertEqual(list(result), [[1, 2], [3, 4], [5, 6], [7, 8],
                                        [9, 10]])


def possible_field_names_errors(error_fields):
    error_fields = ['"{}"'.format(field_name) for field_name in error_fields]
    fields_permutations = itertools.permutations(error_fields,
                                                 len(error_fields))
    fields_permutations_str = [', '.join(field_names)
                               for field_names in fields_permutations]
    return ['Invalid field names: {}'.format(field_names)
            for field_names in fields_permutations_str]


class PluginUtilsTestCase(utils.RowsTestMixIn, unittest.TestCase):

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
        self.assertEqual(list(table.fields.keys()), header)
        self.assertEqual(table[0].field1, 1)
        self.assertEqual(table[0].field2, 3.14)
        self.assertEqual(table[0].field3, 'Álvaro')

        import_fields = ['field3', 'field2']
        table = plugins_utils.create_table([header] + table_rows,
                                           import_fields=import_fields)
        self.assertEqual(list(table.fields.keys()), import_fields)
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

        self.assertIn(exception_context.exception.args[0],
                      possible_field_names_errors(error_fields))

    def test_create_table_repeated_field_names(self):
        header = ['first', 'first', 'first']
        table_rows = [['1', 3.14, 'Álvaro'],
                      ['2', 2.71, 'turicas'],
                      ['3', 1.23, 'Justen']]
        table = plugins_utils.create_table([header] + table_rows)
        self.assertEqual(list(table.fields.keys()),
                         ['first', 'first_2', 'first_3'])
        self.assertEqual(table[0].first, 1)
        self.assertEqual(table[0].first_2, 3.14)
        self.assertEqual(table[0].first_3, 'Álvaro')

        header = ['field', '', 'field']
        table_rows = [['1', 3.14, 'Álvaro'],
                      ['2', 2.71, 'turicas'],
                      ['3', 1.23, 'Justen']]
        table = plugins_utils.create_table([header] + table_rows)
        self.assertEqual(list(table.fields.keys()),
                         ['field', 'field_1', 'field_2'])
        self.assertEqual(table[0].field, 1)
        self.assertEqual(table[0].field_1, 3.14)
        self.assertEqual(table[0].field_2, 'Álvaro')

    def test_create_table_empty_data(self):
        header = ['first', 'first', 'first']
        table_rows = []
        table = plugins_utils.create_table([header] + table_rows)
        self.assertEqual(list(table.fields.keys()),
                         ['first', 'first_2', 'first_3'])
        self.assertEqual(len(table), 0)

    def test_create_table_force_types(self):
        header = ['field1', 'field2', 'field3']
        table_rows = [['1', '3.14', 'Álvaro'],
                      ['2', '2.71', 'turicas'],
                      ['3', '1.23', 'Justen']]
        force_types = {'field2': rows.fields.DecimalField}

        table = plugins_utils.create_table([header] + table_rows,
                                           force_types=force_types)
        for field_name, field_type in force_types.items():
            self.assertEqual(table.fields[field_name], field_type)

    def test_prepare_to_export_all_fields(self):
        result = plugins_utils.prepare_to_export(utils.table,
                                                 export_fields=None)

        self.assertEqual(list(utils.table.fields.keys()), next(result))

        for row in utils.table._rows:
            self.assertEqual(row, next(result))

        with self.assertRaises(StopIteration):
            next(result)

    def test_prepare_to_export_some_fields(self):
        field_names = list(utils.table.fields.keys())
        number_of_fields = random.randint(2, len(field_names) - 1)
        some_fields = [field_names[index] for index in range(number_of_fields)]
        random.shuffle(some_fields)
        result = plugins_utils.prepare_to_export(utils.table,
                                                 export_fields=some_fields)

        self.assertEqual(some_fields, next(result))

        for row in utils.table:
            expected_row = [getattr(row, field_name)
                            for field_name in some_fields]
            self.assertEqual(expected_row, next(result))

        with self.assertRaises(StopIteration):
            next(result)

    def test_prepare_to_export_some_fields_dont_exist(self):
        field_names = list(utils.table.fields.keys())
        error_fields = ['does_not_exist', 'java']
        export_fields = field_names + error_fields
        result = plugins_utils.prepare_to_export(utils.table,
                                                 export_fields=export_fields)
        with self.assertRaises(ValueError) as exception_context:
            next(result)

        self.assertIn(exception_context.exception.args[0],
                      possible_field_names_errors(error_fields))

    def test_prepare_to_export_with_FlexibleTable(self):
        flexible = rows.FlexibleTable()
        for row in utils.table:
            flexible.append(row._asdict())

        field_names = list(flexible.fields.keys())
        prepared = plugins_utils.prepare_to_export(flexible)
        self.assertEqual(next(prepared), field_names)

        for row, expected_row in zip(prepared, flexible._rows):
            values = [expected_row[field_name] for field_name in field_names]
            self.assertEqual(values, row)

    def test_prepare_to_export_with_FlexibleTable_and_export_fields(self):
        flexible = rows.FlexibleTable()
        for row in utils.table:
            # convertion to text_type is needed on Python 2 since namedtuples'
            # keys are bytes, not unicode
            flexible.append({six.text_type(key): value
                             for key, value in row._asdict().items()})

        field_names = list(flexible.fields.keys())
        export_fields = field_names[:len(field_names) // 2]
        print([(x, type(x)) for x in export_fields])
        prepared = plugins_utils.prepare_to_export(flexible,
                                                   export_fields=export_fields)
        self.assertEqual(next(prepared), export_fields)

        for row, expected_row in zip(prepared, flexible._rows):
            values = [expected_row[field_name] for field_name in export_fields]
            self.assertEqual(values, row)

    def test_prepare_to_export_wrong_obj_type(self):
        '''`prepare_to_export` raises exception if obj isn't `*Table`'''

        expected_message = 'Table type not recognized'

        with self.assertRaises(ValueError) as exception_context:
            next(plugins_utils.prepare_to_export(1))
        self.assertEqual(exception_context.exception.args[0], expected_message)

        with self.assertRaises(ValueError) as exception_context:
            next(plugins_utils.prepare_to_export(42.0))
        self.assertEqual(exception_context.exception.args[0], expected_message)

        with self.assertRaises(ValueError) as exception_context:
            next(plugins_utils.prepare_to_export([list('abc'), [1, 2, 3]]))
        self.assertEqual(exception_context.exception.args[0], expected_message)

    @mock.patch('rows.plugins.utils.prepare_to_export',
                return_value=iter([[], [], []]))
    def test_serialize_should_call_prepare_to_export(self,
            mocked_prepare_to_export):
        table = utils.table
        kwargs = {'export_fields': 123, 'other_parameter': 3.14, }
        result = plugins_utils.serialize(table, **kwargs)
        self.assertFalse(mocked_prepare_to_export.called)
        field_names, table_rows = next(result), list(result)
        self.assertTrue(mocked_prepare_to_export.called)
        self.assertEqual(mocked_prepare_to_export.call_count, 1)
        self.assertEqual(mock.call(table, **kwargs),
                         mocked_prepare_to_export.call_args)

    def test_serialize(self):
        result = plugins_utils.serialize(utils.table)
        field_types = list(utils.table.fields.values())
        self.assertEqual(next(result), list(utils.table.fields.keys()))

        for row, expected_row in zip(result, utils.table._rows):
            values = [field_type.serialize(value)
                      for field_type, value in zip(field_types, expected_row)]
            self.assertEqual(values, row)

    def test_make_header_should_add_underscore_if_starts_with_number(self):
        result = plugins_utils.make_header(['123', '456', '123'])
        expected_result = ['field_123', 'field_456', 'field_123_2']
        self.assertEqual(result, expected_result)

    def test_make_header_should_not_ignore_permit_not(self):
        result = plugins_utils.make_header(['abc', '^qwe', 'rty'],
                                           permit_not=True)
        expected_result = ['abc', '^qwe', 'rty']
        self.assertEqual(result, expected_result)

    def test_make_unique_name(self):
        name = 'test'
        existing_names = []
        name_format = '{index}_{name}'

        result = plugins_utils.make_unique_name(name, existing_names,
                                                name_format)
        self.assertEqual(result, name)

        existing_names = ['test']
        result = plugins_utils.make_unique_name(name, existing_names,
                                                name_format)
        self.assertEqual(result, '2_test')

        existing_names = ['test', '2_test', '3_test', '5_test']
        result = plugins_utils.make_unique_name(name, existing_names,
                                                name_format)
        self.assertEqual(result, '4_test')

        existing_names = ['test', '2_test', '3_test', '5_test']
        result = plugins_utils.make_unique_name(name, existing_names,
                                                name_format,
                                                start=1)
        self.assertEqual(result, '1_test')

    def test_export_data(self):
        data = 'python rules'.encode('utf-8')
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)

        filename_or_fobj = temp.file
        result = plugins_utils.export_data(filename_or_fobj, data)
        temp.file.seek(0)
        output = temp.file.read()
        self.assertIs(result, temp.file)
        self.assertEqual(output, data)

        filename_or_fobj = None
        result = plugins_utils.export_data(filename_or_fobj, data)
        self.assertIs(result, data)


class FilenameFObjTestCase(unittest.TestCase):
    # TODO: test other features of this function (example: BytesIO should
    #       return filename = None)

    def setUp(self):
        self.filename = 'tests/data/csv_with_null_bytes.csv'
        self.encoding = 'latin1'
        self.data = io.open(self.filename, mode='rb').read()
        self.decoded_data = self.data.decode(self.encoding)

    def test_get_filename_and_fobj_passing_filename(self):
        mode = 'rb'
        _, f = get_filename_and_fobj(self.filename, mode=mode)
        self.assertTrue(hasattr(f, 'readable') and f.readable())
        self.assertEqual(f.mode, mode)
        self.assertEqual(f.read(), self.data)

    def test_get_filename_and_fobj_passing_text_fobj(self):
        if six.PY3:
            mode = 'r'
            fobj = open(self.filename, encoding=self.encoding)
            _, f = get_filename_and_fobj(fobj, mode=mode, encoding=self.encoding)
            self.assertTrue(hasattr(f, 'readable') and f.readable())
            self.assertEqual(f.mode, mode)
            self.assertEqual(f.read(), self.decoded_data)

        mode = 'r'
        fobj = io.open(self.filename, encoding=self.encoding)
        _, f = get_filename_and_fobj(fobj, mode=mode, encoding=self.encoding)
        self.assertTrue(hasattr(f, 'readable') and f.readable())
        self.assertEqual(f.mode, mode)
        self.assertEqual(f.read(), self.decoded_data)

    def test_get_filename_and_fobj_passing_bytes_fobj(self):
        mode = 'rb'
        fobj = open(self.filename, mode=mode)
        _, f = get_filename_and_fobj(fobj, mode=mode)
        self.assertTrue(hasattr(f, 'readable') and f.readable())
        self.assertEqual(f.mode, mode)
        self.assertEqual(f.read(), self.data)

        fobj = io.open(self.filename, mode=mode)
        _, f = get_filename_and_fobj(fobj, mode=mode)
        self.assertTrue(hasattr(f, 'readable') and f.readable())
        self.assertEqual(f.mode, mode)
        self.assertEqual(f.read(), self.data)

    def test_get_filename_and_fobj_passing_BytesIO(self):
        mode = 'rb'
        fobj = io.BytesIO(self.data)
        _, f = get_filename_and_fobj(fobj, mode=mode)
        self.assertTrue(hasattr(f, 'readable') and f.readable())
        self.assertEqual(f.mode, mode)
        self.assertEqual(f.read(), self.data)

    # TODO: test make_header
    # TODO: test all features of create_table
    # TODO: test if error is raised if len(row) != len(fields)
