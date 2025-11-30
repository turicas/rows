# coding: utf-8

# Copyright 2014-2025 Álvaro Justen <https://github.com/turicas/rows/>
#    This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
#    Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
#    any later version.
#    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
#    warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
#    more details.
#    You should have received a copy of the GNU Lesser General Public License along with this program.  If not, see
#    <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import os
from collections import namedtuple
from operator import itemgetter
from pathlib import Path

from rows.compat import ORDERED_DICT, PYTHON_VERSION, TEXT_TYPE

if PYTHON_VERSION < (3, 0, 0):
    from collections import Iterable, MutableSequence, Sized  # noqa
else:
    from collections.abc import Iterable, MutableSequence


class Table(MutableSequence):

    def __new__(cls, *args, **kwargs):
        if cls is not Table:
            return super(Table, cls).__new__(cls)

        mode = kwargs.get("mode")
        subclasses = {
            "eager": EagerTable,
            "incremental": IncrementalTable,
            "stream": StreamTable,
            "flexible": FlexibleTable,
        }
        if mode is None:
            # XXX: must be the same as the value in `mode=XXX` on `__init__`
            mode = "eager"  # TODO: may change to a better one as the default for old versions
        elif mode.lower() not in subclasses.keys():
            raise ValueError("Unknown mode: {}".format(mode))
        subclass = subclasses.get(mode.lower())
        return super(Table, subclass).__new__(subclass)

    def __init__(self, fields, meta=None, mode=None, data=None):
        from collections import namedtuple

        from rows.fields import make_header

        # TODO: what if `fields` is None but `data` is not? Run the detection algorithm here instead of inside
        # `create_table`?
        if data is not None and not isinstance(data, Iterable):
            raise TypeError("`data` must be an iterable")
        self._original_data = data or []
        mode_from_class = self.__class__.__name__.replace("Table", "").lower()
        if mode is None:
            # TODO: add warning regarding changing the default
            pass
        elif mode != mode_from_class:
            raise TypeError("Invalid 'mode' parameter for {}: {}".format(self.__class__.__name__, repr(mode)))
        self._mode = mode_from_class

        # TODO: should we really use OrderedDict here?
        # TODO: should use slug/make_header on each field name automatically or inside each plugin?
        header = make_header(fields.keys())
        self.fields = ORDERED_DICT(
            [(header_name, field_type) for (header_name, (_, field_type)) in zip(header, fields.items())]
        )
        # TODO: should be able to customize row return type (namedtuple, dict etc.)
        self.Row = namedtuple("Row", self.field_names)
        self.meta = dict(meta) if meta is not None else {}
        self._rows = []
        self.__post_init__()

    def __post_init__(self):
        return

    def _make_row_from_tuple(self, row):
        from rows.fields import cached_type_deserialize

        # Python tuple creation from list comprehesion is faster than from generator expression:
        # <https://gist.github.com/turicas/f28c110d931c437f5b952040ec2c1da1>
        return tuple(
            [cached_type_deserialize(field_type, row[index]) for index, field_type in enumerate(self.fields.values())]
        )

    def _make_row_from_dict(self, row):
        from rows.fields import cached_type_deserialize

        # Python tuple creation from list comprehesion is faster than from generator expression:
        # <https://gist.github.com/turicas/f28c110d931c437f5b952040ec2c1da1>
        return tuple(
            [
                cached_type_deserialize(field_type, row.get(field_name, None))
                for field_name, field_type in self.fields.items()
            ]
        )

    def _add_or_replace_column(self, name, values):
        from rows.fields import cached_type_deserialize, detect_types, slug

        values = list(values)  # I'm not lazy, sorry
        if len(values) != len(self):
            raise ValueError(
                "Values length ({}) should be the same as " "Table length ({})".format(len(values), len(self))
            )

        field_name = slug(name)
        is_new_field = field_name not in self.field_names
        field_type = detect_types([field_name], [[value] for value in values])[field_name]
        # TODO: this type detection would benefit of having `TypeDetector.feed_column` implemented
        self.fields[field_name] = field_type
        self.Row = namedtuple("Row", self.field_names)

        if is_new_field:
            for (row_index, row), value in zip(enumerate(self._rows), values):
                self._rows[row_index] = tuple(list(row) + [cached_type_deserialize(field_type, value)])
        else:
            field_index = self.field_names.index(field_name)
            for (row_index, row), value in zip(enumerate(self._rows), values):
                self._rows[row_index] = tuple(
                    [
                        row_value if field_index != col_index else cached_type_deserialize(field_type, value)
                        for col_index, row_value in enumerate(row)
                    ]
                )

    def _del_column(self, name):
        try:
            field_index = self.field_names.index(name)
        except ValueError:
            raise KeyError(name)

        del self.fields[name]
        self.Row = namedtuple("Row", self.field_names)
        for index, row in enumerate(self._rows):
            self._rows[index] = tuple([value for col_index, value in enumerate(row) if col_index != field_index])

    @classmethod
    def copy(cls, table, data):
        table = cls(fields=table.fields, meta=table.meta, mode=table.mode)
        table._rows = list(data)  # TODO: verify data?
        return table

    def head(self, n=10):
        return Table.copy(self, self._rows[:n])

    def tail(self, n=10):
        return Table.copy(self, self._rows[-n:])

    def _serialize_to_dict(self, row):
        return {
            field_name: field_type.serialize(getattr(row, field_name)) for field_name, field_type in self.fields.items()
        }

    def _repr_html_(self):
        import rows.plugins
        from rows.fields import TextField

        show_head = self._mode != "stream"
        show_tail = self._mode in ("eager", "flexible") or (self._mode == "incremental" and self._filled)
        head_rows = list(self[:10]) if show_head else []
        tail_rows = list(self[-10:]) if show_tail else []
        total = len(self) if show_tail else "?"

        if show_tail and total <= 20:
            return rows.plugins.html.export_to_html(self, caption=True).decode("utf-8")

        # Show only head and tail
        representation = Table(
            fields=ORDERED_DICT([(field_name, TextField) for field_name in self.field_names]),
            meta={"name": self.name},
        )
        for row in head_rows:
            representation.append(self._serialize_to_dict(row))
        if tail_rows or not show_tail:
            representation.append({field_name: "..." for field_name in self.field_names})
        for row in tail_rows:
            representation.append(self._serialize_to_dict(row))
        result = rows.plugins.html.export_to_html(representation, caption=True)
        result = result.replace(
            b"</caption>",
            " (previewing {} rows out of ".format(len(head_rows) + len(tail_rows)).encode("ascii")
            + ("{:,}".format(total).encode("ascii") if show_tail else b"?")
            + b")</caption>",
        )
        return result.decode("utf-8")

    @property
    def mode(self):
        return self._mode

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

        from rows.fields import slug

        name = self.meta.get("name", None)
        if name is not None:
            return slug(name)

        source = self.meta.get("source", None)
        if source and source.uri:
            return slug(os.path.splitext(Path(source.uri).name)[0])

        return "table1"

    def __repr__(self):
        length = (
            len(self._rows)
            if self._mode in ("eager", "flexible") or (self._mode == "incremental" and self._filled)
            else "?"
        )
        imported = ""
        imported_from = self.meta.get("imported_from")
        if imported_from:
            imported = " (from {})".format(imported_from)
        class_name = type(self).__name__
        return "<{}{}: {} fields, {} rows>".format(class_name, imported, len(self.fields), length)

    def __radd__(self, other):
        if other == 0:
            return self
        raise ValueError()

    def __iadd__(self, other):
        return self + other

    def __add__(self, other):
        if other == 0:
            return self

        if not isinstance(self, type(other)) or self.fields != other.fields:
            raise ValueError("Tables have incompatible fields")
        else:
            # TODO: overwrite for each table type
            table = Table(fields=self.fields)
            table._rows = self._rows + other._rows
            return table

    def order_by(self, key):
        # TODO: overwrite for each table type
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

    def export(self, field_names=None):
        table_field_names = list(self.field_names)
        field_names = table_field_names if field_names is None else list(field_names)
        if table_field_names == field_names:  # Yield directly the stored rows
            for row in self._iter_tuples():
                yield row
        else:
            field_indexes = tuple(map(table_field_names.index, field_names))
            for row in self._iter_tuples():
                yield tuple([row[field_index] for field_index in field_indexes])

    def _maybe_close_source(self):
        source = self.meta.get("source", None)
        if source is not None:
            if getattr(source, "should_close", False):
                source.fobj.close()
            if getattr(source, "should_delete", False):
                path = Path(TEXT_TYPE(source.uri))
                if path.exists():
                    path.unlink()


