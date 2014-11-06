# coding: utf-8

# Copyright 2014 Álvaro Justen <https://github.com/turicas/rows/>
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

import logging
import types

from collections import defaultdict, OrderedDict
from itertools import chain

from .converters import TYPE_CONVERTERS, TYPES


LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def _str_decode(element, codec):
    if isinstance(element, str):
        return element.decode(codec)
    else:
        return element

def get_type(value):
    key_type = type(value)
    if key_type == unicode:
        return str
    return key_type


class BaseTable(object):
    '''Base class for the really useful table classes'''

    def __init__(self, fields, log_filename=None, log_level=logging.INFO,
            log_format=LOG_FORMAT, input_encoding='utf-8'):
        self.input_encoding = input_encoding
        self._rows = []
        self.logger = None

        self.fields = fields
        self.types = {} # TODO: auto-initialize with 'str'?
        self._fields_not_converted = 0
        self._rows_not_converted = 0
        self.converters = TYPE_CONVERTERS
        if log_filename is not None:
            self.logger = logging.Logger(log_filename, level=log_level)
            handler = FileHandler(log_filename)
            formatter = Formatter(LOG_FORMAT)
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def rename_field(self, old_name, new_name):
        self.fields[self.fields.index(old_name)] = new_name
        self.types[new_name] = self.types[old_name]
        del self.types[old_name]

    def convert_row(self, row):
        encoding = self.input_encoding
        converters = self.converters
        converted = []
        error_message = ('Could not convert field value "{value}" '
                         '(field {field}, type {type})')
        not_converted = self._fields_not_converted
        for index, field in enumerate(self.fields):
            try:
                converted_value = \
                        converters[self.types[field]](row[index], encoding)
            except ValueError:
                converted_value = None
                self._fields_not_converted += 1
                if self.logger is not None:
                    data = {'field': field, 'value': repr(row[index]),
                            'type': self.types[field]}
                    self.logger.warning(error_message.format(**data))
            converted.append(converted_value)
        if self._fields_not_converted > not_converted:
            self._rows_not_converted += 1
        return converted

    def identify_data_types(self, sample_size, skip=None):
        """Create ``self.types``, a ``dict`` in which each key is a table
        header (from ``self.fields``) and value is a type in:
        ``(int, float, datetime.date, datetime.datetime, str)``.

        The types are identified trying to convert each column value to each
        type.
        """

        # TODO: maybe use <https://github.com/scraperwiki/scrumble/>
        # TODO: test this sample algorithm

        sample_rows = self._get_sample(sample_size)
        columns = zip(*sample_rows)
        converters = self.converters
        input_encoding = self.input_encoding
        for i, header in enumerate(self.fields):
            column_types = list(TYPES)
            cant_be = set()
            try:
                column = set(columns[i])
            except IndexError:
                self.types[header] = str
            else:
                types = list(set([type(value) for value in column]) -
                             set([type(None)]))
                if len(types) == 1 and types[0] not in (str, unicode):
                    # all rows have the same type (!= str, unicode)
                    identified_type = types[0]
                elif not [value for value in column if unicode(value).strip()]:
                    # all rows with an empty field -> str (can't identify)
                    identified_type = str
                else:
                    # ok, let's try to identify the type of this column by
                    # converting every value in the sample
                    for value in column:
                        if unicode(value).strip() == '' or value is None:
                            continue
                        for type_ in column_types:
                            try:
                                converters[type_](value, input_encoding)
                            except (ValueError, TypeError):
                                if type_ == str:
                                    raise ValueError(
                                            '{} cant be {}'.format(repr(value),
                                        type_))
                                cant_be.add(type_)

                    for removed_type in cant_be:
                        column_types.remove(removed_type)
                    identified_type = column_types[0] # priorities matter
                self.types[header] = identified_type

        self.samples_read = len(sample_rows)

    def filter(self, func):
        # TODO: may use (and create) Table.copy?
        filtered = Table(fields=self.fields)

        filtered._rows = []
        for row in self._rows:
            row_as_dict = dict(zip(self.fields, self.convert_row(row)))
            if func(row_as_dict):
                filtered._rows.append(row)

        filtered.input_encoding = self.input_encoding
        filtered.converters = self.converters.copy()
        filtered.types = self.types

        return filtered


