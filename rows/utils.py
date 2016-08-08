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

import cgi
import mimetypes
import os
import tempfile

from collections import Iterator
from unicodedata import normalize
from urlparse import urlparse

try:
    import magic
except ImportError:
    magic = None
else:
    if not hasattr(magic, 'detect_from_content'):
        # This is not the file-magic library
        magic = None


import requests
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

import rows

SLUG_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'


def slug(text, encoding=None, separator='_', permitted_chars=SLUG_CHARS,
         replace_with_separator=' -_'):
    '''Slugfy text

    Example: ' ÁLVARO justen% ' -> 'alvaro_justen'
    '''

    # Convert everything to unicode.
    # Example: b' ÁLVARO justen% ' -> u' ÁLVARO justen% '
    if isinstance(text, str):
        text = text.decode(encoding or 'ascii')

    # Strip non-ASCII characters
    # Example: u' ÁLVARO  justen% ' -> ' ALVARO  justen% '
    text = normalize('NFKD', text.strip()).encode('ascii', 'ignore')

    # Replace spaces and other chars with separator
    # Example: u' ALVARO  justen% ' -> u'_ALVARO__justen%_'
    for char in replace_with_separator:
        text = text.replace(char, separator)

    # Remove non-permitted characters and put everything to lowercase
    # Example: u'_ALVARO__justen%_' -> u'_alvaro__justen_'
    text = filter(lambda char: char in permitted_chars, text).lower()

    # Remove double occurrencies of separator
    # Example: u'_alvaro__justen_' -> u'_alvaro_justen_'
    double_separator = separator + separator
    while double_separator in text:
        text = text.replace(double_separator, separator)

    # Strip separators
    # Example: u'_alvaro_justen_' -> u'alvaro_justen'
    return text.strip(separator)


def ipartition(iterable, partition_size):
    if not isinstance(iterable, Iterator):
        iterator = iter(iterable)
    else:
        iterator = iterable

    finished = False
    while not finished:
        data = []
        for _ in range(partition_size):
            try:
                data.append(iterator.next())
            except StopIteration:
                finished = True
                break
        if data:
            yield data


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


def download_file(uri, verify_ssl):
    response = requests.get(uri, verify=verify_ssl)
    content = response.content
    if magic is not None:
        encoding = magic.detect_from_content(content).encoding
    else:
        encoding = response.encoding

    # TODO: try to guess with uri.split('/')[-1].split('.')[-1].lower()
    # TODO: try to guess with file-magic lib
    try:
        content_type = response.headers['content-type']
        plugin_name = content_type.split('/')[-1].split(';')[0].lower()
    except (KeyError, IndexError):
        try:
            plugin_name = uri.split('/')[-1].split('.')[-1].lower()
        except IndexError:
            raise RuntimeError('Could not identify file type.')

    tmp = tempfile.NamedTemporaryFile()
    filename = '{}.{}'.format(tmp.name, plugin_name)
    tmp.close()
    with open(filename, 'wb') as fobj:
        fobj.write(content)

    return {'filename': filename, 'encoding': encoding, }


def get_data_from_uri(uri, verify_ssl):
    if uri.startswith('http://') or uri.startswith('https://'):
        should_delete = True
        file_attributes = download_file(uri, verify_ssl=verify_ssl)
        filename = file_attributes['filename']
        encoding = file_attributes['encoding']
    else:
        should_delete = False
        filename = uri
        encoding = None

    plugin_name = filename.split('.')[-1].lower()
    if plugin_name == 'htm':
        plugin_name = 'html'
    elif plugin_name == 'text':
        plugin_name = 'txt'
    elif plugin_name == 'json':
        plugin_name = 'json'

    return {'should_delete': should_delete,
            'filename': filename,
            'plugin_name': plugin_name,
            'encoding': encoding, }


def import_from_uri(uri, default_encoding, verify_ssl=True, *args, **kwargs):
    # TODO: support '-' also
    file_attributes = get_data_from_uri(uri, verify_ssl=verify_ssl)
    should_delete = file_attributes['should_delete']
    filename = file_attributes['filename']
    plugin_name = file_attributes['plugin_name']
    encoding = file_attributes['encoding']
    if kwargs.get('encoding', None) is None:
        if encoding is not None:
            kwargs['encoding'] = encoding
        else:
            kwargs['encoding'] = default_encoding

    try:
        import_function = getattr(rows, 'import_from_{}'.format(plugin_name))
    except AttributeError:
        raise ValueError('Plugin (import) "{}" not found'.format(plugin_name))

    table = import_function(filename, *args, **kwargs)

    if should_delete:
        os.unlink(filename)

    return table


def export_to_uri(table, uri, *args, **kwargs):
    'Given a `rows.Table` and an URI, detects plugin (from URI) and exports'

    # TODO: support '-' also
    plugin_name = plugin_name_by_uri(uri)

    try:
        export_function = getattr(rows, 'export_to_{}'.format(plugin_name))
    except AttributeError:
        raise ValueError('Plugin (export) "{}" not found'.format(plugin_name))

    return export_function(table, uri, *args, **kwargs)
