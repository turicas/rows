# coding: utf-8

from collections import Mapping, OrderedDict, namedtuple


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


# TODO: implement with rows.locale('pt_BR.UTF-8'): ...