class EagerTable(Table):
    def __init__(self, *args, **kwargs):
        super(EagerTable, self).__init__(*args, **kwargs)

    def __post_init__(self):
        self._rows = [self._make_row_from_tuple(row) for row in self._original_data]
        self._generator = None
        self._maybe_close_source()

    def _iter_tuples(self):
        return self._rows

    def __iter__(self):
        Row = self.Row
        return (Row(*row) for row in self._iter_tuples())

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.Row(*self._rows[key])
        elif isinstance(key, slice):
            return Table.copy(self, self._rows[key])
        elif isinstance(key, TEXT_TYPE):
            try:
                field_index = self.field_names.index(key)
            except ValueError:
                raise KeyError(key)
            return [row[field_index] for row in self._rows]
        else:
            raise ValueError("Unsupported key type: {}".format(type(key).__name__))

    def __setitem__(self, key, value):
        if isinstance(key, int):
            self._rows[key] = self._make_row_from_dict(value)
        elif isinstance(key, TEXT_TYPE):
            self._add_or_replace_column(name=key, values=value)
        elif isinstance(key, slice):
            self._rows[key] = [self._make_row_from_dict(v) for v in value]
        else:
            raise ValueError("Unsupported key type: {}".format(type(key).__name__))

    def __delitem__(self, key):
        if isinstance(key, int):
            del self._rows[key]
        elif isinstance(key, TEXT_TYPE):
            self._del_column(name=key)
        elif isinstance(key, slice):
            del self._rows[key]
        else:
            raise ValueError("Unsupported key type: {}".format(type(key).__name__))

    def append(self, row):
        """Add a row to the table. Should be a dict"""
        self._rows.append(self._make_row_from_dict(row))

    def extend(self, data):
        self._rows.extend(self._make_row_from_dict(row) for row in data)

    def insert(self, index, row):
        self._rows.insert(index, self._make_row_from_dict(row))


