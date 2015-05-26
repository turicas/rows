#!/usr/bin/env python
# coding: utf-8

import argparse
import locale
import os
import tempfile

import requests

from .plugins import *


def import_from(source, fields=None, include_fields=None, exclude_fields=None):
    source_lower = source.lower()
    delete_file = False

    if source_lower.startswith('http://') or \
            source_lower.startswith('https://'):
        response = requests.get(source)
        try:
            content_type = response.headers['content-type']
            extension = content_type.split(';')[0].split('/')[-1]
        except (KeyError, IndexError):
            extension = ''

        tmp = tempfile.NamedTemporaryFile(delete=False)
        source = '{}.{}'.format(tmp.name, extension)
        source_lower = source.lower()
        delete_file = True
        with open(source, 'w') as fobj:
            fobj.write(response.content)

    if source_lower.endswith('.csv'):
        data = import_from_csv(source,
                               fields=fields,
                               include_fields=include_fields,
                               exclude_fields=exclude_fields)

    elif source_lower.endswith('.html') or source_lower.endswith('.htm'):
        with open(source) as fobj:
            data = import_from_html(fobj.read(),
                                    fields=fields,
                                    include_fields=include_fields,
                                    exclude_fields=exclude_fields)

    elif source_lower.startswith('mysql://'):
        data = import_from_mysql(source[8:],
                                 fields=fields,
                                 include_fields=include_fields,
                                 exclude_fields=exclude_fields)

    else:
        raise ValueError('Source type not identified')

    if delete_file:
        os.unlink(source)
    return data

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
    args.add_argument('--locale-in', dest='locale_in', required=False)
    args.add_argument('--locale-out', dest='locale_out', required=False)
    args.add_argument('--fields', dest='fields', required=False)
    args.add_argument('--include-fields', dest='include_fields',
                      required=False)
    args.add_argument('--exclude-fields', dest='exclude_fields',
                      required=False)
    argv = args.parse_args()

    if argv.locale_in:
        locale.setlocale(locale.LC_ALL, argv.locale_in)

    fields = None
    if argv.fields:
        fields = argv.fields.split(',')

    include_fields = None
    if argv.include_fields:
        include_fields = argv.include_fields.split(',')

    exclude_fields = None
    if argv.exclude_fields:
        exclude_fields = argv.exclude_fields.split(',')

    table = import_from(argv.source, fields=fields,
                        include_fields=include_fields,
                        exclude_fields=exclude_fields)

    if argv.locale_out:
        locale.setlocale(locale.LC_ALL, argv.locale_out)

    export_to(table, argv.destination)
