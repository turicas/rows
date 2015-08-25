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

import codecs
import unittest

import rows
import utils


class PluginCsvTestCase(utils.ExpectedTableMixIn, unittest.TestCase):

    filename = 'tests/data/all-field-types.csv'
    encoding = 'utf-8'

    def test_import_from_csv_filename(self):
        table = rows.import_from_csv(self.filename, encoding=self.encoding)
        self.assert_expected_table(table)

    def test_import_from_csv_fobj(self):
        with open(self.filename) as fobj:
            table = rows.import_from_csv(fobj, encoding=self.encoding)
            self.assert_expected_table(table)

    def test_export_to_csv(self):
        # TODO: test export_to_csv
        self.fail()
