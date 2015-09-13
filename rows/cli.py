# coding: utf-8

# Copyright 2014-2015 Álvaro Justen <https://github.com/turicas/rows/>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

# TODO: define exit codes
# TODO: move default options to base command
# TODO: test this whole module
# TODO: add option to pass 'create_table' options in command-line (like force
#       fields)

import sys

import click
import requests.exceptions

import rows

from rows.utils import import_from_uri, export_to_uri


DEFAULT_INPUT_ENCODING = 'utf-8'
DEFAULT_OUTPUT_ENCODING = 'utf-8'
DEFAULT_INPUT_LOCALE = 'C'
DEFAULT_OUTPUT_LOCALE = 'C'


def import_table(source, encoding, verify_ssl=True):
    try:
        table = import_from_uri(source, verify_ssl=verify_ssl,
                                encoding=encoding)
    except requests.exceptions.SSLError:
        click.echo('ERROR: SSL verification failed! '
                   'Use `--verify-ssl=no` if you want to ignore.', err=True)
        sys.exit(2)
    else:
        return table


@click.group()
def cli():
    pass


@cli.command(help='Convert table on `source` URI to `destination`')
@click.option('--input-encoding', default=DEFAULT_INPUT_ENCODING)
@click.option('--output-encoding', default=DEFAULT_OUTPUT_ENCODING)
@click.option('--input-locale', default=DEFAULT_INPUT_LOCALE)
@click.option('--output-locale', default=DEFAULT_OUTPUT_LOCALE)
@click.option('--verify-ssl', default=True, type=bool)
@click.argument('source')
@click.argument('destination')
def convert(input_encoding, output_encoding, input_locale, output_locale,
            verify_ssl, source, destination):

    with rows.locale_context(input_locale):
        table = import_table(source, encoding=input_encoding,
                             verify_ssl=verify_ssl)

    with rows.locale_context(output_locale):
        export_to_uri(destination, table, encoding=output_encoding)


@cli.command(help='Join tables from `source` URIs using `key(s)` to group '
                  'rows and save into `destination`')
@click.option('--input-encoding', default=DEFAULT_INPUT_ENCODING)
@click.option('--output-encoding', default=DEFAULT_OUTPUT_ENCODING)
@click.option('--input-locale', default=DEFAULT_INPUT_LOCALE)
@click.option('--output-locale', default=DEFAULT_OUTPUT_LOCALE)
@click.option('--verify-ssl', default=True, type=bool)
@click.argument('keys')
@click.argument('sources', nargs=-1, required=True)
@click.argument('destination')
def join(input_encoding, output_encoding, input_locale, output_locale,
         verify_ssl, keys, sources, destination):
    keys = [key.strip() for key in keys.split(',')]

    with rows.locale_context(input_locale):
        tables = [import_table(source, encoding=input_encoding,
                               verify_ssl=verify_ssl)
                  for source in sources]

    result = rows.join(keys, tables)

    with rows.locale_context(output_locale):
        export_to_uri(destination, result, encoding=output_encoding)


@cli.command(help='Sort from `source` by `key(s)` and save into `destination`')
@click.option('--input-encoding', default=DEFAULT_INPUT_ENCODING)
@click.option('--output-encoding', default=DEFAULT_OUTPUT_ENCODING)
@click.option('--input-locale', default=DEFAULT_INPUT_LOCALE)
@click.option('--output-locale', default=DEFAULT_OUTPUT_LOCALE)
@click.option('--verify-ssl', default=True, type=bool)
@click.argument('key')
@click.argument('source')
@click.argument('destination')
def sort(input_encoding, output_encoding, input_locale, output_locale,
         verify_ssl, key, source, destination):
    key = key.replace('^', '-')

    with rows.locale_context(input_locale):
        table = import_table(source, encoding=input_encoding,
                             verify_ssl=verify_ssl)
        table.order_by(key)

    with rows.locale_context(output_locale):
        export_to_uri(destination, table, encoding=output_encoding)


@cli.command(name='sum',
             help='Sum tables from `source` URIs and save into `destination`')
@click.option('--input-encoding', default=DEFAULT_INPUT_ENCODING)
@click.option('--output-encoding', default=DEFAULT_OUTPUT_ENCODING)
@click.option('--input-locale', default=DEFAULT_INPUT_LOCALE)
@click.option('--output-locale', default=DEFAULT_OUTPUT_LOCALE)
@click.option('--verify-ssl', default=True, type=bool)
@click.argument('sources', nargs=-1, required=True)
@click.argument('destination')
def sum_(input_encoding, output_encoding, input_locale, output_locale,
         verify_ssl, sources, destination):

    with rows.locale_context(input_locale):
        tables = [import_table(source, encoding=input_encoding,
                               verify_ssl=verify_ssl)
                  for source in sources]

    result = tables[0]
    for table in tables[1:]:
        result = result + table

    with rows.locale_context(output_locale):
        export_to_uri(destination, result, encoding=output_encoding)


if __name__ == '__main__':
    cli()
