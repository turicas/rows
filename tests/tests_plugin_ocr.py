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
from rows.plugins.utils_rect import join_contiguous_rects

import tests.utils as utils

test_data = [
    {'char': 'R', 'left': 1282.0, 'bottom': 52.0, 'right': 1284.0, 'top': 63.0, 'page': 0.0},
    {'char': 'S', 'left': 1284.0, 'bottom': 52.0, 'right': 1295.0, 'top': 63.0, 'page': 0.0},
    {'char': '2', 'left': 1302.0, 'bottom': 52.0, 'right': 1303.0, 'top': 63.0, 'page': 0.0},
    {'char': '5', 'left': 1303.0, 'bottom': 52.0, 'right': 1309.0, 'top': 63.0, 'page': 0.0},
    {'char': '.', 'left': 1312.0, 'bottom': 53.0, 'right': 1317.0, 'top': 63.0, 'page': 0.0},
    {'char': '0', 'left': 1319.0, 'bottom': 53.0, 'right': 1321.0, 'top': 56.0, 'page': 0.0},
    {'char': '0', 'left': 1326.0, 'bottom': 53.0, 'right': 1334.0, 'top': 64.0, 'page': 0.0},
    {'char': '0', 'left': 1334.0, 'bottom': 53.0, 'right': 1338.0, 'top': 64.0, 'page': 0.0},
    {'char': ',', 'left': 1338.0, 'bottom': 53.0, 'right': 1343.0, 'top': 64.0, 'page': 0.0},
    {'char': '0', 'left': 1344.0, 'bottom': 51.0, 'right': 1347.0, 'top': 56.0, 'page': 0.0},
    {'char': '0', 'left': 1352.0, 'bottom': 53.0, 'right': 1362.0, 'top': 64.0, 'page': 0.0},
]


class PluginOcrTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = "ocr"
    file_extension = "png"
    filename = "tests/data/all-field-types.png"

    def test_imports(self):
        self.assertIs(rows.import_from_image, rows.plugins.ocr.import_from_image)

    def basic_test(self):
        table = rows.import_from_image(self.filename)
        # TODO: assert


class TestRectUtils(unittest.TestCase):

    def test_join_contiguous_rects(self):
        self.assertEquals(
            join_contiguous_rects(test_data, 10),
            [{'char': 'RS25.000,00', 'left': 1282.0, 'bottom': 51.0, 'right': 1362.0, 'top': 64.0, 'page': 0.0}]
        )
