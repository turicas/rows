# coding: utf-8

# Copyright 2014-2025 Álvaro Justen <https://github.com/turicas/rows/>
#    This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
#    Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
#    any later version.
#    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
#    warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
#    more details.
#    You should have received a copy of the GNU Lesser General Public License along with this program.  If not, see
#    <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import pytest

import bz2
import gzip
import io
import tempfile
try:
    import lzma
except ImportError:
    lzma = None
from pathlib import Path

from rows.fileio import cfopen
from rows.compat import PYTHON_VERSION, TEXT_TYPE


content = "Álvaro"
encoding = "iso-8859-1"
content_encoded = content.encode(encoding)

if PYTHON_VERSION < (3, 0, 0):
    def gzip_decompress(data):
        return gzip.GzipFile(fileobj=io.BytesIO(data)).read()
else:
    gzip_decompress = gzip.decompress


def assert_cfopen_path_filename_binary_content(suffix, decompress):
    temp = tempfile.NamedTemporaryFile(delete=False)
    filename = Path(temp.name + (suffix or ""))
    fobj = cfopen(filename, mode="wb")
    fobj.write(content_encoded)
    fobj.close()
    assert decompress(open(TEXT_TYPE(filename), mode="rb").read()) == content_encoded


def assert_cfopen_str_filename_binary_content(suffix, decompress):
    temp = tempfile.NamedTemporaryFile(delete=False)
    filename = TEXT_TYPE(temp.name + (suffix or ""))
    fobj = cfopen(filename, mode="wb")
    fobj.write(content_encoded)
    fobj.close()
    assert decompress(open(TEXT_TYPE(filename), mode="rb").read()) == content_encoded


def assert_cfopen_path_filename_text_content(suffix, decompress):
    temp = tempfile.NamedTemporaryFile(delete=False)
    filename = Path(temp.name + (suffix or ""))
    fobj = cfopen(filename, mode="w", encoding=encoding)
    fobj.write(content)
    fobj.close()
    assert decompress(open(TEXT_TYPE(filename), mode="rb").read()) == content_encoded


def assert_cfopen_str_filename_text_content(suffix, decompress):
    temp = tempfile.NamedTemporaryFile(delete=False)
    filename = TEXT_TYPE(temp.name + (suffix or ""))
    fobj = cfopen(filename, mode="w", encoding=encoding)
    fobj.write(content)
    fobj.close()
    assert decompress(open(TEXT_TYPE(filename), mode="rb").read()) == content_encoded


def test_cfopen_no_compression():
    same_content = lambda data: data
    assert_cfopen_str_filename_binary_content(suffix="", decompress=same_content)
    assert_cfopen_str_filename_text_content(suffix="", decompress=same_content)
    assert_cfopen_path_filename_binary_content(suffix="", decompress=same_content)
    assert_cfopen_path_filename_text_content(suffix="", decompress=same_content)


def test_cfopen_compression_gzip():
    assert_cfopen_str_filename_binary_content(suffix=".gz", decompress=gzip_decompress)
    assert_cfopen_str_filename_text_content(suffix=".gz", decompress=gzip_decompress)
    assert_cfopen_path_filename_binary_content(suffix=".gz", decompress=gzip_decompress)
    assert_cfopen_path_filename_text_content(suffix=".gz", decompress=gzip_decompress)


@pytest.mark.skipif(lzma is None, reason="lzma is not available")
def test_cfopen_compression_lzma():
    assert_cfopen_str_filename_binary_content(suffix=".xz", decompress=lzma.decompress)
    assert_cfopen_str_filename_text_content(suffix=".xz", decompress=lzma.decompress)
    assert_cfopen_path_filename_binary_content(suffix=".xz", decompress=lzma.decompress)
    assert_cfopen_path_filename_text_content(suffix=".xz", decompress=lzma.decompress)


def test_cfopen_compression_bz2():
    assert_cfopen_str_filename_binary_content(suffix=".bz2", decompress=bz2.decompress)
    assert_cfopen_str_filename_text_content(suffix=".bz2", decompress=bz2.decompress)
    assert_cfopen_path_filename_binary_content(suffix=".bz2", decompress=bz2.decompress)
    assert_cfopen_path_filename_text_content(suffix=".bz2", decompress=bz2.decompress)
