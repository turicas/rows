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

import unittest

from rows.cli import create_complete_query


class CliTestCase(unittest.TestCase):

    def test_create_complete_query(self):
        query = "-- Olá\n--Como vai?\n\n\n\t--aqui tem outro\n-- SELECT ahaha\n\t\n\n/*\nmultiline\ncomments\nin\nSQL\n\t\t\tWITH x AS (SELECT * FROM foo) SELECT * FROM x\n--teste\t\t*/\n\t\tSELECT * FROM bar"
        result = create_complete_query(query, [])
        expected = query
        assert result == expected

        result = create_complete_query("a > 1", ["tableX"])
        expected = "SELECT * FROM tableX WHERE a > 1"
        assert result == expected

    # TODO: test everything else
