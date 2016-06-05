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

import tempfile
import unittest

from collections import OrderedDict

import mock

import rows
import rows.plugins.html
from . import utils


# TODO: test unescape
# TODO: test colspan
# TODO: test rowspan
# TODO: test more nested tables
#       URL = 'https://finance.yahoo.com/q;_ylt=At7WXTIEGzyrIHemoSMI7I.iuYdG;_ylu=X3oDMTBxdGVyNzJxBHNlYwNVSCAzIERlc2t0b3AgU2VhcmNoIDEx;_ylg=X3oDMTByaDM4cG9kBGxhbmcDZW4tVVMEcHQDMgR0ZXN0AzUxMjAxMw--;_ylv=3?s=GOOG&uhb=uhb2&type=2button&fr=uh3_finance_web_gs'
#       URL_2 = 'http://www.rio.rj.gov.br/dlstatic/10112/2147539/DLFE-237833.htm/paginanova2.0.0.0._B.htm'

def cleanup_lines(lines):
    return [line.strip() for line in lines.strip().split('\n') if line.strip()]


class PluginHtmlTestCase(utils.RowsTestMixIn, unittest.TestCase):

    filename = 'tests/data/all-field-types.html'
    encoding = 'utf-8'

    def test_imports(self):
        self.assertIs(rows.import_from_html,
                      rows.plugins.html.import_from_html)
        self.assertIs(rows.export_to_html, rows.plugins.html.export_to_html)

    def test_import_from_html_filename(self):
        table = rows.import_from_html(self.filename, encoding=self.encoding)
        self.assert_table_equal(table, utils.table)

        expected_meta = {'imported_from': 'html', 'filename': self.filename,}
        self.assertEqual(table.meta, expected_meta)

    def test_import_from_html_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        with open(self.filename) as fobj:
            table = rows.import_from_html(fobj, encoding=self.encoding)
        self.assert_table_equal(table, utils.table)

        expected_meta = {'imported_from': 'html', 'filename': self.filename,}
        self.assertEqual(table.meta, expected_meta)

    @mock.patch('rows.plugins.html.create_table')
    def test_import_from_html_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'encoding': 'iso-8859-15', 'some_key': 123, 'other': 456, }
        result = rows.import_from_html(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'html', 'filename': self.filename, }
        self.assertEqual(call[1], kwargs)

    def test_export_to_html_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_html(utils.table, temp.name)

        table = rows.import_from_html(temp.name)
        self.assert_table_equal(table, utils.table)

    def test_export_to_html_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_html(utils.table, temp.file)

        table = rows.import_from_html(temp.name)
        self.assert_table_equal(table, utils.table)

    @mock.patch('rows.plugins.html.serialize')
    def test_export_to_html_uses_serialize(self, mocked_serialize):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        kwargs = {'test': 123, 'parameter': 3.14, 'encoding': 'utf-8', }
        mocked_serialize.return_value = iter([list(utils.table.fields.keys())])

        rows.export_to_html(utils.table, temp.name, **kwargs)
        self.assertTrue(mocked_serialize.called)
        self.assertEqual(mocked_serialize.call_count, 1)

        call = mocked_serialize.call_args
        self.assertEqual(call[0], (utils.table, ))
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins.html.export_data')
    def test_export_to_html_uses_export_data(self, mocked_export_data):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        kwargs = {'test': 123, 'parameter': 3.14, 'encoding': 'utf-8', }
        mocked_export_data.return_value = 42

        result = rows.export_to_html(utils.table, temp.name, **kwargs)
        self.assertTrue(mocked_export_data.called)
        self.assertEqual(mocked_export_data.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_export_data.call_args
        self.assertEqual(call[0][0], temp.name)
        self.assertEqual(call[1], {})

    def test_export_to_html_none(self):
        # TODO: may test with codecs.open passing an encoding
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        result = rows.export_to_html(utils.table)
        rows.export_to_html(utils.table, temp.file)
        temp.file.seek(0)
        self.assertEqual(temp.file.read(), result)

    def test_table_index(self):
        filename = 'tests/data/simple-table.html'
        fobj = open(filename)

        table_1 = rows.import_from_html(fobj)
        self.assertEqual(set(table_1.fields.keys()), set(['t0r0c0', 't0r0c1']))
        self.assertEqual(len(table_1), 1)
        self.assertEqual(table_1[0].t0r0c0, 't0r1c0')
        self.assertEqual(table_1[0].t0r0c1, 't0r1c1')

        fobj.seek(0)
        table_2 = rows.import_from_html(fobj, index=1)
        self.assertEqual(set(table_2.fields.keys()), set(['t1r0c0', 't1r0c1']))
        self.assertEqual(len(table_2), 2)
        self.assertEqual(table_2[0].t1r0c0, 't1r1c0')
        self.assertEqual(table_2[0].t1r0c1, 't1r1c1')
        self.assertEqual(table_2[1].t1r0c0, 't1r2c0')
        self.assertEqual(table_2[1].t1r0c1, 't1r2c1')

    def test_table_thead_tbody(self):
        filename = 'tests/data/table-thead-tbody.html'
        fobj = open(filename)

        table = rows.import_from_html(fobj)
        self.assertEqual(set(table.fields.keys()), set(['t1', 't2']))
        self.assertEqual(len(table), 2)
        self.assertEqual(table[0].t1, '456')
        self.assertEqual(table[0].t2, '123')
        self.assertEqual(table[1].t1, 'qqq')
        self.assertEqual(table[1].t2, 'aaa')

    def test_nested_tables_outer(self):
        filename = 'tests/data/nested-table.html'
        fobj = open(filename)

        table = rows.import_from_html(fobj)
        self.assertEqual(set(table.fields.keys()),
                         set(['t00r0c0', 't00r0c1', 't00r0c2']))
        self.assertEqual(len(table), 3)

        self.assertEqual(table[0].t00r0c0, 't0,0r1c0')
        self.assertEqual(table[0].t00r0c1, 't0,0r1c1')
        self.assertEqual(table[0].t00r0c2, 't0,0r1c2')

        inner_table = ('t0,1r0c0 t0,1r0c1 t0,1r1c0 t0,1r1c1 t0,1r2c0 '
                       't0,1r2c1 t0,2r0c0 t0,2r0c1 t0,2r1c0 t0,2r1c1 '
                       't0,1r3c1 t0,1r4c0 t0,1r4c1 t0,1r5c0 t0,1r5c1').split()
        self.assertEqual(table[1].t00r0c0, 't0,0r2c0')
        self.assertEqual(cleanup_lines(table[1].t00r0c1), inner_table)
        self.assertEqual(table[1].t00r0c2, 't0,0r2c2')

        self.assertEqual(table[2].t00r0c0, 't0,0r3c0')
        self.assertEqual(table[2].t00r0c1, 't0,0r3c1')
        self.assertEqual(table[2].t00r0c2, 't0,0r3c2')

    def test_nested_tables_first_inner(self):
        filename = 'tests/data/nested-table.html'
        fobj = open(filename)

        table = rows.import_from_html(fobj, index=1)
        self.assertEqual(set(table.fields.keys()),
                         set(['t01r0c0', 't01r0c1']))
        self.assertEqual(len(table), 5)

        self.assertEqual(table[0].t01r0c0, 't0,1r1c0')
        self.assertEqual(table[0].t01r0c1, 't0,1r1c1')

        self.assertEqual(table[1].t01r0c0, 't0,1r2c0')
        self.assertEqual(table[1].t01r0c1, 't0,1r2c1')

        inner_table = 't0,2r0c0 t0,2r0c1 t0,2r1c0 t0,2r1c1'.split()
        self.assertEqual(cleanup_lines(table[2].t01r0c0), inner_table)
        self.assertEqual(table[2].t01r0c1, 't0,1r3c1')

        self.assertEqual(table[3].t01r0c0, 't0,1r4c0')
        self.assertEqual(table[3].t01r0c1, 't0,1r4c1')

        self.assertEqual(table[4].t01r0c0, 't0,1r5c0')
        self.assertEqual(table[4].t01r0c1, 't0,1r5c1')

    def test_nested_tables_second_inner(self):
        filename = 'tests/data/nested-table.html'
        fobj = open(filename)

        table = rows.import_from_html(fobj, index=2)
        self.assertEqual(set(table.fields.keys()),
                         set(['t02r0c0', 't02r0c1']))
        self.assertEqual(len(table), 1)

        self.assertEqual(table[0].t02r0c0, 't0,2r1c0')
        self.assertEqual(table[0].t02r0c1, 't0,2r1c1')

    def test_preserve_html(self):
        filename = 'tests/data/nested-table.html'
        fobj = open(filename)

        table = rows.import_from_html(fobj, preserve_html=True)
        expected_data = [
                '<table>', '<tr>', '<td> t0,1r0c0 </td>',
                '<td> t0,1r0c1 </td>', '</tr>', '<tr>', '<td> t0,1r1c0 </td>',
                '<td> t0,1r1c1 </td>', '</tr>', '<tr>', '<td> t0,1r2c0 </td>',
                '<td> t0,1r2c1 </td>', '</tr>', '<tr>', '<td>', '<table>',
                '<tr>', '<td> t0,2r0c0 </td>', '<td> t0,2r0c1 </td>', '</tr>',
                '<tr>', '<td> t0,2r1c0 </td>', '<td> t0,2r1c1 </td>', '</tr>',
                '</table>', '</td>', '<td> t0,1r3c1 </td>', '</tr>', '<tr>',
                '<td> t0,1r4c0 </td>', '<td> t0,1r4c1 </td>', '</tr>', '<tr>',
                '<td> t0,1r5c0 </td>', '<td> t0,1r5c1 </td>', '</tr>',
                '</table>']
        self.assertEqual(cleanup_lines(table[1].t00r0c1), expected_data)

    @mock.patch('rows.plugins.html.create_table')
    def test_preserve_html_and_not_skip_header(self, mocked_create_table):
        filename = 'tests/data/table-with-sections.html'

        # If `import_from_html` needs to identify field names, then it
        # should not preserve HTML inside first row
        table_1 = rows.import_from_html(filename, index=1, preserve_html=True)
        call_args = mocked_create_table.call_args_list.pop()
        data = call_args[0][0]
        kwargs = call_args[1]

        self.assertEqual(kwargs.get('fields', None), None)
        self.assertEqual(len(data), 6)
        self.assertNotIn('<', data[0][1])
        self.assertNotIn('>', data[0][1])
        for row in data[1:]:
            # Second field has HTML
            self.assertIn('<', row[1])
            self.assertIn('>', row[1])

        # If we provide fields and ask to preserve HTML and to don't skip
        # header then it should strip HTML from every row
        fields = OrderedDict([('first', rows.fields.TextField),
                              ('second', rows.fields.TextField),
                              ('third', rows.fields.TextField),
                              ('fourth', rows.fields.TextField)])
        table_2 = rows.import_from_html(filename, index=1, fields=fields,
                                        preserve_html=True, skip_header=False)
        call_args = mocked_create_table.call_args_list.pop()
        data = call_args[0][0]
        kwargs = call_args[1]

        self.assertEqual(kwargs.get('fields', None), fields)
        self.assertEqual(len(data), 6)
        for row in data:
            # Second field has HTML and should not be stripped
            self.assertIn('<', row[1])
            self.assertIn('>', row[1])

    def test_ignore_colspan(self):
        filename = 'tests/data/colspan-table.html'
        fobj = open(filename)

        table = rows.import_from_html(fobj, ignore_colspan=True)
        self.assertEqual(set(table.fields.keys()), set(['field1', 'field2']))
        self.assertEqual(len(table), 2)
        self.assertEqual(table[0].field1, 'row1field1')
        self.assertEqual(table[0].field2, 'row1field2')
        self.assertEqual(table[1].field1, 'row2field1')
        self.assertEqual(table[1].field2, 'row2field2')

        fobj = open(filename)
        with self.assertRaises(ValueError) as raises:
            table = rows.import_from_html(fobj, ignore_colspan=False)
        self.assertEqual(raises.exception.message, 'Number of fields differ')

    def test_extract_properties(self):
        filename = 'tests/data/properties-table.html'
        fobj = open(filename)

        table = rows.import_from_html(fobj, properties=True)
        self.assertEqual(list(table.fields.keys()),
                         ['field1', 'field2', 'properties'])
        self.assertEqual(list(table.fields.values()),
                         [rows.fields.TextField,
                          rows.fields.TextField,
                          rows.fields.JSONField])
        properties_1 = {'class': 'some-class another-class',
                        'data-test': 'value', }
        properties_2 = {'class': 'css-class', 'data-test': 'value2', }
        self.assertEqual(len(table), 2)
        self.assertEqual(table[0].field1, 'row1field1')
        self.assertEqual(table[0].field2, 'row1field2')
        self.assertEqual(table[0].properties, properties_1)
        self.assertEqual(table[1].field1, 'row2field1')
        self.assertEqual(table[1].field2, 'row2field2')
        self.assertEqual(table[1].properties, properties_2)


class PluginHtmlUtilsTestCase(unittest.TestCase):

    html = '<a href="some-url" class="some-class"> some text </a> other'

    def test_tag_to_dict(self):
        result = rows.plugins.html.tag_to_dict(self.html)
        expected = {'text': ' some text ', 'class': 'some-class',
                    'href': 'some-url'}
        self.assertEqual(result, expected)

    def test_tag_text(self):
        result = rows.plugins.html.tag_text(self.html)
        expected = ' some text '
        self.assertEqual(result, expected)
