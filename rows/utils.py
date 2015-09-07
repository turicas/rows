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

import os
import tempfile

from collections import Iterator
from unicodedata import normalize

import requests

import rows


# TODO: create functions to serialize/deserialize data

SLUG_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'


def slug(text, encoding=None, separator='_', permitted_chars=SLUG_CHARS,
         replace_with_separator=' -_'):
    if isinstance(text, str):
        text = text.decode(encoding or 'ascii')
    clean_text = text.strip()
    for char in replace_with_separator:
        clean_text = clean_text.replace(char, separator)
    double_separator = separator + separator
    while double_separator in clean_text:
        clean_text = clean_text.replace(double_separator, separator)
    ascii_text = normalize('NFKD', clean_text).encode('ascii', 'ignore')
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
                data.append(iterator.next())
            except StopIteration:
                finished = True
                break
        yield data


def download_file(uri):
    response = requests.get(uri)
    content = response.content

    # TODO: try to guess with uri.split('/')[-1].split('.')[-1].lower()
    try:
        content_type = response.headers['content-type']
        plugin_name = content_type.split('/')[-1]
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

    return filename


def get_uri_information(uri):
    if uri.startswith('http://') or uri.startswith('https://'):
        should_delete = True
        filename = download_file(uri)
    else:
        should_delete = False
        filename = uri

    plugin_name = filename.split('.')[-1].lower()
    if plugin_name == 'htm':
        plugin_name = 'html'
    elif plugin_name == 'text':
        plugin_name = 'txt'
    elif plugin_name == 'json':
        plugin_name = 'pjson'
    return should_delete, filename, plugin_name


def import_from_uri(uri):
    # TODO: support '-' also
    should_delete, filename, plugin_name = get_uri_information(uri)

    try:
        import_function = getattr(rows, 'import_from_{}'.format(plugin_name))
    except AttributeError:
        raise ValueError('Plugin (import) "{}" not found'.format(plugin_name))

    with open(filename) as fobj:
        table = import_function(fobj)

    if should_delete:
        os.unlink(filename)

    return table


def export_to_uri(uri, table):
    # TODO: support '-' also
    plugin_name = uri.split('.')[-1].lower()

    try:
        export_function = getattr(rows, 'export_to_{}'.format(plugin_name))
    except AttributeError:
        raise ValueError('Plugin (export) "{}" not found'.format(plugin_name))

    export_function(table, uri)
