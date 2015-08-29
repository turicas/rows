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
import locale

from unicodedata import normalize

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
            header = make_header(table_rows[0])
            table_rows = table_rows[1:]
            detected_fields = detect_types(header, table_rows, *args, **kwargs)
            detected_fields.update(fields)
            fields = detected_fields
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
