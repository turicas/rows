# coding: utf-8

# Copyright 2014-2019 Álvaro Justen <https://github.com/turicas/rows/>

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

import unittest

import rows

import tests.utils as utils


class PluginOcrTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = "ocr"
    file_extension = "png"
    filename = "tests/data/all-field-types.png"

    def test_imports(self):
        self.assertIs(rows.import_from_image, rows.plugins.ocr.import_from_image)

    def basic_test(self):
        table = rows.import_from_image(self.filename)
        # TODO: assert
