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

# TODO: test this whole module
# TODO: add option to pass 'create_table' options in command-line (like force
#       fields)

import click

import rows

from rows.utils import import_from_uri, export_to_uri


@click.group()
def cli():
    pass


@cli.command(help='Convert table on `source` URI to `destination`')
@click.option('--input-encoding', default='utf-8')
@click.option('--output-encoding', default='utf-8')
@click.option('--input-locale', default='en_US.UTF-8')
@click.option('--output-locale', default='en_US.UTF-8')
@click.argument('source')
@click.argument('destination')
def convert(input_encoding, output_encoding, input_locale, output_locale,
            source, destination):
    input_locale = input_locale.split('.')
    output_locale = output_locale.split('.')

    with rows.locale_context(input_locale):
        table = import_from_uri(source)

    with rows.locale_context(output_locale):
        export_to_uri(destination, table)


@cli.command(help='Join tables from `source` URIs using `key(s)` to group rows and save into `destination`')
@click.option('--input-encoding', default='utf-8')
@click.option('--output-encoding', default='utf-8')
@click.option('--input-locale', default='en_US.UTF-8')
@click.option('--output-locale', default='en_US.UTF-8')
@click.argument('keys')
@click.argument('sources', nargs=-1, required=True)
@click.argument('destination')
def join(input_encoding, output_encoding, input_locale, output_locale, keys,
         sources, destination):
    keys = [key.strip() for key in keys.split(',')]
    input_locale = input_locale.split('.')
    output_locale = output_locale.split('.')

    with rows.locale_context(input_locale):
        tables = [import_from_uri(source) for source in sources]

    result = rows.join(keys, tables)

    with rows.locale_context(output_locale):
        export_to_uri(destination, result)


@cli.command(help='Sum tables from `source` URIs and save into `destination`')
@click.option('--input-encoding', default='utf-8')
@click.option('--output-encoding', default='utf-8')
@click.option('--input-locale', default='en_US.UTF-8')
@click.option('--output-locale', default='en_US.UTF-8')
@click.argument('sources', nargs=-1, required=True)
@click.argument('destination')
def sum(input_encoding, output_encoding, input_locale, output_locale, sources,
        destination):
    input_locale = input_locale.split('.')
    output_locale = output_locale.split('.')

    with rows.locale_context(input_locale):
        tables = [import_from_uri(source) for source in sources]

    result = tables[0]
    for table in tables[1:]:
        result = result + table

    with rows.locale_context(output_locale):
        export_to_uri(destination, result)


if __name__ == '__main__':
    cli()