class IncrementalTable(Table):
    def __init__(self, *args, **kwargs):
        super(IncrementalTable, self).__init__(*args, **kwargs)

    def __post_init__(self):
        from itertools import chain

        self._rows = []
        self._rows_extra = []
        self._original_generator = map(self._make_row_from_tuple, self._original_data)
        self._generator = chain(self._original_generator, iter(self._rows_extra))
        self._filled = False

    def _iter_tuples(self):
        for row in self._rows:
            yield row
        for row in self._generator:
            self._rows.append(row)
            yield row
        self._filled = True
        self._maybe_close_source()

    def __iter__(self):
        for row in self._iter_tuples():
            yield self.Row(*row)

    def _fill_all(self):
        if not self._filled:
            self._rows.extend(self._generator)  # TODO: may avoid this if the generator is completely consumed
            self._filled = True
            self._maybe_close_source()

    def _fill_to_key(self, key):
        from itertools import islice

        current_len = len(self._rows)
        if current_len > key:
            return
        for row in islice(self._generator, key + 1 - current_len):
            self._rows.append(row)
        if len(self._rows) <= key:
            raise IndexError("Index out of range")

    def __len__(self):
        if not self._filled:
            self._fill_all()
        return len(self._rows)

    def __getitem__(self, key):
        if isinstance(key, int):
            self._fill_to_key(key)
            return self.Row(*self._rows[key])
        elif isinstance(key, slice):
            if key.stop is None:
                if not self._filled:
                    self._fill_all()
            else:
                self._fill_to_key(key.stop)
            return Table.copy(self, self._rows[key])
        elif isinstance(key, TEXT_TYPE):
            try:
                field_index = self.field_names.index(key)
            except ValueError:
                raise KeyError(key)
            if not self._filled:
                self._fill_all()
            return [row[field_index] for row in self._rows]
        else:
            raise ValueError("Unsupported key type: {}".format(type(key).__name__))

    def __setitem__(self, key, value):
        if isinstance(key, int):
            if key < 0:
                if not self._filled:
                    self._fill_all()
            else:
                self._fill_to_key(key)
            self._rows[key] = self._make_row_from_dict(value)
        elif isinstance(key, TEXT_TYPE):
            if not self._filled:
                self._fill_all()
            self._add_or_replace_column(name=key, values=value)
        elif isinstance(key, slice):
            stop = key.stop
            if stop is None:
                if not self._filled:
                    self._fill_all()
            else:
                if stop < 0:
                    if not self._filled:
                        self._fill_all()
                else:
                    self._fill_to_key(stop - 1)
            self._rows[key] = [self._make_row_from_dict(v) for v in value]
        else:
            raise ValueError("Unsupported key type: {}".format(type(key).__name__))

    def __delitem__(self, key):
        if isinstance(key, int):
            if key < 0:
                if not self._filled:
                    self._fill_all()
            else:
                self._fill_to_key(key)
            del self._rows[key]
        elif isinstance(key, TEXT_TYPE):
            if not self._filled:
                self._fill_all()
            self._del_column(name=key)
        elif isinstance(key, slice):
            start, stop = key.start, key.stop
            # TODO: what to do with `key.step`?
            if stop is None or (start is not None and start < 0) or (stop is not None and stop < 0):
                if not self._filled:
                    self._fill_all()
            else:
                self._fill_to_key(stop - 1)
            del self._rows[key]
        else:
            raise ValueError("Unsupported key type: {}".format(type(key).__name__))

    def append(self, row):
        """Add a row to the table. Should be a dict"""
        self._rows_extra.append(self._make_row_from_dict(row))

    def extend(self, data):
        self._rows_extra.extend(self._make_row_from_dict(row) for row in data)

    def insert(self, index, row):
        if index < 0:
            if not self._filled:
                self._fill_all()
        else:
            self._fill_to_key(index)
        self._rows.insert(index, self._make_row_from_dict(row))


