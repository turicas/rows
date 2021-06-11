# coding: utf-8

# Copyright 2014-2019 Álvaro Justen <https://github.com/turicas/rows/>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import os
from collections import OrderedDict, namedtuple
from operator import itemgetter
from pathlib import Path

import six

if six.PY2:
    from collections import MutableSequence, Sized
elif six.PY3:
    from collections.abc import MutableSequence, Sized


class BaseTable(MutableSequence):

    def __init__(self, fields, meta=None):
        from rows.plugins import utils

        # TODO: should we really use OrderedDict here?
        # TODO: should use slug on each field name automatically or inside each
        #       plugin?
        self.fields = OrderedDict(
            [
                (utils.slug(field_name), field_type)
                for field_name, field_type in OrderedDict(fields).items()
            ]
        )

        # TODO: should be able to customize row return type (namedtuple, dict
        #       etc.)
        self.Row = namedtuple("Row", self.field_names)
        self.meta = dict(meta) if meta is not None else {}

    def _repr_html_(self):
        import rows.plugins

        convert_to_html = rows.plugins.html.export_to_html

        total = len(self)
        if total <= 20:
            result = convert_to_html(self, caption=True)

        else:  # Show only head and tail
            representation = Table(
                fields=OrderedDict(
                    [
                        (field_name, rows.fields.TextField)
                        for field_name in self.field_names
                    ]
                ),
                meta={"name": self.name}
            )
            for row in self.head():
                representation.append(
                    {
                        field_name: field_type.serialize(getattr(row, field_name))
                        for field_name, field_type in self.fields.items()
                    }
                )
            representation.append(
                {field_name: "..." for field_name in self.field_names}
            )
            for row in self.tail():
                representation.append(
                    {
                        field_name: field_type.serialize(getattr(row, field_name))
                        for field_name, field_type in self.fields.items()
                    }
                )

            result = convert_to_html(representation, caption=True).replace(
                b"</caption>",
                b" (showing 20 rows, out of "
                + str(total).encode("ascii")
                + b")</caption>",
            )

        return result.decode("utf-8")

    @property
    def field_names(self):
        return list(self.fields.keys())

    @property
    def field_types(self):
        return list(self.fields.values())

    @property
    def name(self):
        """Define table name based on its metadata (filename used on import)

        If `filename` is not available, return `table1`.
        """

        from rows.plugins.utils import slug

        name = self.meta.get("name", None)
        if name is not None:
            return slug(name)

        source = self.meta.get("source", None)
        if source and source.uri:
            return slug(os.path.splitext(Path(source.uri).name)[0])

        return "table1"

    def __repr__(self):
        length = len(self) if isinstance(self, Sized) else "?"

        imported = ""
        if "imported_from" in self.meta:
            imported = " (from {})".format(self.meta["imported_from"])

        return "<rows.Table{} {} fields, {} rows>".format(
            imported, len(self.fields), length
        )

    def _make_row(self, row):
        # TODO: should be able to customize row type (namedtuple, dict etc.)
        return [
            field_type.deserialize(row.get(field_name, None))
            for field_name, field_type in self.fields.items()
        ]

    def __radd__(self, other):
        if other == 0:
            return self
        raise ValueError()

    def __iadd__(self, other):
        return self + other

    def __add__(self, other):
        raise NotImplementedError()


