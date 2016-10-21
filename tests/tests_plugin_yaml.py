# coding: utf-8

# Copyright 2014-2016 Álvaro Justen <https://github.com/turicas/rows/>
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
import tempfile
import yaml

from collections import Counter
from collections import OrderedDict
from collections import defaultdict

import six
import mock

import rows
import tests.utils as utils


class PluginYamlTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'yaml'
    file_extension = 'yaml'
    filename = 'tests/data/all-field-types.yaml'
    encoding = 'utf-8'
    assert_meta_encoding = True

    def test_imports(self):
        self.assertIs(rows.import_from_yaml,
                      rows.plugins.plugin_yaml.import_from_yaml)
        self.assertIs(rows.export_to_yaml,
                      rows.plugins.plugin_yaml.export_to_yaml)

    @mock.patch('rows.plugins.plugin_yaml.create_table')
    def test_import_from_yaml_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'some_key': 123, 'other': 456, }
        result = rows.import_from_yaml(self.filename, encoding=self.encoding,
                                       **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'yaml',
                          'filename': self.filename,
                          'encoding': self.encoding,}
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins.plugin_yaml.create_table')
    def test_import_from_yaml_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        table_1 = rows.import_from_yaml(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args, field_ordering=False)

        # import using fobj
        with open(self.filename) as fobj:
            table_2 = rows.import_from_yaml(fobj)
            call_args = mocked_create_table.call_args_list[1]
            self.assert_create_table_data(call_args, field_ordering=False)

    @mock.patch('rows.plugins.plugin_yaml.create_table')
    def test_import_from_yaml_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'some_key': 123, 'other': 456, }
        encoding = 'iso-8859-15'
        result = rows.import_from_yaml(self.filename, encoding=encoding,
                                       **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'yaml',
                          'filename': self.filename,
                          'encoding': encoding,}
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins.plugin_yaml.prepare_to_export')
    def test_export_to_yaml_uses_prepare_to_export(self,
            mocked_prepare_to_export):
        temp = tempfile.NamedTemporaryFile(delete=False, mode='wb')
        self.files_to_delete.append(temp.name)
        kwargs = {'test': 123, 'parameter': 3.14, }
        mocked_prepare_to_export.return_value = \
                iter([utils.table.fields.keys()])

        rows.export_to_yaml(utils.table, temp.name, **kwargs)
        self.assertTrue(mocked_prepare_to_export.called)
        self.assertEqual(mocked_prepare_to_export.call_count, 1)

        call = mocked_prepare_to_export.call_args
        self.assertEqual(call[0], (utils.table, ))
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins.plugin_yaml.export_data')
    def test_export_to_yaml_uses_export_data(self, mocked_export_data):
        temp = tempfile.NamedTemporaryFile(delete=False, mode='wb')
        self.files_to_delete.append(temp.name)
        kwargs = {'test': 123, 'parameter': 3.14, }
        mocked_export_data.return_value = 42

        result = rows.export_to_yaml(utils.table, temp.name, **kwargs)
        self.assertTrue(mocked_export_data.called)
        self.assertEqual(mocked_export_data.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_export_data.call_args
        self.assertEqual(call[0][0], temp.name)
        self.assertEqual(call[1], {'mode': 'wb'})

    def test_export_to_yaml_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False, mode='wb')
        self.files_to_delete.append(temp.name)
        rows.export_to_yaml(utils.table, temp.name)
        table = rows.import_from_yaml(temp.name)
        self.assert_table_equal(table, utils.table)

    def test_export_to_yaml_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False, mode='wb')
        self.files_to_delete.append(temp.name)
        rows.export_to_yaml(utils.table, temp.file)

        table = rows.import_from_yaml(temp.name)
        self.assert_table_equal(table, utils.table)

    def test_export_to_yaml_filename_save_data_in_correct_format(self):
        temp = tempfile.NamedTemporaryFile(delete=False, mode='wb')
        self.files_to_delete.append(temp.name)

        rows.export_to_yaml(utils.table, temp.name)

        with open(temp.name) as fobj:
            imported_yaml = yaml.load(fobj)

        COLUMN_TYPE = {
                'float_column': float,
                'decimal_column': float,
                'bool_column': bool,
                'integer_column': int,
                'date_column': six.text_type,
                'datetime_column': six.text_type,
                'percent_column': six.text_type,
                'unicode_column': six.text_type,
        }
        field_types = defaultdict(list)
        for row in imported_yaml:
            for field_name, value in row.items():
                field_types[field_name].append(type(value))
        # We test if the JSON was created serializing all the fields correctly
        # (some as native JSON values, like int and float) and others needed to
        # be serialized, like date, datetime etc.
        for field_name, value_types in field_types.items():
            if field_name != 'unicode_column':
                self.assertEqual(Counter(value_types),
                                 Counter({type(None): 1,
                                          COLUMN_TYPE[field_name]: 6}))
            else:
                self.assertEqual(Counter(value_types),
                                 Counter({COLUMN_TYPE[field_name]: 7}))
