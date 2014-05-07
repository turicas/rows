#!/usr/bin/env python
# coding: utf-8

import argparse

from .plugins import *


def import_from(source):
    if source.lower().endswith('.csv'):
        return import_from_csv(source)
    elif source.lower().endswith('.html') or source.lower().endswith('.htm'):
        return import_from_html(source)
    elif source.lower().startswith('mysql://'):
        return import_from_mysql(source[8:])
    else:
        raise ValueError('Source type not identified')

def export_to(table, destination):
    if destination.lower().endswith('.csv'):
        return table.export_to_csv(destination)
    elif destination.lower().endswith('.html') or \
            destination.lower().endswith('.htm'):
        return table.export_to_html(destination)
    if destination.lower().endswith('.txt'):
        return table.export_to_text(destination)
    elif destination.lower().startswith('mysql://'):
        return table.export_to_mysql(destination[8:])
    else:
        raise ValueError('Destination type not identified')

def main():
    args = argparse.ArgumentParser(description='...')
    args.add_argument('--from', dest='source', required=True)
    args.add_argument('--to', dest='destination', required=True)
    argv = args.parse_args()

    table = import_from(argv.source)
    export_to(table, argv.destination)