class Table(BaseTable):
    def __init__(self, fields, meta=None):
        super(Table, self).__init__(fields=fields, meta=meta)
        self._rows = []

    @classmethod
    def copy(cls, table, data):
        table = cls(fields=table.fields, meta=table.meta)
        table._rows = list(data)  # TODO: verify data?
        return table

    def head(self, n=10):
        return Table.copy(self, self._rows[:n])

    def tail(self, n=10):
        return Table.copy(self, self._rows[-n:])

    def append(self, row):
        """Add a row to the table. Should be a dict"""

        self._rows.append(self._make_row(row))

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, key):
        key_type = type(key)
        if key_type == int:
            return self.Row(*self._rows[key])
        elif key_type == slice:
            return Table.copy(self, self._rows[key])
        elif key_type is six.text_type:
            try:
                field_index = self.field_names.index(key)
            except ValueError:
                raise KeyError(key)

            # TODO: should change the line below to return a generator exp?
            return [row[field_index] for row in self._rows]
        else:
            raise ValueError("Unsupported key type: {}".format(type(key).__name__))

    def __setitem__(self, key, value):
        key_type = type(key)
        if key_type == int:
            self._rows[key] = self._make_row(value)
        elif key_type is six.text_type:
            from rows import fields
            from rows.plugins import utils

            values = list(value)  # I'm not lazy, sorry
            if len(values) != len(self):
                raise ValueError(
                    "Values length ({}) should be the same as "
                    "Table length ({})".format(len(values), len(self))
                )

            field_name = utils.slug(key)
            is_new_field = field_name not in self.field_names
            field_type = fields.detect_types(
                [field_name], [[value] for value in values]
            )[field_name]
            self.fields[field_name] = field_type
            self.Row = namedtuple("Row", self.field_names)

            if is_new_field:
                for row, value in zip(self._rows, values):
                    row.append(field_type.deserialize(value))
            else:
                field_index = self.field_names.index(field_name)
                for row, value in zip(self._rows, values):
                    row[field_index] = field_type.deserialize(value)
        else:
            raise ValueError("Unsupported key type: {}".format(type(key).__name__))

    def __delitem__(self, key):
        key_type = type(key)
        if key_type == int:
            del self._rows[key]
        elif key_type is six.text_type:
            try:
                field_index = self.field_names.index(key)
            except ValueError:
                raise KeyError(key)

            del self.fields[key]
            self.Row = namedtuple("Row", self.field_names)
            for row in self._rows:
                row.pop(field_index)
        else:
            raise ValueError("Unsupported key type: {}".format(type(key).__name__))

    def insert(self, index, row):
        self._rows.insert(index, self._make_row(row))

    def __add__(self, other):
        if other == 0:
            return self

        if not isinstance(self, type(other)) or self.fields != other.fields:
            raise ValueError("Tables have incompatible fields")
        else:
            table = Table(fields=self.fields)
            table._rows = self._rows + other._rows
            return table

    def order_by(self, key):
        # TODO: implement locale
        # TODO: implement for more than one key
        reverse = False
        if key.startswith("-"):
            key = key[1:]
            reverse = True

        field_names = self.field_names
        if key not in field_names:
            raise ValueError('Field "{}" does not exist'.format(key))

        key_index = field_names.index(key)
        self._rows.sort(key=itemgetter(key_index), reverse=reverse)


class FlexibleTable(Table):
    def __init__(self, fields=None, meta=None):
        if fields is None:
            fields = {}
        super(FlexibleTable, self).__init__(fields, meta)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.Row(**self._rows[key])
        elif isinstance(key, slice):
            return [self.Row(**row) for row in self._rows[key]]
        else:
            raise ValueError("Unsupported key type: {}".format(type(key).__name__))

    def _add_field(self, field_name, field_type):
        self.fields[field_name] = field_type
        self.Row = namedtuple("Row", self.field_names)

    def _make_row(self, row):
        from rows import fields

        for field_name in row.keys():
            if field_name not in self.field_names:
                self._add_field(field_name, fields.identify_type(row[field_name]))

        return {
            field_name: field_type.deserialize(row.get(field_name, None))
            for field_name, field_type in self.fields.items()
        }

    def insert(self, index, row):
        self._rows.insert(index, self._make_row(row))

    def __setitem__(self, key, value):
        self._rows[key] = self._make_row(value)

    def append(self, row):
        """Add a row to the table. Should be a dict"""

        self._rows.append(self._make_row(row))
