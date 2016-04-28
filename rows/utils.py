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

import six
import os
import tempfile

from collections import Iterator
from unicodedata import normalize

import requests
try:
    import urllib3
except ImportError:
    from requests.packages import urllib3

import rows

try:
    urllib3.disable_warnings()
except AttributeError:
    # old versions of urllib3 or requests
    pass

SLUG_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'


def slug(text, encoding=None, separator='_', permitted_chars=SLUG_CHARS,
         replace_with_separator=' -_'):
    if isinstance(text, six.binary_type):
        text = text.decode(encoding or 'ascii')
    clean_text = text.strip()
    for char in replace_with_separator:
        clean_text = clean_text.replace(char, separator)
    double_separator = separator + separator
    while double_separator in clean_text:
        clean_text = clean_text.replace(double_separator, separator)
    ascii_text = normalize('NFKD', clean_text)
    strict_text = [x for x in ascii_text if x in permitted_chars]
    text = ''.join(strict_text).lower()

    if text.startswith(separator):
        text = text[len(separator):]
    if text.endswith(separator):
        text = text[:-len(separator)]

    return text


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
                data.append(next(iterator))
            except StopIteration:
                finished = True
                break
        if data:
            yield data


def download_file(uri, verify_ssl):
    response = requests.get(uri, verify=verify_ssl)
    content = response.content

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

    return {'filename': filename, 'encoding': response.encoding, }


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


def export_to_uri(uri, table, *args, **kwargs):
    # TODO: support '-' also
    plugin_name = uri.split('.')[-1].lower()

    try:
        export_function = getattr(rows, 'export_to_{}'.format(plugin_name))
    except AttributeError:
        raise ValueError('Plugin (export) "{}" not found'.format(plugin_name))

    export_function(table, uri, *args, **kwargs)
