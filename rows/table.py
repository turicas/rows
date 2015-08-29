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

from collections import MutableSequence, namedtuple, OrderedDict
from operator import itemgetter

import rows.fields as fields


class Table(MutableSequence):

    def __init__(self, fields, meta=None):
        # TODO: should we really use OrderedDict here?
        # TODO: should use slug on each field name automatically or inside each
        #       plugin?
        self.fields = OrderedDict(fields)
        self.field_names = self.fields.keys()
        self.field_types = self.fields.values()

        # TODO: should be able to customize row return type (namedtuple, dict
        #       etc.)
        self.Row = namedtuple('Row', self.field_names)
        self._rows = []
        self.meta = dict(meta) if meta is not None else {}

    def _make_row(self, row):
        # TODO: should be able to customize row type (namedtuple, dict etc.)
        return [field_type.deserialize(row.get(field_name, None))
                for field_name, field_type in self.fields.items()]

    def append(self, row):
        """Add a row to the table. Should be a dict"""

        self._rows.append(self._make_row(row))

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, key):

        if isinstance(key, int):
            return self.Row(*self._rows[key])
        elif isinstance(key, slice):
            return [self.Row(*row) for row in self._rows[key]]
        else:
            raise ValueError('Type not recognized: {}'.format(type(key)))


    def __setitem__(self, key, value):
        self._rows[key] = self._make_row(value)

    def __delitem__(self, key):
        del self._rows[key]

    def insert(self, index, row):
        self._rows.insert(index, self._make_row(row))

    def __radd__(self, other):
        if other == 0:
            return self
        raise ValueError()

    # TODO: fix "table += other"
    def __add__(self, other):
        if other == 0:
            return self

        if type(self) != type(other) or self.fields != other.fields:
            raise ValueError('Tables have incompatible fields')

        table = Table(fields=self.fields)
        map(lambda row: table.append(row._asdict()), self)
        map(lambda row: table.append(row._asdict()), other)
        return table

    def order_by(self, key):
        # TODO: implement locale
        # TODO: implement for more than one key
        reverse = False
        if key.startswith('-'):
            key = key[1:]
            reverse = True

        field_names = self.fields.keys()
        if key not in field_names:
            raise ValueError('Field "{}" does not exist'.format(key))

        key_index = field_names.index(key)
        self._rows.sort(key=itemgetter(key_index), reverse=reverse)
