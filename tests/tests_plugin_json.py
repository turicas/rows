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
import json
import rows
import utils


class PluginJsonTestCase(utils.RowsTestMixIn, unittest.TestCase):

    filename = 'tests/data/all-field-types.json'
    encoding = 'utf-8'

    def test_0_imports(self):
        self.assertIs(rows.import_from_json,
                      rows.plugins._json.import_from_json)
        self.assertIs(rows.export_to_json,
                      rows.plugins._json.export_to_json)

    def test_1_import_from_json_filename(self):
        table = rows.import_from_json(self.filename, encoding=self.encoding)
        self.assert_table_equal(table, utils.table)
        expected_meta = {'imported_from': 'json', 'filename': self.filename, }
        self.assertEqual(table.meta, expected_meta)

    def test_2_import_from_json_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        with open(self.filename) as fobj:
            table = rows.import_from_json(fobj, encoding=self.encoding)
        self.assert_table_equal(table, utils.table)

        expected_meta = {'imported_from': 'json', 'filename': self.filename, }
        self.assertEqual(table.meta, expected_meta)

    def test_3_export_to_json_filename(self):
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_json(utils.table, temp.name)
        table = rows.import_from_json(temp.name)
        self.assert_table_equal(table, utils.table)

    def test_export_to_json_filename_(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_json(utils.table, temp.name)
        with open(self.filename, 'rb') as fobj:
            first_json = json.loads(fobj.read())
            fobj.close()
        with open(temp.name, 'rb') as fobj:
            second_json = json.loads(fobj.read())
            fobj.close()
        import pprint
        pprint.pprint([first_json[0], second_json[0]])
        self.assertListEqual(first_json, second_json)

    def test_export_to_json_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        # TODO: may test file contents
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_json(utils.table, temp.file)

        table = rows.import_from_json(temp.name)
        self.assert_table_equal(table, utils.table)
