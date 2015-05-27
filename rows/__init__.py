# coding: utf-8

from collections import Mapping, OrderedDict, namedtuple
from contextlib import contextmanager

import fields


class Table(object):

    def __init__(self, fields):
        self.fields = OrderedDict(fields)
        self.field_names, self.field_types = [], []
        for field_name, field_type in self.fields.items():
            self.field_names.append(field_name)
            self.field_types.append(field_type)
        # TODO: should be able to customize row return type (namedtuple, dict etc.)
        self.Row = namedtuple('Row', self.field_names)
        self._rows = []

    def append(self, row):
        """Add a row to the table. Should be a dict"""

        # TODO: should be able to customize row type (namedtuple, dict etc.)
        row_data = []
        for field_name, field_type in self.fields.items():
            value = row.get(field_name, None)
            if not isinstance(value, field_type.TYPE):
                value = field_type.deserialize(value)
            row_data.append(value)
        self._rows.append(row_data)

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, item):
        # TODO: should support slice also?
        if not isinstance(item, int):
            raise ValueError('Type not recognized: {}'.format(type(item)))

        return self.Row(*self._rows[item])


def detect_field_types(field_names, sample_rows):
    """Where the magic happens"""

    # TODO: should expect data in unicode or will be able to use binary data?
    columns = zip(*sample_rows)
    # TODO: raise a ValueError exception instead
    assert len(columns) == len(field_names)

    available_types = list([getattr(fields, name) for name in fields.__all__
                            if name != 'Field'])
    none_type = set([type(None)])
    detected_types = OrderedDict([(field_name, None)
                                  for field_name in field_names])
    for index, field_name in enumerate(field_names):
        possible_types = list(available_types)
        column_data = set(columns[index])
        all_types = set(type(value) for value in column_data)
        all_types = list(all_types - none_type)

        if len(all_types) == 1 and all_types[0] not in (str, unicode):
            # all values in this column have the same type (!= str, unicode)
            identified_type = all_types[0]
        elif not [value for value in column_data if unicode(value).strip()]:
            # all rows with an empty field -> str (can't identify)
            identified_type = fields.StringField
        else:
            # ok, let's try to identify the type of this column by
            # converting every value in the sample
            for value in column_data:
                if unicode(value).strip() == '' or value is None:
                    # TODO: should test 'value in NULL'?
                    continue

                cant_be = None
                for type_ in possible_types:
                    try:
                        type_.deserialize(value)
                    except (ValueError, TypeError):
                        cant_be = type_
                        continue
                if cant_be is not None:
                    possible_types.remove(cant_be)

            identified_type = possible_types[0]  # priorities matter
        detected_types[field_name] = identified_type
    return detected_types

def import_from_csv(filename, delimiter=',', quotechar='"', encoding='utf-8'):
    # TODO: add auto_detect_types=True parameter
    # this import will be moved in the future (to another module, actually)
    import unicodecsv

    fobj = open(filename)
    csv_reader = unicodecsv.reader(fobj, encoding=encoding, delimiter=',',
                                   quotechar='"')
    table_rows = [row for row in csv_reader]
    header, table_rows = table_rows[0], table_rows[1:]

    field_types = detect_field_types(header, table_rows)
    table = Table(fields=field_types)
    for row in table_rows:
        table.append({field_name: value
                      for field_name, value in zip(header, row)})
    return table


import locale

@contextmanager
def locale_context(name, category=locale.LC_ALL):

    old_name = locale.getlocale(category)
    locale.setlocale(category, name)
    try:
        yield
    finally:
        locale.setlocale(category, old_name)
