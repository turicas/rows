# coding: utf-8

import collections
import locale

from unicodedata import normalize

import rows.fields


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

    return ''.join(strict_text)


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



def detect_field_types(field_names, sample_rows, *args, **kwargs):
    """Where the magic happens"""

    # TODO: should support receiving unicode objects directly
    # TODO: should expect data in unicode or will be able to use binary data?
    number_of_fields = len(field_names)
    columns = zip(*[row for row in sample_rows
                        if len(row) == number_of_fields])

    if len(columns) != len(field_names):
        raise ValueError('Number of fields differ')

    available_types = list([getattr(rows.fields, name)
                            for name in rows.fields.__all__
                            if name != 'Field'])
    none_type = set([type(None)])
    detected_types = collections.OrderedDict([(field_name, None)
                                              for field_name in field_names])
    encoding = kwargs.get('encoding', None)
    for index, field_name in enumerate(field_names):
        possible_types = list(available_types)
        column_data = set(columns[index])

        if not [value for value in column_data if as_string(value).strip()]:
            # all rows with an empty field -> str (can't identify)
            identified_type = rows.fields.ByteField
        else:
            # ok, let's try to identify the type of this column by
            # converting every value in the sample
            for value in column_data:
                if is_null(value):
                    continue

                cant_be = set()
                for type_ in possible_types:
                    try:
                        type_.deserialize(value, *args, **kwargs)
                    except (ValueError, TypeError):
                        cant_be.add(type_)
                for type_to_remove in cant_be:
                    possible_types.remove(type_to_remove)
            identified_type = possible_types[0]  # priorities matter
        detected_types[field_name] = identified_type
    return detected_types
