# coding: utf-8

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


def create_table(data, force_headers=None, fields=None, encoding=None, *args,
                 **kwargs):
    # TODO: add auto_detect_types=True parameter
    table_rows = list(data)

    if fields is None:
        if force_headers is None:
            header = make_header(table_rows[0])
            table_rows = table_rows[1:]
        else:
            header = force_headers
        fields = detect_types(header, table_rows, encoding=encoding)
    else:
        # TODO: may reuse max_columns from html
        max_columns = max(len(row) for row in table_rows)
        assert len(fields) == max_columns
        header = make_header(fields.keys())

    # TODO: put this inside Table.__init__
    table = Table(fields=fields)
    for row in table_rows:
        table.append({field_name: value
                      for field_name, value in zip(header, row)})

    return table
