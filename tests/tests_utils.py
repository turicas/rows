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

import bz2
import contextlib
import gzip
import os
import shutil
import tempfile
import unittest

try:
    import lzma
except ImportError:
    lzma = None

import six

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


class TestUtilsDecompress(unittest.TestCase):

    def setUp(self):
        self.contents = b'I use rows and it is awesome!'
        self.temp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp)

    @contextlib.contextmanager
    def _create_file(self, algorithm, extension=True):
        extension = '.{}'.format(algorithm.__name__) if extension else ''
        filename = 'test{}'.format(extension)
        filepath = os.path.join(self.temp, filename)

        open_mapping = {
            bz2: bz2.BZ2File,
            gzip: gzip.GzipFile,
            lzma: getattr(lzma, 'LZMAFile')
        }
        open_method = open_mapping.get(algorithm)
        with open_method(filepath, 'wb') as obj:
            obj.write(self.contents)

        with open(filepath, 'rb') as obj:
            yield filepath, obj

    def _test_decompress_with_path(self, algorithm):
        with self._create_file(algorithm) as path_and_obj:
            path, _ = path_and_obj
            decompressed = rows.utils.decompress(path)
            self.assertEqual(self.contents, decompressed)

    def _test_decompress_with_file_obj(self, algorithm,):
        with self._create_file(algorithm) as path_and_obj:
            _, obj = path_and_obj
            decompressed = rows.utils.decompress(obj)
        self.assertEqual(self.contents, decompressed)

    def _test_decompress_without_extension(self, algorithm):
        with self._create_file(algorithm, False) as path_and_obj:
            path, _ = path_and_obj
            decompressed = rows.utils.decompress(path, algorithm.__name__)
        self.assertEqual(self.contents, decompressed)

    def test_decompress_bz2_with_path(self):
        self._test_decompress_with_path(bz2)

    def test_decompress_gzip_with_path(self):
        self._test_decompress_with_path(gzip)

    @unittest.skipIf(not lzma, 'No lzma module available')
    def test_decompress_lzma_with_path(self):
        self._test_decompress_with_path(lzma)

    def test_decompress_bz2_with_file_object(self):
        self._test_decompress_with_file_obj(bz2)

    def test_decompress_gzip_with_file_object(self):
        self._test_decompress_with_file_obj(gzip)

    @unittest.skipIf(not lzma, 'No lzma module available')
    def test_decompress_lzma_with_file_object(self):
        self._test_decompress_with_file_obj(lzma)

    def test_decompress_bz2_without_extension(self):
        self._test_decompress_without_extension(bz2)

    def test_decompress_gzip_without_extension(self):
        self._test_decompress_without_extension(gzip)

    @unittest.skipIf(not lzma, 'No lzma module available')
    def test_decompress_lzma_without_extension(self):
        self._test_decompress_without_extension(lzma)

    def test_decompress_with_incompatible_file(self):
        with self.assertRaises(RuntimeError):
            with tempfile.NamedTemporaryFile() as tmp:
                rows.utils.decompress(tmp.name)
