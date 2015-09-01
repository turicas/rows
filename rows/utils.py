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

import collections
import os
import tempfile

from unicodedata import normalize

try:
    import magic
except ImportError:
    magic = None

import requests

import rows

from rows.fields import detect_types
from rows.table import Table


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


def ipartition(iterable, n):
    if not isinstance(iterable, collections.Iterator):
        iterator = iter(iterable)
    else:
        iterator = iterable

    finished = False
    while not finished:
        data = []
        for i in range(n):
            try:
                data.append(iterator.next())
            except StopIteration:
                finished = True
                break
        yield data


def make_header(data):
    header = [slug(field_name).lower() for field_name in data]
    return [field_name if field_name else 'field_{}'.format(index)
            for index, field_name in enumerate(header)]


def create_table(data, meta=None, force_headers=None, fields=None,
                 skip_header=True, *args, **kwargs):
    # TODO: add auto_detect_types=True parameter
    table_rows = list(data)

    if fields is None:
        if force_headers is None:
            header = make_header(table_rows[0])
            table_rows = table_rows[1:]
        else:
            header = force_headers
        fields = detect_types(header, table_rows, *args, **kwargs)
    else:
        if skip_header:
            table_rows = table_rows[1:]
            header = make_header(fields.keys())
            assert type(fields) is collections.OrderedDict
            fields = {field_name: fields[key]
                      for field_name, key in zip(header, fields)}
        else:
            header = make_header(fields.keys())

        # TODO: may reuse max_columns from html
        max_columns = max(len(row) for row in table_rows)
        assert len(fields) == max_columns

    # TODO: put this inside Table.__init__
    table = Table(fields=fields, meta=meta)
    for row in table_rows:
        table.append({field_name: value
                      for field_name, value in zip(header, row)})

    return table


def get_filename_and_fobj(filename_or_fobj, mode='r', dont_open=False):
    if getattr(filename_or_fobj, 'read', None) is not None:
        fobj = filename_or_fobj
        filename = getattr(fobj, 'name', None)
    else:
        fobj = open(filename_or_fobj, mode=mode) if not dont_open else None
        filename = filename_or_fobj

    return filename, fobj


def download_file(uri):
    response = requests.get(uri)
    content = response.content

    # TODO: try to guess with uri.split('/')[-1].split('.')[-1].lower()
    try:
        content_type = response.headers['content-type']
        plugin_name = content_type.split('/')[-1]
    except (KeyError, IndexError):
        if magic:
            with magic.Magic() as file_type_guesser:
                file_type = file_type_guesser.id_buffer(content)
            plugin_name = file_type.strip().split()[0]
        else:
            plugin_name = uri.split('/')[-1].split('.')[-1].lower()
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
