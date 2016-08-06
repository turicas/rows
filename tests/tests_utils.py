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

import types
import unittest

from collections import OrderedDict

from rows.utils import ipartition, slug


class UtilsTestCase(unittest.TestCase):

    def test_slug(self):
        self.assertEqual(slug('Álvaro Justen'), 'alvaro_justen')
        self.assertEqual(slug("Moe's Bar"), 'moes_bar')
        self.assertEqual(slug("-----te-----st------"), 'te_st')

    def test_slug_double_underscore(self):
        'Reported in <https://github.com/turicas/rows/issues/179>'

        self.assertEqual(slug('Query Occurrence"( % ),"First Seen'),
                         'query_occurrence_first_seen')
        self.assertEqual(slug(' álvaro  justen% '), 'alvaro_justen')

    def test_ipartition(self):
        iterable = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = ipartition(iterable, 3)
        self.assertEqual(type(result), types.GeneratorType)
        self.assertEqual(list(result), [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]])

        result = ipartition(iterable, 2)
        self.assertEqual(type(result), types.GeneratorType)
        self.assertEqual(list(result), [[1, 2], [3, 4], [5, 6], [7, 8],
                                        [9, 10]])


    # TODO: test download_file
    # TODO: test get_uri_information
    # TODO: test import_from_uri (test also args like encoding)
    # TODO: test export_to_uri (test also args like encoding)