class StreamTable(Table):
    def __init__(self, *args, **kwargs):
        super(StreamTable, self).__init__(*args, **kwargs)

    def __post_init__(self):
        self._rows = None
        self._generator = map(self._make_row_from_tuple, self._original_data)

    def _iter_tuples(self):
        return self._generator

    def __iter__(self):
        Row = self.Row
        for row in self._iter_tuples():
            yield Row(*row)
        self._maybe_close_source()

    def __len__(self):
        raise TypeError("Table length is unknown in 'stream' mode")

    def __getitem__(self, index):
        raise TypeError("Table is not indexable in 'stream' mode")

    def __setitem__(self, index, value):
        raise TypeError("Cannot set item in 'stream' mode")

    def __delitem__(self, index):
        raise TypeError("Cannot delete item in 'stream' mode")

    def append(self, row):
        """Add a row to the table. Should be a dict"""
        raise TypeError("Cannot append row in 'stream' mode")

    def extend(self, data):
        raise TypeError("Cannot extend Table in 'stream' mode")

    def insert(self, index, value):
        raise TypeError("Cannot insert row in 'stream' mode")

    @classmethod
    def copy(cls, table, data):
        raise TypeError("Cannot copy a table in 'stream' mode")


class FlexibleTable(EagerTable):
    def __init__(self, *args, **kwargs):
        kwargs["fields"] = kwargs.get("fields") or {}
        super(FlexibleTable, self).__init__(*args, **kwargs)

    def __post_init__(self):
        if self._original_data:
            self.extend(self._original_data)
        self._generator = None

    def __iter__(self):
        Row, field_names = self.Row, self.field_names
        return (Row(*[row.get(field_name) for field_name in field_names]) for row in self._rows)

    def __getitem__(self, key):
        if isinstance(key, int):
            row = self._rows[key]
            return self.Row(*[row.get(field_name) for field_name in self.field_names])
        elif isinstance(key, slice):
            Row, field_names = self.Row, self.field_names
            return [Row(*[row.get(field_name) for field_name in field_names]) for row in self._rows[key]]
        elif isinstance(key, TEXT_TYPE):
            if key not in self.field_names:
                raise KeyError(key)
            return [row.get(key) for row in self._rows]
        else:
            raise ValueError("Unsupported key type: {}".format(type(key).__name__))

    def _add_field(self, field_name, field_type):
        self.fields[field_name] = field_type
        self.Row = namedtuple("Row", self.field_names)

    def _make_row_from_dict(self, row):
        from rows.fields import cached_type_deserialize, identify_type

        for field_name in row.keys():
            if field_name not in self.field_names:
                self._add_field(field_name, identify_type(row[field_name]))
        return {
            field_name: cached_type_deserialize(field_type, row.get(field_name, None))
            for field_name, field_type in self.fields.items()
        }

    def insert(self, index, row):
        self._rows.insert(index, self._make_row_from_dict(row))

    def __setitem__(self, key, value):
        self._rows[key] = self._make_row_from_dict(value)

    def append(self, row):
        """Add a row to the table. Should be a dict"""

        self._rows.append(self._make_row_from_dict(row))

    def export(self, field_names=None):
        field_names = list(self.field_names) if field_names is None else list(field_names)
        for row in self._rows:
            yield tuple([row.get(field_name) for field_name in field_names])
