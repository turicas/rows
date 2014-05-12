#!/usr/bin/env python
# coding: utf-8
"""
This plugin exports to a JSON file formatted according to the specifications of Google Bigquery
"""
import json
from .rows import LazyTable, Table

__all__ = ['import_from_JSON', 'export_to_JSON']


def export_to_JSON(table, filename=None):
    base_object = {'rows': []}
    for row in table:
        base_object['rows'].append({'json': row})
    if filename is not None:
        with open(filename, 'w') as f:
            f.write(json.dumps(base_object))
    else:
        return json.dumps(base_object)


def import_from_JSON(JSON, lazy=False):
    fields = JSON['rows'][0]['json'].keys()
    rows_iter = (row['json'] for row in JSON['rows'])

    if lazy:
        table = LazyTable(iterable=rows_iter, fields=fields)
    else:
        table = Table(fields=fields)
        table._rows = list(rows_iter)
    return table



