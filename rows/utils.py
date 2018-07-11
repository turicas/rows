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

import cgi
import csv
import gzip
import io
import mimetypes
import os
import sqlite3
import tempfile
from collections import OrderedDict
from itertools import islice
try:
    import lzma
except ImportError:
    lzma = None

import requests
from tqdm import tqdm

import rows
from rows.plugins.utils import make_header, slug

try:
    from urlparse import urlparse  # Python 2
except ImportError:
    from urllib.parse import urlparse  # Python 3

try:
    import magic
except ImportError:
    magic = None
else:
    if not hasattr(magic, 'detect_from_content'):
        # This is not the file-magic library
        magic = None

chardet = requests.compat.chardet
try:
    import urllib3
except ImportError:
    from requests.packages import urllib3
else:
    try:
        urllib3.disable_warnings()
    except AttributeError:
        # old versions of urllib3 or requests
        pass


# TODO: should get this information from the plugins
TEXT_PLAIN = {
        'txt': 'text/txt',
        'text': 'text/txt',
        'csv': 'text/csv',
        'json': 'application/json',
}
OCTET_STREAM = {
        'microsoft ooxml': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'par archive data': 'application/parquet',
}
FILE_EXTENSIONS = {
        'csv': 'text/csv',
        'db': 'application/x-sqlite3',
        'htm': 'text/html',
        'html': 'text/html',
        'json': 'application/json',
        'ods': 'application/vnd.oasis.opendocument.spreadsheet',
        'parquet': 'application/parquet',
        'sqlite': 'application/x-sqlite3',
        'text': 'text/txt',
        'tsv': 'text/csv',
        'txt': 'text/txt',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}
MIME_TYPE_TO_PLUGIN_NAME = {
        'application/json': 'json',
        'application/parquet': 'parquet',
        'application/vnd.ms-excel': 'xls',
        'application/vnd.oasis.opendocument.spreadsheet': 'ods',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
        'application/x-sqlite3': 'sqlite',
        'text/csv': 'csv',
        'text/html': 'html',
        'text/txt': 'txt',
}


class Source(object):
    'Define a source to import a `rows.Table`'

    __slots__ = ['plugin_name', 'uri', 'encoding', 'delete']

    def __init__(self, plugin_name=None, uri=None, encoding=None,
                 delete=False):
        self.plugin_name = plugin_name
        self.uri = uri
        self.delete = delete
        self.encoding = encoding

    def __repr__(self):
        return 'Source(plugin_name={}, uri={}, encoding={}, delete={})'\
                .format(self.plugin_name, self.uri, self.encoding, self.delete)


def plugin_name_by_uri(uri):
    'Return the plugin name based on the URI'

    # TODO: parse URIs like 'sqlite://' also
    parsed = urlparse(uri)
    basename = os.path.basename(parsed.path)

    if not basename.strip():
        raise RuntimeError('Could not identify file format.')

    plugin_name = basename.split('.')[-1].lower()
    if plugin_name in FILE_EXTENSIONS:
        plugin_name = MIME_TYPE_TO_PLUGIN_NAME[FILE_EXTENSIONS[plugin_name]]

    return plugin_name


def extension_by_source(source, mime_type):
    'Return the file extension used by this plugin'

    # TODO: should get this information from the plugin
    extension = source.plugin_name
    if extension:
        return extension

    if mime_type:
        return mime_type.split('/')[-1]


def normalize_mime_type(mime_type, mime_name, file_extension):

    file_extension = file_extension.lower() if file_extension else ''
    mime_name = mime_name.lower() if mime_name else ''
    mime_type = mime_type.lower() if mime_type else ''

    if mime_type == 'text/plain' and file_extension in TEXT_PLAIN:
        return TEXT_PLAIN[file_extension]

    elif mime_type == 'application/octet-stream' and mime_name in OCTET_STREAM:
        return OCTET_STREAM[mime_name]

    elif file_extension in FILE_EXTENSIONS:
        return FILE_EXTENSIONS[file_extension]

    else:
        return mime_type


