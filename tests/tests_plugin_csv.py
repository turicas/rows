# coding: utf-8

# Copyright 2014-2017 Álvaro Justen <https://github.com/turicas/rows/>
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

import csv
import tempfile
import textwrap
import unittest
from collections import OrderedDict
from io import BytesIO
from textwrap import dedent

import mock

import rows
import rows.plugins.plugin_csv
import tests.utils as utils


def make_csv_data(quote_char, field_delimiter, line_delimiter):
    data = [['field1', 'field2', 'field3'],
            ['value1', 'value2', 'value3']]
    lines = [['{}{}{}'.format(quote_char, value, quote_char)
              for value in line]
             for line in data]
    lines = line_delimiter.join([field_delimiter.join(line)
                                 for line in data])
    return data, lines


class PluginCsvTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = 'csv'
    file_extension = 'csv'
    filename = 'tests/data/all-field-types.csv'
    encoding = 'utf-8'
    assert_meta_encoding = True

    def test_imports(self):
        self.assertIs(rows.import_from_csv, rows.plugins.plugin_csv.import_from_csv)
        self.assertIs(rows.export_to_csv, rows.plugins.plugin_csv.export_to_csv)
        self.assertTrue(rows.import_from_csv.is_lazy)

    @mock.patch('rows.plugins.plugin_csv.create_table')
    def test_import_from_csv_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'some_key': 123, 'other': 456, }
        result = rows.import_from_csv(self.filename, encoding='utf-8',
                                      **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'csv',
                          'filename': self.filename,
                          'encoding': 'utf-8',}
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins.plugin_csv.create_table')
    def test_import_from_csv_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        rows.import_from_csv(self.filename)
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args)

        # import using fobj
        with open(self.filename, 'rb') as fobj:
            rows.import_from_csv(fobj)
            call_args = mocked_create_table.call_args_list[1]
            self.assert_create_table_data(call_args)

    @mock.patch('rows.plugins.plugin_csv.create_table')
    def test_import_from_csv_discover_dialect(self, mocked_create_table):
        data, lines = make_csv_data(quote_char="'",
                                    field_delimiter=";",
                                    line_delimiter="\r\n")
        fobj = BytesIO()
        fobj.write(lines.encode('utf-8'))
        fobj.seek(0)

        rows.import_from_csv(fobj)
        call_args = mocked_create_table.call_args_list[0]
        self.assertEqual(data, list(call_args[0][0]))

    def test_import_from_csv_discover_dialect_decode_error(self):

        # Create a 1024-bytes line (if encoded to ASCII, UTF-8 etc.)
        line = '"' + ('a' * 508) + '", "' + ('b' * 508) + '"\r\n'
        lines = 256 * line  # 256KiB

        # Now change the last byte (in the 256KiB sample) to have half of a
        # character representation (when encoded to UTF-8)
        data = lines[:-3] + '++Á"\r\n'
        data = data.encode('utf-8')

        # Should not raise `UnicodeDecodeError`
        table = rows.import_from_csv(BytesIO(data), encoding='utf-8',
                sample_size=262144)

        last_row = table[-1]
        last_column = 'b' * 508
        self.assertEqual(getattr(last_row, last_column), 'b' * 508 + '++Á')

    def test_import_from_csv_impossible_dialect(self):
        # Fix a bug from: https://github.com/turicas/rows/issues/214
        # The following CSV will make the `csv`'s sniff to return an impossible
        # dialect to be used (having doublequote = False and escapechar =
        # None). See more at:
        # https://docs.python.org/3/library/csv.html#csv.Dialect.doublequote

        encoding = 'utf-8'
        data = dedent('''
        field1,field2
        1,2
        3,4
        5,6
        '''.strip()).encode(encoding)

        dialect = rows.plugins.plugin_csv.discover_dialect(data, encoding)
        self.assertIs(dialect.doublequote, True)
        self.assertIs(dialect.escapechar, None)

    @mock.patch('rows.plugins.plugin_csv.create_table')
    def test_import_from_csv_force_dialect(self, mocked_create_table):
        data, lines = make_csv_data(quote_char="'",
                                    field_delimiter="\t",
                                    line_delimiter="\r\n")
        fobj = BytesIO()
        fobj.write(lines.encode('utf-8'))
        fobj.seek(0)

        rows.import_from_csv(fobj, dialect='excel-tab')
        call_args = mocked_create_table.call_args_list[0]
        self.assertEqual(data, list(call_args[0][0]))

    def test_detect_dialect_more_data(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        filename = '{}.{}'.format(temp.name, self.file_extension)
        self.files_to_delete.append(filename)

        # If the sniffer reads only the first line, it will think the delimiter
        # is ',' instead of ';'
        data = textwrap.dedent('''
            field1,samefield;field2,other
            row1value1;row1value2
            row2value1;row2value2
            ''').strip()
        with open(filename, 'wb') as fobj:
            fobj.write(data.encode('utf-8'))

        table = rows.import_from_csv(filename, encoding='utf-8')
        self.assertEqual(table.field_names, ['field1samefield', 'field2other'])
        self.assertEqual(table[0].field1samefield, 'row1value1')
        self.assertEqual(table[0].field2other, 'row1value2')
        self.assertEqual(table[1].field1samefield, 'row2value1')
        self.assertEqual(table[1].field2other, 'row2value2')

    def test_detect_weird_dialect(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        filename = '{}.{}'.format(temp.name, self.file_extension)
        self.files_to_delete.append(filename)

        # If the sniffer reads only the first line, it will think the delimiter
        # is ',' instead of ';'
        encoding = 'utf-8'
        data = BytesIO(textwrap.dedent('''
            field1|field2|field3|field4
            1|2|3|4
            5|6|7|8
            9|0|1|2
            ''').strip().encode(encoding))

        table = rows.import_from_csv(data, encoding=encoding, lazy=False)
        self.assertEqual(table.field_names,
                         ['field1', 'field2', 'field3', 'field4'])

        expected = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 0, 1, 2]]
        for expected_data, row in zip(expected, table):
            row = [row.field1, row.field2, row.field3, row.field4]
            self.assertEqual(expected_data, row)

    def test_detect_dialect_using_json(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        filename = '{}.{}'.format(temp.name, self.file_extension)
        encoding = 'utf-8'
        self.files_to_delete.append(filename)

        # Using JSON will force the sniffer to do not include ':', '}' in the
        # possible delimiters
        table = rows.Table(fields=OrderedDict([
            ('jsoncolumn1', rows.fields.JSONField),
            ('jsoncolumn2', rows.fields.JSONField),
            ]))
        table.append({
            'jsoncolumn1': '{"a": 42}',
            'jsoncolumn2': '{"b": 43}',
            })
        table.append({
            'jsoncolumn1': '{"c": 44}',
            'jsoncolumn2': '{"d": 45}',
            })
        rows.export_to_csv(table, filename, encoding=encoding)

        table = rows.import_from_csv(filename, encoding=encoding)

        self.assertEqual(table.field_names, ['jsoncolumn1', 'jsoncolumn2'])
        self.assertDictEqual(table[0].jsoncolumn1, {'a': 42})
        self.assertDictEqual(table[0].jsoncolumn2, {'b': 43})
        self.assertDictEqual(table[1].jsoncolumn1, {'c': 44})
        self.assertDictEqual(table[1].jsoncolumn2, {'d': 45})

    @mock.patch('rows.plugins.plugin_csv.serialize')
    def test_export_to_csv_uses_serialize(self, mocked_serialize):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        kwargs = {'test': 123, 'parameter': 3.14, }
        mocked_serialize.return_value = iter([utils.table.fields.keys()])

        rows.export_to_csv(utils.table, temp.name, encoding='utf-8', **kwargs)
        self.assertTrue(mocked_serialize.called)
        self.assertEqual(mocked_serialize.call_count, 1)

        call = mocked_serialize.call_args
        self.assertEqual(call[0], (utils.table, ))
        self.assertEqual(call[1], kwargs)

    def test_export_to_csv_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_csv(utils.table, temp.name)

        table = rows.import_from_csv(temp.name)
        self.assert_table_equal(table, utils.table)

        temp.file.seek(0)
        result = temp.file.read()
        export_in_memory = rows.export_to_csv(utils.table, None)
        self.assertEqual(result, export_in_memory)

    def test_export_to_csv_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_csv(utils.table, temp.file)

        table = rows.import_from_csv(temp.name)
        self.assert_table_equal(table, utils.table)

    def test_issue_168(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        filename = '{}.{}'.format(temp.name, self.file_extension)
        self.files_to_delete.append(filename)

        table = rows.Table(fields=OrderedDict([
            ('jsoncolumn', rows.fields.JSONField),
            ]))
        table.append({'jsoncolumn': '{"python": 42}'})
        rows.export_to_csv(table, filename)

        table2 = rows.import_from_csv(filename)
        self.assert_table_equal(table, table2)

    def test_quotes(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        filename = '{}.{}'.format(temp.name, self.file_extension)
        self.files_to_delete.append(filename)

        table = rows.Table(fields=OrderedDict([
                    ('field_1', rows.fields.TextField),
                    ('field_2', rows.fields.TextField),
                    ('field_3', rows.fields.TextField),
                    ('field_4', rows.fields.TextField), ]))
        table.append({
            'field_1': '"quotes"',
            'field_2': 'test "quotes"',
            'field_3': '"quotes" test',
            'field_4': 'test "quotes" test',
            })
        # we need this line row since `"quotes"` on `field_1` could be
        # `JSONField` or `TextField`
        table.append({
            'field_1': 'noquotes',
            'field_2': 'test "quotes"',
            'field_3': '"quotes" test',
            'field_4': 'test "quotes" test',
            })
        rows.export_to_csv(table, filename)

        table2 = rows.import_from_csv(filename)
        self.assert_table_equal(table, table2)

    def test_export_to_csv_accepts_dialect(self):
        result_1 = rows.export_to_csv(utils.table, dialect=csv.excel_tab)
        result_2 = rows.export_to_csv(utils.table, dialect=csv.excel)
        self.assertEqual(result_1.replace(b'\t', b','), result_2)

    def test_import_from_csv_is_lazy(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        filename = '{}.{}'.format(temp.name, self.file_extension)
        self.files_to_delete.append(filename)
        encoding = 'utf-8'
        number_of_rows = 1000

        fobj = open(filename, mode='wb+')
        fobj.write('field1,field2\r\n'.encode(encoding))
        for index in range(number_of_rows):
            row_data = ','.join([str(index), str(index ** 2)]) + '\r\n'
            fobj.write(row_data.encode(encoding))
        fobj.flush()
        total_bytes = fobj.tell()

        fobj.seek(0)
        table = rows.import_from_csv(fobj,
                                     encoding=encoding,
                                     dialect=csv.excel,
                                     samples=1,  # pre-read only the first row
                                     lazy=True)
        self.assertEqual(fobj.tell(), 20)  # 20 = len(1st line) + len(2nd line)

        data = list(table)
        self.assertEqual(len(data), number_of_rows)
        self.assertEqual(fobj.tell(), total_bytes)
