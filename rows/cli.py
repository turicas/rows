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

from io import BytesIO

import click
import requests.exceptions

import rows

from rows.utils import import_from_uri, export_to_uri
from rows.plugins.utils import make_header


DEFAULT_INPUT_ENCODING = 'utf-8'
DEFAULT_OUTPUT_ENCODING = 'utf-8'
DEFAULT_INPUT_LOCALE = 'C'
DEFAULT_OUTPUT_LOCALE = 'C'


def _import_table(source, encoding, verify_ssl=True, *args, **kwargs):
    try:
        table = import_from_uri(source, verify_ssl=verify_ssl,
                                encoding=encoding, *args, **kwargs)
    except requests.exceptions.SSLError:
        click.echo('ERROR: SSL verification failed! '
                   'Use `--verify-ssl=no` if you want to ignore.', err=True)
        sys.exit(2)
    else:
        return table

def _get_field_names(field_names, table_field_names, permit_not=False):
    new_field_names = make_header(field_names.split(','),
                                  permit_not=permit_not)
    if not permit_not:
        diff = set(new_field_names) - table_field_names
    else:
        diff = set(field_name.replace('^', '')
                   for field_name in new_field_names) - table_field_names

    if diff:
        missing = ', '.join(['"{}"'.format(field) for field in diff])
        click.echo('Table does not have fields: {}'.format(missing), err=True)
        sys.exit(1)
    else:
        return new_field_names


@click.group()
@click.version_option(version=rows.__version__, prog_name='rows')
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
        table = _import_table(source, encoding=input_encoding,
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
        tables = [_import_table(source, encoding=input_encoding,
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
    # TODO: `key` can be a list
    key = key.replace('^', '-')

    with rows.locale_context(input_locale):
        table = _import_table(source, encoding=input_encoding,
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
        tables = [_import_table(source, encoding=input_encoding,
                                verify_ssl=verify_ssl)
                  for source in sources]

    result = tables[0]
    for table in tables[1:]:
        result = result + table

    with rows.locale_context(output_locale):
        export_to_uri(destination, result, encoding=output_encoding)


@cli.command(name='print', help='Print a table')
@click.option('--input-encoding', default=DEFAULT_INPUT_ENCODING)
@click.option('--output-encoding', default=DEFAULT_OUTPUT_ENCODING)
@click.option('--input-locale', default=DEFAULT_INPUT_LOCALE)
@click.option('--output-locale', default=DEFAULT_OUTPUT_LOCALE)
@click.option('--verify-ssl', default=True, type=bool)
@click.option('--fields')
@click.option('--fields-except')
@click.option('--order-by')
@click.argument('source', required=True)
def print_(input_encoding, output_encoding, input_locale, output_locale,
           verify_ssl, fields, fields_except, order_by, source):

    if fields is not None and fields_except is not None:
        click.echo('ERROR: `--fields` cannot be used with `--fields-except`',
                   err=True)
        sys.exit(20)

    # TODO: may use `import_fields` for better performance
    with rows.locale_context(input_locale):
        table = _import_table(source, encoding=input_encoding,
                              verify_ssl=verify_ssl)

    table_field_names = set(table.fields.keys())
    if fields is not None:
        fields = _get_field_names(fields, table_field_names)
    if fields_except is not None:
        fields_except = _get_field_names(fields_except, table_field_names)

    if fields is not None and fields_except is None:
        export_fields = fields
    elif fields is not None and fields_except is not None:
        export_fields = list(fields)
        map(export_fields.remove, fields_except)
    elif fields is None and fields_except is not None:
        export_fields = list(table_field_names)
        map(export_fields.remove, fields_except)
    else:
        export_fields = table_field_names

    if order_by is not None:
        order_by = _get_field_names(order_by, table_field_names,
                                    permit_not=True)
        # TODO: use complete list of `order_by` fields
        table.order_by(order_by[0].replace('^', '-'))

    fobj = BytesIO()
    with rows.locale_context(output_locale):
        rows.export_to_txt(table, fobj, encoding=output_encoding,
                           export_fields=export_fields)
    # TODO: may pass unicode to click.echo if output_encoding is not provided

    fobj.seek(0)
    click.echo(fobj.read())


if __name__ == '__main__':
    cli()
