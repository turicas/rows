# coding: utf-8

import collections
import locale

from unicodedata import normalize


# TODO: create functions to serialize/deserialize data

SLUG_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_'
NULL = ('-', 'null', 'none', 'nil')


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

    return ''.join(strict_text).lower()


def as_string(value):
    if isinstance(value, (unicode, str)):
        return value
    else:
        return str(value)


def is_null(value):
    if value is None:
        return True

    value_str = as_string(value).strip().lower()
    return not value_str or value_str in NULL


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