class LazyTable(BaseTable):
    def __init__(self, fields, iterable, log_filename=None,
            log_level=logging.INFO, log_format=LOG_FORMAT):
        super(LazyTable, self).__init__(fields, log_filename, log_level,
                log_format)
        self._rows = iterable

    def __iter__(self):
        return self

    def next(self):
        return dict(zip(self.fields, self.convert_row(self._rows.next())))

    def _get_sample(self, sample_size):
        if sample_size is not None:
            sample = []
            for index, row in enumerate(self._rows, start=1):
                sample.append(row)
                if index == sample_size:
                    break
            self._rows = chain(sample, self._rows)
        else:
            sample = list(self._rows)
            self._rows = iter(sample)
        return sample


class Table(BaseTable):


    def _get_sample(self, sample_size):
        if sample_size is not None:
            return self._rows[:sample_size]
        else:
            return self._rows


    def append(self, row):
        row = self._prepare_to_append(row)
        self._rows.append(row)
        if not self.types:
            self.types = {key: get_type(value)
                    for key, value in zip(self.fields, row)}
            self.append = self._append


    def _append(self, row):
        row = self._prepare_to_append(row)
        row_types = [get_type(value) for value in row]
        table_types = [self.types[key] for key in self.fields]
        if row_types != table_types:
            raise ValueError('Incorrect types')
        self._rows.append(row)


    def _prepare_to_append(self, item):
        if isinstance(item, dict):
            row = []
            for column in self.fields:
                if column in item:
                    value = item[column]
                else:
                    value = None
                row.append(value)
        elif isinstance(item, (tuple, set)):
            row = list(item)
        elif isinstance(item, list):
            row = item
        else:
            raise ValueError()
        if len(row) != len(self.fields):
            raise ValueError()
        return [_str_decode(value, self.input_encoding) for value in row]


    def extend(self, items):
        """Append a lot of items.
        ``items`` should be a list of new rows, each row can be represented as
        ``list``, ``tuple`` or ``dict``.
        If one of the rows causes a ``ValueError`` (for example, because it has
        more or less elements than it should), then nothing will be appended to
        ``Table``.
        """
        new_items = []
        for item in items:
            new_items.append(self._prepare_to_append(item))
        for item in new_items:
            self.append(item)


    def __len__(self):
        """Returns the number of rows. Same as ``len(list)``."""
        return len(self._rows)


    def __setitem__(self, item, value):
        if isinstance(item, (str, unicode)):
            if item not in self.fields:
                self.append_column(item, value)
            columns = zip(*self._rows)
            if not columns or len(value) != len(self):
                raise ValueError()
            else:
                columns[self.fields.index(item)] = value
                self._rows = [list(x) for x in zip(*columns)]
        elif isinstance(item, int):
            self._rows[item] = self._prepare_to_append(value)
        elif isinstance(item, slice):
            self._rows[item] = [self._prepare_to_append(v) for v in value]
        else:
            raise ValueError()


    def __getitem__(self, item):
        if isinstance(item, (str, unicode)):
            if item not in self.fields:
                raise KeyError()
            columns = zip(*self._rows)
            if not columns:
                return []
            else:
                return list(columns[self.fields.index(item)])
        elif isinstance(item, (int, slice)):
            return dict(zip(self.fields, self.convert_row(self._rows[item])))
        else:
            raise ValueError()


    def __delitem__(self, item):
        if isinstance(item, (str, unicode)):
            columns = zip(*self._rows)
            header_index = self.fields.index(item)
            del columns[header_index]
            del self.fields[header_index]
            self._rows = [list(row) for row in zip(*columns)]
        elif isinstance(item, (int, slice)):
            del self._rows[item]
        else:
            raise ValueError()


    def count(self, row):
        """Returns how many rows are equal to ``row`` in ``Table``.
        Same as ``list.count``.
        """
        return self._rows.count(self._prepare_to_append(row))


    def index(self, x, i=None, j=None):
        """Returns the index of row ``x`` in table (starting from zero).
        Same as ``list.index``.
        """
        x = self._prepare_to_append(x)
        if i is None and j is None:
            return self._rows.index(x)
        elif j is None:
            return self._rows.index(x, i)
        else:
            return self._rows.index(x, i, j)


    def insert(self, index, row):
        """Insert ``row`` in the position ``index``. Same as ``list.insert``.
        ``row`` can be ``list``, ``tuple`` or ``dict``.
        """
        self._rows.insert(index, self._prepare_to_append(row))


    def pop(self, index=-1):
        """Removes and returns row in position ``index``. ``index`` defaults
        to -1. Same as ``list.pop``.
        """
        return self._rows.pop(index)


    def remove(self, row):
        """Removes first occurrence of ``row``. Raises ``ValueError`` if
        ``row`` is not found. Same as ``list.remove``.
        """
        self._rows.remove(self._prepare_to_append(row))


    def reverse(self):
        """Reverse the order of rows *in place* (does not return a new
        ``Table``, change the rows in this instance of ``Table``).
        Same as ``list.reverse``.
        """
        self._rows.reverse()


    def add_field(self, name, values, position=None, row_as_dict=False):
        """Append a field to the table

        If `posision` is None, the field is added to the end
        """

        if (type(values) != types.FunctionType and \
            len(values) != len(self)) or \
           name in self.fields:
            raise ValueError()
        if position is None:
            insert_header = lambda name: self.fields.append(name)
            insert_data = lambda row, value: row.append(value)
        else:
            insert_header = lambda name: self.fields.insert(position, name)
            insert_data = lambda row, value: row.insert(position, value)
        for index, row in enumerate(self):
            if type(values) == types.FunctionType:
                if row_as_dict:
                    value = values({header: row[index] \
                                    for index, header in \
                                        enumerate(self.fields)})
                else:
                    value = values(row)
            else:
                value = values[index]
            if not row_as_dict:
                insert_data(row, _str_decode(value, self.input_encoding))
            else:
                row[name] = _str_decode(value, self.input_encoding)
        insert_header(name)
        self.types[name] = str


    def remove_field(self, field):
        field_index = self.fields.index(field)
        for row in self._rows:
            row.pop(field_index)
        self.fields.pop(field_index)
        del self.types[field]


    def order_by(self, column, ordering='asc'):
        index = self.fields.index(column)
        if ordering.lower().startswith('desc'):
            sort_function = lambda x, y: cmp(y[index], x[index])
        else:
            sort_function = lambda x, y: cmp(x[index], y[index])
        self._rows.sort(sort_function)


    def transpose(self):
        everything = [self.fields] + self._rows
        new = zip(*everything)
        self.fields = new[0]
        self._rows = new[1:]
        self.types = {}
        self.identify_data_types(sample_size=None)


    def __radd__(self, other):
        if other == 0:
            return self
        raise ValueError()


    def __add__(self, other):
        if other == 0:
            return self

        if type(self) != type(other) or self.fields != other.fields or \
                self.types != other.types:
            raise ValueError('iTables are incompatible '
                    '(fields or its types are different)')
        table = Table(fields=self.fields)
        table._rows = self._rows + other._rows
        table.types = self.types
        return table


def join(keys, *tables):
    '''Merge a list of tables, using `keys` to group rows'''

    if isinstance(keys, (str, unicode)):
        keys = (keys, )

    data = defaultdict(OrderedDict)
    fields = []
    types = {}
    for table in tables:
        types.update(table.types)

        for field in table.fields:
            if field not in fields:
                fields.append(field)

        for row in table:
            row_key = tuple([row[key] for key in keys])
            data[row_key].update(row)

    merged = Table(fields=fields)
    merged.types = types
    merged._rows = []
    for row in data.values():
        new_row = []
        for field in fields:
            if field not in row:
                new_row.append(None)
            else:
                new_row.append(row[field])
        merged._rows.append(new_row)

    return merged
