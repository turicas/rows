# coding: utf-8

from __future__ import unicode_literals

from collections import OrderedDict, namedtuple


class Table(object):

    def __init__(self, fields):
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

    def __radd__(self, other):
        if other == 0:
            return self
        raise ValueError()


    def __add__(self, other):
        if other == 0:
            return self

        if type(self) != type(other) or self.fields != other.fields:
            raise ValueError('Tables have incompatible fields')

        table = Table(fields=self.fields)
        for row in self:
            table.append({field: getattr(row, field) for field in row._fields})
        for row in other:
            table.append({field: getattr(row, field) for field in row._fields})
        return table

    def serialize(self, *args, **kwargs):
        fields = self.fields
        fields_items = fields.items()

        for row in self:
            yield [field_type.serialize(getattr(row, field_name),
                                        *args, **kwargs)
                   for field_name, field_type in fields_items]
