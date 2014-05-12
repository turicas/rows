#!/usr/bin/env python
# coding: utf-8

import json

def write(table, filename=None):
    with open(filename, 'w'):
        json.dumps(table)
