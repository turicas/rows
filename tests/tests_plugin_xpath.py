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

import tempfile
import unittest

from collections import OrderedDict

import mock

import rows
import rows.plugins.xpath
import utils


class PluginXPathTestCase(utils.RowsTestMixIn, unittest.TestCase):

    filename = 'tests/data/ecuador-medios-radiodifusoras.html'
    encoding = 'utf-8'
    expected_data = 'tests/data/ecuador-medios-radiodifusoras.csv'

    def setUp(self):
        rows_xpath = '//*[@class="entry-container"]/*[@class="row-fluid"]/*[@class="span6"]'
        fields_xpath = OrderedDict([
                ('url', '//h2/a/@href'),
                ('name', '//h2/a/text()'),
                ('address', '//div[@class="spField field_direccion"]/text()'),
                ('phone', '//div[@class="spField field_telefono"]/text()'),
                ('website', '//div[@class="spField field_sitio_web"]/text()'),
                ('email', '//div[@class="spField field_email"]/text()'), ])
        self.kwargs = {'rows_xpath': rows_xpath,
                       'fields_xpath': fields_xpath, }

        self.expected_table = rows.import_from_csv(self.expected_data)
        self.files_to_delete = []

    def test_imports(self):
        self.assertIs(rows.import_from_xpath,
                      rows.plugins.xpath.import_from_xpath)

    def test_import_from_xpath_filename(self):
        table = rows.import_from_xpath(self.filename,
                                       encoding=self.encoding,
                                       **self.kwargs)

        expected_meta = {'imported_from': 'xpath', 'filename': self.filename,}
        self.assertEqual(table.meta, expected_meta)

        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        fobj = temp.file
        rows.export_to_csv(table, fobj)
        fobj.seek(0)
        table = rows.import_from_csv(fobj)

        self.assert_table_equal(table, self.expected_table)

    def test_import_from_xpath_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        with open(self.filename) as fobj:
            table = rows.import_from_xpath(fobj,
                                           encoding=self.encoding,
                                           **self.kwargs)

        expected_meta = {'imported_from': 'xpath', 'filename': self.filename,}
        self.assertEqual(table.meta, expected_meta)

        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        fobj = temp.file
        rows.export_to_csv(table, fobj)
        fobj.seek(0)
        table = rows.import_from_csv(fobj)

        self.assert_table_equal(table, self.expected_table)

    @mock.patch('rows.plugins.xpath.create_table')
    def test_import_from_xpath_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'encoding': 'iso-8859-15', 'some_key': 123, 'other': 456, }
        self.kwargs.update(kwargs)

        result = rows.import_from_xpath(self.filename, **self.kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'xpath', 'filename': self.filename,}
        self.assertEqual(call[1], kwargs)