def plugin_name_by_mime_type(mime_type, mime_name, file_extension):
    'Return the plugin name based on the MIME type'

    return MIME_TYPE_TO_PLUGIN_NAME.get(
            normalize_mime_type(mime_type, mime_name, file_extension),
            None)


def detect_local_source(path, content, mime_type=None, encoding=None):

    # TODO: may add sample_size

    filename = os.path.basename(path)
    parts = filename.split('.')
    extension = parts[-1] if len(parts) > 1 else None

    if magic is not None:
        detected = magic.detect_from_content(content)
        encoding = detected.encoding or encoding
        mime_name = detected.name
        mime_type = detected.mime_type or mime_type

    else:
        encoding = chardet.detect(content)['encoding'] or encoding
        mime_name = None
        mime_type = mime_type or mimetypes.guess_type(filename)[0]

    plugin_name = plugin_name_by_mime_type(mime_type, mime_name, extension)
    if encoding == 'binary':
        encoding = None

    return Source(uri=path,
                  plugin_name=plugin_name,
                  encoding=encoding)


def local_file(path, sample_size=1048576):

    # TODO: may change sample_size
    with open(path, 'rb') as fobj:
        content = fobj.read(sample_size)

    source = detect_local_source(path, content, mime_type=None, encoding=None)

    return Source(uri=path,
                  plugin_name=source.plugin_name,
                  encoding=source.encoding,
                  delete=False)


def download_file(uri, verify_ssl=True, timeout=5, progress=False,
                  chunk_size=8192, sample_size=1048576):

    response = requests.get(uri, verify=verify_ssl, timeout=timeout,
                            stream=True)
    if not response.ok:
        raise RuntimeError('HTTP response: {}'.format(response.status_code))

    # Get data from headers (if available) to help plugin + encoding detection
    filename, encoding, mime_type = uri, None, None
    headers = response.headers
    if 'content-type' in headers:
        mime_type, options = cgi.parse_header(headers['content-type'])
        encoding = options.get('charset', encoding)
    if 'content-disposition' in headers:
        _, options = cgi.parse_header(headers['content-disposition'])
        filename = options.get('filename', filename)

    if progress:
        total = response.headers.get('content-length', None)
        total = int(total) if total else None
        progress_bar = tqdm(desc='Downloading file', total=total,
                            unit='bytes', unit_scale=True, unit_divisor=1024)
    tmp = tempfile.NamedTemporaryFile(delete=False)
    sample_data = b''
    for data in response.iter_content(chunk_size=chunk_size):
        tmp.file.write(data)
        if len(sample_data) <= sample_size:
            sample_data += data
        if progress:
            progress_bar.update(len(data))
    tmp.file.close()
    if progress:
        progress_bar.close()

    # Detect file type and rename temporary file to have the correct extension
    source = detect_local_source(filename, sample_data, mime_type, encoding)
    extension = extension_by_source(source, mime_type)
    filename = '{}.{}'.format(tmp.name, extension)
    os.rename(tmp.name, filename)

    return Source(uri=filename,
                  plugin_name=source.plugin_name,
                  encoding=source.encoding,
                  delete=True)


def detect_source(uri, verify_ssl, progress, timeout=5):
    '''Return a `rows.Source` with information for a given URI

    If URI starts with "http" or "https" the file will be downloaded.

    This function should only be used if the URI already exists because it's
    going to download/open the file to detect its encoding and MIME type.
    '''

    # TODO: should also supporte other schemes, like file://, sqlite:// etc.

    if uri.lower().startswith('http://') or uri.lower().startswith('https://'):
        return download_file(uri, verify_ssl=verify_ssl, timeout=timeout,
                             progress=progress)

    else:
        return local_file(uri)


