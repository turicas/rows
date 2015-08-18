# coding: utf-8

from collections import defaultdict, OrderedDict

from rows.table import Table


def join(keys, tables):
    """Merge a list of `row.Table` objects using `keys` to group rows"""

    if isinstance(keys, (str, unicode)):
        keys = (keys, )

    data = defaultdict(OrderedDict)
    fields = OrderedDict()
    for table in tables:
        fields.update(table.fields)

        for row in table:
            row_key = tuple([getattr(row, key) for key in keys])
            data[row_key].update({field: getattr(row, field)
                                  for field in row._fields})

    merged = Table(fields=fields)
    for row in data.values():
        for field in fields:
            if field not in row:
                row[field] = None
        merged.append(row)

    return merged
