# coding: utf-8

# Copyright 2014-2018 Álvaro Justen <https://github.com/turicas/rows/>

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

import tempfile
import unittest

import rows.utils
import tests.utils as utils


class UtilsTestCase(utils.RowsTestMixIn, unittest.TestCase):

    def assert_encoding(self, first, second):
        '''Assert encoding equality

        `iso-8859-1` should be detected as the same as `iso-8859-8`
        as described in <https://github.com/turicas/rows/issues/194>
        (affects Debian and Fedora packaging)
        '''

        self.assertEqual(first.lower().split('-')[:-1],
                         second.lower().split('-')[:-1])

    def test_local_file_sample_size(self):

        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)

        header = b'field1,field2,field3\r\n'
        row_data = b'non-ascii-field-1,non-ascii-field-2,non-ascii-field-3\r\n'
        encoding = 'iso-8859-1'
        temp.file.write(header)
        counter = len(header)
        increment = len(row_data)
        while counter <= 8192:
            temp.file.write(row_data)
            counter += increment
        temp.file.write('Álvaro,àáááããçc,ádfáffad\r\n'.encode(encoding))
        temp.file.close()

        result = rows.utils.local_file(temp.name)
        self.assertEqual(result.uri, temp.name)
        self.assert_encoding(result.encoding, encoding)
        self.assertEqual(result.delete, False)

# TODO: test detect_local_source
# TODO: test detect_source
# TODO: test download_file
# TODO: test export_to_uri
# TODO: test extension_by_plugin_name
# TODO: test import_from_source
# TODO: test import_from_uri
# TODO: test local_file
# TODO: test normalize_mime_type
# TODO: test plugin_name_by_mime_type
# TODO: test plugin_name_by_uri
