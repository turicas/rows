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
