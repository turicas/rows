#!/usr/bin/env python
# coding: utf-8
"""
This plugin exports to a JSON file formatted according to the specifications of Google Bigquery
"""
import json

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

