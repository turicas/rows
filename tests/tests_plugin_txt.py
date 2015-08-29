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

import rows
import rows.plugins.txt
import utils


class PluginTxtTestCase(utils.RowsTestMixIn, unittest.TestCase):

    filename = 'tests/data/all-field-types.txt'
    encoding = 'utf-8'

    def test_imports(self):
        self.assertIs(rows.export_to_txt, rows.plugins.txt.export_to_txt)

    def test_export_to_txt_filename(self):
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_txt(utils.table, temp.name)

        self.assert_file_contents_equal(temp.name, self.filename)

    def test_export_to_txt_fobj(self):
        # TODO: may test with codecs.open passing an encoding
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        rows.export_to_txt(utils.table, temp.file)

        self.assert_file_contents_equal(temp.name, self.filename)