def import_from_source(source, default_encoding, *args, **kwargs):
    'Import data described in a `rows.Source` into a `rows.Table`'

    plugin_name = source.plugin_name
    kwargs['encoding'] = (kwargs.get('encoding', None) or
                          source.encoding or
                          default_encoding)

    try:
        import_function = getattr(rows, 'import_from_{}'.format(plugin_name))
    except AttributeError:
        raise ValueError('Plugin (import) "{}" not found'.format(plugin_name))

    table = import_function(source.uri, *args, **kwargs)

    if source.delete:
        os.unlink(source.uri)

    return table


def import_from_uri(uri, default_encoding='utf-8', verify_ssl=True,
                    progress=False, *args, **kwargs):
    'Given an URI, detects plugin and encoding and imports into a `rows.Table`'

    # TODO: support '-' also
    # TODO: (optimization) if `kwargs.get('encoding', None) is not None` we can
    #       skip encoding detection.
    source = detect_source(uri, verify_ssl=verify_ssl, progress=progress)
    return import_from_source(source, default_encoding, *args, **kwargs)


def export_to_uri(table, uri, *args, **kwargs):
    'Given a `rows.Table` and an URI, detects plugin (from URI) and exports'

    # TODO: support '-' also
    plugin_name = plugin_name_by_uri(uri)

    try:
        export_function = getattr(rows, 'export_to_{}'.format(plugin_name))
    except AttributeError:
        raise ValueError('Plugin (export) "{}" not found'.format(plugin_name))

    return export_function(table, uri, *args, **kwargs)


def open_compressed(filename, mode='r', encoding='utf-8'):
    'Return a text-based file object from a filename, even if compressed'

    # TODO: this open compressed files feature will be incorported into the
    # library soon
    if str(filename).lower().endswith('.xz'):
        if lzma is None:
            raise RuntimeError('lzma support is not installed')

        fobj = lzma.open(filename, mode=mode)
        if 'b' in mode:
            return fobj
        return io.TextIOWrapper(fobj, encoding=encoding)

    elif str(filename).lower().endswith('.gz'):
        fobj = gzip.GzipFile(filename, mode=mode)
        if 'b' in mode:
            return fobj
        return io.TextIOWrapper(fobj, encoding=encoding)

    else:
        return open(filename, mode=mode, encoding=encoding)


def csv2sqlite(input_filename, output_filename, samples=None, batch_size=10000,
               encoding='utf-8', callback=None, force_types=None,
               table_name='table1'):
    'Export a CSV file to SQLite, based on field type detection from samples'

    # Identify data types
    fobj = open_compressed(input_filename, encoding=encoding)
    data = list(islice(csv.DictReader(fobj), samples))
    fields = rows.import_from_dicts(data).fields
    if force_types is not None:
        fields.update(force_types)

    # Create lazy table object to be converted
    # TODO: this lazyness feature will be incorported into the library soon
    reader = csv.reader(open_compressed(input_filename, encoding))
    header = next(reader)  # skip header
    table = rows.Table(fields=OrderedDict([(field, fields[field])
                                           for field in header]))
    table._rows = reader

    # Export to SQLite
    return rows.export_to_sqlite(table, output_filename, table_name=table_name,
                                 batch_size=batch_size, callback=callback)


class CsvLazyDictWriter:

    def __init__(self, filename, encoding='utf-8'):
        self.writer = None
        self.filename = filename
        self.encoding = encoding
        self._fobj = None

    @property
    def fobj(self):
        if self._fobj is None:
            self._fobj = open_compressed(
                self.filename,
                mode='w',
                encoding=self.encoding,
            )

        return self._fobj

    def writerow(self, row):
        if self.writer is None:
            self.writer = csv.DictWriter(self.fobj, fieldnames=list(row.keys()))
            self.writer.writeheader()

        self.writerow = self.writer.writerow
        return self.writerow(row)
