#!/usr/bin/env python
# coding: utf-8

import argparse
import os
import tempfile

import requests

import rows


def import_from(source):
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
        data = rows.import_from_csv(source)
    elif source_lower.endswith('.html') or source_lower.endswith('.htm'):
        with open(source) as fobj:
            data = rows.import_from_html(fobj.read())
    elif source_lower.endswith('.xls'):
        data = rows.import_from_xls(source)
    else:
        raise ValueError('Source type not identified')

    if delete_file:
        os.unlink(source)
    return data

def export_to(table, destination):
    if destination.lower().endswith('.csv'):
        return rows.export_to_csv(table, destination)
    elif destination.lower().endswith('.html') or \
            destination.lower().endswith('.htm'):
        return rows.export_to_html(table, destination)
    elif destination.lower().endswith('.xls'):
        return rows.export_to_xls(table, destination)
    else:
        raise ValueError('Destination type not identified')

def main():
    args = argparse.ArgumentParser(description='...')
    args.add_argument('--from', dest='source', required=True)
    args.add_argument('--to', dest='destination', required=True)
    args.add_argument('--encode-in', dest='encode_in', required=False)
    args.add_argument('--encode-out', dest='encode_out', required=False)
    args.add_argument('--locale-in', dest='locale_in', required=False)
    args.add_argument('--locale-out', dest='locale_out', required=False)
    argv = args.parse_args()

    if not argv.locale_in:
        table = import_from(argv.source)
    else:
        with rows.locale_context(locale_in):
            table = import_from(argv.source)

    if not argv.locale_out:
        export_to(table, argv.destination)
    else:
        with rows.locale_context(argv.locale_out):
            export_to(table, argv.destination)
