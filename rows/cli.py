# coding: utf-8

# Copyright 2014-2019 Álvaro Justen <https://github.com/turicas/rows/>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

# TODO: define exit codes
# TODO: move default options to base command
# TODO: may move all 'destination' to '--output'
# TODO: test this whole module
# TODO: add option to pass 'create_table' options in command-line (like force
#       fields)

import csv
import os
import pathlib
import sqlite3
import sys
from collections import defaultdict
from io import BytesIO

import click
import requests.exceptions
import six
from tqdm import tqdm

import rows
from rows.fields import make_header
from rows.utils import (
    ProgressBar,
    csv_to_sqlite,
    detect_source,
    download_file,
    export_to_uri,
    generate_schema,
    import_from_source,
    import_from_uri,
    load_schema,
    open_compressed,
    pgexport,
    pgimport,
    sqlite_to_csv,
    uncompressed_size,
)


DEFAULT_INPUT_ENCODING = "utf-8"
DEFAULT_INPUT_LOCALE = "C"
DEFAULT_OUTPUT_ENCODING = "utf-8"
DEFAULT_OUTPUT_LOCALE = "C"
HOME_PATH = pathlib.Path.home()
CACHE_PATH = HOME_PATH / ".cache" / "rows" / "http"


def parse_options(options):
    options_dict = {}
    for option in options:
        equal_position = option.find("=")
        if equal_position == -1:
            raise ValueError("Equal sign not found for {}".format(repr(option)))
        else:
            options_dict[option[:equal_position]] = option[equal_position + 1:]
    return options_dict


def _import_table(source, encoding, verify_ssl=True, progress=True, *args, **kwargs):
    # TODO: may use import_from_uri instead
    uri = source.uri if hasattr(source, "uri") else source
    try:
        table = import_from_uri(
            uri,
            default_encoding=DEFAULT_INPUT_ENCODING,
            verify_ssl=verify_ssl,
            encoding=encoding,
            progress=progress,
            *args,
            **kwargs,
        )
    except requests.exceptions.SSLError:
        click.echo(
            "ERROR: SSL verification failed! "
            "Use `--verify-ssl=no` if you want to ignore.",
            err=True,
        )
        sys.exit(2)
    else:
        return table


def _get_field_names(field_names, table_field_names, permit_not=False):
    new_field_names = make_header(field_names.split(","), permit_not=permit_not)
    if not permit_not:
        diff = set(new_field_names) - set(table_field_names)
    else:
        diff = set(field_name.replace("^", "") for field_name in new_field_names) - set(
            table_field_names
        )

    if diff:
        missing = ", ".join(['"{}"'.format(field) for field in diff])
        click.echo("Table does not have fields: {}".format(missing), err=True)
        sys.exit(1)
    else:
        return new_field_names


def _get_import_fields(fields, fields_exclude):
    if fields is not None and fields_exclude is not None:
        click.echo("ERROR: `--fields` cannot be used with `--fields-exclude`", err=True)
        sys.exit(20)
    elif fields is not None:
        return make_header(fields.split(","), permit_not=False)
    else:
        return None


def _get_export_fields(table_field_names, fields_exclude):
    if fields_exclude is not None:
        fields_exclude = _get_field_names(fields_exclude, table_field_names)
        return [
            field_name
            for field_name in table_field_names
            if field_name not in fields_exclude
        ]
    else:
        return None


def _get_schemas_for_inputs(schemas, inputs):
    if schemas is None:
        schemas = [None for _ in inputs]
    else:
        schemas = [schema.strip() or None for schema in schemas.split(",")]
        if len(schemas) > len(inputs):
            click.echo("ERROR: number of schemas is greater than sources", err=True)
            sys.exit(9)
        elif len(schemas) < len(inputs):
            diff = len(inputs) - len(schemas)
            for _ in range(diff):
                schemas.append(None)

    return [load_schema(schema) if schema else None for schema in schemas]


class AliasedGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        return click.Group.get_command(self, ctx, cmd_name) or click.Group.get_command(
            self, ctx, cmd_name.replace("2", "-to-")
        )


@click.group(cls=AliasedGroup)
@click.option("--http-cache", type=bool, default=False)
@click.option("--http-cache-path", default=str(CACHE_PATH.absolute()))
@click.version_option(version=rows.__version__, prog_name="rows")
def cli(http_cache, http_cache_path):
    if http_cache:
        import requests_cache

        http_cache_path = pathlib.Path(http_cache_path).absolute()
        if not http_cache_path.parent.exists():
            os.makedirs(str(http_cache_path.parent), exist_ok=True)
        if str(http_cache_path).lower().endswith(".sqlite"):
            http_cache_path = pathlib.Path(str(http_cache_path)[:-7]).absolute()

        requests_cache.install_cache(str(http_cache_path))


@cli.command(help="Convert table on `source` URI to `destination`")
@click.option("--input-encoding", default=None)
@click.option("--output-encoding", default="utf-8")
@click.option("--input-locale")
@click.option("--output-locale")
@click.option("--verify-ssl", type=bool, default=True)
@click.option("--order-by")
@click.option("--fields", help="A comma-separated list of fields to import")
@click.option("--fields-exclude", help="A comma-separated list of fields to exclude")
@click.option("--input-option", "-i", multiple=True, help="Custom (import) plugin key=value custom option (can be specified multiple times)")
@click.option("--output-option", "-o", multiple=True, help="Custom (export) plugin key=value custom option (can be specified multiple times)")
@click.option("--quiet", "-q", is_flag=True)
@click.argument("source")
@click.argument("destination")
def convert(
    input_encoding,
    output_encoding,
    input_locale,
    output_locale,
    verify_ssl,
    order_by,
    fields,
    fields_exclude,
    input_option,
    output_option,
    quiet,
    source,
    destination,
):

    input_options = parse_options(input_option)
    output_options = parse_options(output_option)
    progress = not quiet

    input_encoding = input_encoding or input_options.get("encoding", None)
    source_info = None
    if input_encoding is None:
        source_info = detect_source(uri=source, verify_ssl=verify_ssl, progress=progress)
        input_encoding = source_info.encoding or DEFAULT_INPUT_ENCODING

    import_fields = _get_import_fields(fields, fields_exclude)
    if input_locale is not None:
        with rows.locale_context(input_locale):
            table = _import_table(
                source_info or source,
                encoding=input_encoding,
                verify_ssl=verify_ssl,
                import_fields=import_fields,
                progress=progress,
                **input_options,
            )
    else:
        table = _import_table(
            source_info or source,
            encoding=input_encoding,
            verify_ssl=verify_ssl,
            import_fields=import_fields,
            progress=progress,
            **input_options,
        )

    if order_by is not None:
        order_by = _get_field_names(order_by, table.field_names, permit_not=True)
        # TODO: use complete list of `order_by` fields
        table.order_by(order_by[0].replace("^", "-"))

    export_fields = _get_export_fields(table.field_names, fields_exclude)
    # TODO: may use sys.stdout.encoding if output_file = '-'
    output_encoding = output_encoding or DEFAULT_OUTPUT_ENCODING
    if output_locale is not None:
        with rows.locale_context(output_locale):
            export_to_uri(
                table,
                destination,
                encoding=output_encoding,
                export_fields=export_fields,
                **output_options,
            )
    else:
        export_to_uri(
            table, destination, encoding=output_encoding,
            export_fields=export_fields,
            **output_options,
        )


@cli.command(
    help="Join tables from `source` URIs using `key(s)` to group "
    "rows and save into `destination`"
)
@click.option("--input-encoding", default=None)
@click.option("--output-encoding", default="utf-8")
@click.option("--input-locale")
@click.option("--output-locale")
@click.option("--verify-ssl", type=bool, default=True)
@click.option("--order-by")
@click.option("--fields", help="A comma-separated list of fields to export")
@click.option(
    "--fields-exclude",
    help="A comma-separated list of fields to exclude when exporting",
)
@click.argument("keys")
@click.argument("sources", nargs=-1, required=True)
@click.argument("destination")
def join(
    input_encoding,
    output_encoding,
    input_locale,
    output_locale,
    verify_ssl,
    order_by,
    fields,
    fields_exclude,
    keys,
    sources,
    destination,
):

    # TODO: detect input_encoding for all sources
    input_encoding = input_encoding or DEFAULT_INPUT_ENCODING

    export_fields = _get_import_fields(fields, fields_exclude)
    keys = make_header(keys.split(","), permit_not=False)

    if input_locale is not None:
        with rows.locale_context(input_locale):
            tables = [
                _import_table(source, encoding=input_encoding, verify_ssl=verify_ssl)
                for source in sources
            ]
    else:
        tables = [
            _import_table(source, encoding=input_encoding, verify_ssl=verify_ssl)
            for source in sources
        ]

    result = rows.join(keys, tables)
    if order_by is not None:
        order_by = _get_field_names(order_by, result.field_names, permit_not=True)
        # TODO: use complete list of `order_by` fields
        result.order_by(order_by[0].replace("^", "-"))

    if export_fields is None:
        export_fields = _get_export_fields(result.field_names, fields_exclude)
    # TODO: may use sys.stdout.encoding if output_file = '-'
    output_encoding = output_encoding or DEFAULT_OUTPUT_ENCODING
    if output_locale is not None:
        with rows.locale_context(output_locale):
            export_to_uri(
                result,
                destination,
                encoding=output_encoding,
                export_fields=export_fields,
            )
    else:
        export_to_uri(
            result, destination, encoding=output_encoding, export_fields=export_fields
        )


@cli.command(
    name="sum", help="Sum tables from `source` URIs and save into `destination`"
)
@click.option("--input-encoding", default=None)
@click.option("--output-encoding", default="utf-8")
@click.option("--input-locale")
@click.option("--output-locale")
@click.option("--verify-ssl", type=bool, default=True)
@click.option("--order-by")
@click.option("--fields", help="A comma-separated list of fields to import")
@click.option("--fields-exclude", help="A comma-separated list of fields to exclude")
@click.argument("sources", nargs=-1, required=True)
@click.argument("destination")
def sum_(
    input_encoding,
    output_encoding,
    input_locale,
    output_locale,
    verify_ssl,
    order_by,
    fields,
    fields_exclude,
    sources,
    destination,
):

    # TODO: detect input_encoding for all sources
    input_encoding = input_encoding or DEFAULT_INPUT_ENCODING

    import_fields = _get_import_fields(fields, fields_exclude)
    if input_locale is not None:
        with rows.locale_context(input_locale):
            tables = [
                _import_table(
                    source,
                    encoding=input_encoding,
                    verify_ssl=verify_ssl,
                    import_fields=import_fields,
                )
                for source in sources
            ]
    else:
        tables = [
            _import_table(
                source,
                encoding=input_encoding,
                verify_ssl=verify_ssl,
                import_fields=import_fields,
            )
            for source in sources
        ]

    result = sum(tables)
    if order_by is not None:
        order_by = _get_field_names(order_by, result.field_names, permit_not=True)
        # TODO: use complete list of `order_by` fields
        result.order_by(order_by[0].replace("^", "-"))

    export_fields = _get_export_fields(result.field_names, fields_exclude)
    # TODO: may use sys.stdout.encoding if output_file = '-'
    output_encoding = output_encoding or DEFAULT_OUTPUT_ENCODING
    if output_locale is not None:
        with rows.locale_context(output_locale):
            export_to_uri(
                result,
                destination,
                encoding=output_encoding,
                export_fields=export_fields,
            )
    else:
        export_to_uri(
            result, destination, encoding=output_encoding, export_fields=export_fields
        )


@cli.command(name="print", help="Print a table")
@click.option("--input-encoding", default=None)
@click.option("--output-encoding", default="utf-8")
@click.option("--input-locale")
@click.option("--input-option", "-i", multiple=True, help="Custom (import) plugin key=value custom option (can be specified multiple times)")
@click.option("--output-locale")
@click.option(
    "--frame-style", default="ascii", help="Options: ascii, single, double, none"
)
@click.option("--table-index", default=0)
@click.option("--verify-ssl", type=bool, default=True)
@click.option("--fields", help="A comma-separated list of fields to import")
@click.option("--fields-exclude", help="A comma-separated list of fields to exclude")
@click.option("--order-by")
@click.option("--quiet", "-q", is_flag=True)
@click.argument("source", required=True)
def print_(
    input_encoding,
    output_encoding,
    input_locale,
    input_option,
    output_locale,
    frame_style,
    table_index,
    verify_ssl,
    fields,
    fields_exclude,
    order_by,
    quiet,
    source,
):

    input_options = parse_options(input_option)
    progress = not quiet
    input_encoding = input_encoding or input_options.get("encoding", None)
    source_info = None
    if input_encoding is None:
        source_info = detect_source(uri=source, verify_ssl=verify_ssl, progress=progress)
        input_encoding = source_info.encoding or DEFAULT_INPUT_ENCODING

    import_fields = _get_import_fields(fields, fields_exclude)
    # TODO: if create_table implements `fields_exclude` this _import_table call
    # will import only the desired data
    if input_locale is not None:
        with rows.locale_context(input_locale):
            table = _import_table(
                source_info or source,
                encoding=input_encoding,
                verify_ssl=verify_ssl,
                index=table_index,
                import_fields=import_fields,
                progress=progress,
                **input_options,
            )
    else:
        table = _import_table(
            source_info or source,
            encoding=input_encoding,
            verify_ssl=verify_ssl,
            index=table_index,
            import_fields=import_fields,
            progress=progress,
            **input_options,
        )

    if order_by is not None:
        order_by = _get_field_names(order_by, table.field_names, permit_not=True)
        # TODO: use complete list of `order_by` fields
        table.order_by(order_by[0].replace("^", "-"))

    export_fields = _get_export_fields(table.field_names, fields_exclude)
    output_encoding = output_encoding or sys.stdout.encoding or DEFAULT_OUTPUT_ENCODING
    # TODO: may use output_options instead of custom TXT plugin options
    fobj = BytesIO()
    if output_locale is not None:
        with rows.locale_context(output_locale):
            rows.export_to_txt(
                table,
                fobj,
                encoding=output_encoding,
                export_fields=export_fields,
                frame_style=frame_style,
            )
    else:
        rows.export_to_txt(
            table,
            fobj,
            encoding=output_encoding,
            export_fields=export_fields,
            frame_style=frame_style,
        )

    fobj.seek(0)
    # TODO: may pass unicode to click.echo if output_encoding is not provided
    click.echo(fobj.read())


@cli.command(name="query", help="Query a table using SQL")
@click.option("--input-encoding", default=None)
@click.option("--output-encoding", default="utf-8")
@click.option("--input-locale")
@click.option("--output-locale")
@click.option("--verify-ssl", type=bool, default=True)
@click.option(
    "--samples",
    type=int,
    default=5000,
    help="Number of rows to determine the field types (0 = all)",
)
@click.option("--input-option", "-i", multiple=True, help="Custom (import) plugin key=value custom option (can be specified multiple times)")
@click.option("--output")
@click.option(
    "--frame-style", default="ascii", help="Options: ascii, single, double, none"
)
@click.option("--quiet", "-q", is_flag=True)
@click.argument("query", required=True)
@click.argument("sources", nargs=-1, required=True)
def query(
    input_encoding,
    output_encoding,
    input_locale,
    output_locale,
    verify_ssl,
    samples,
    input_option,
    output,
    frame_style,
    quiet,
    query,
    sources,
):

    # TODO: support multiple input options
    # TODO: detect input_encoding for all sources
    input_encoding = input_encoding or DEFAULT_INPUT_ENCODING
    progress = not quiet

    samples = samples if samples > 0 else None

    if not query.strip().lower().startswith("select"):
        table_names = ", ".join(
            ["table{}".format(index) for index in range(1, len(sources) + 1)]
        )
        query = "SELECT * FROM {} WHERE {}".format(table_names, query)

    if len(sources) == 1:
        source = detect_source(sources[0], verify_ssl=verify_ssl, progress=progress)

        if source.plugin_name in ("sqlite", "postgresql"):
            # Optimization: query the db directly
            result = import_from_source(
                source, input_encoding, query=query, samples=samples
            )
        else:
            if input_locale is not None:
                with rows.locale_context(input_locale):
                    table = import_from_source(
                        source, input_encoding, samples=samples
                    )
            else:
                table = import_from_source(
                    source, input_encoding, samples=samples
                )

            sqlite_connection = sqlite3.Connection(":memory:")
            rows.export_to_sqlite(table, sqlite_connection, table_name="table1")
            result = rows.import_from_sqlite(sqlite_connection, query=query)

    else:
        # TODO: if all sources are SQLite we can also optimize the import
        if input_locale is not None:
            with rows.locale_context(input_locale):
                tables = [
                    _import_table(
                        source,
                        encoding=input_encoding,
                        verify_ssl=verify_ssl,
                        samples=samples,
                        progress=progress,
                    )
                    for source in sources
                ]
        else:
            tables = [
                _import_table(
                    source,
                    encoding=input_encoding,
                    verify_ssl=verify_ssl,
                    samples=samples,
                    progress=progress,
                )
                for source in sources
            ]

        sqlite_connection = sqlite3.Connection(":memory:")
        for index, table in enumerate(tables, start=1):
            rows.export_to_sqlite(
                table, sqlite_connection, table_name="table{}".format(index)
            )

        result = rows.import_from_sqlite(sqlite_connection, query=query)

    # TODO: may use sys.stdout.encoding if output_file = '-'
    output_encoding = output_encoding or sys.stdout.encoding or DEFAULT_OUTPUT_ENCODING
    if output is None:
        fobj = BytesIO()
        if output_locale is not None:
            with rows.locale_context(output_locale):
                rows.export_to_txt(
                    result, fobj, encoding=output_encoding, frame_style=frame_style
                )
        else:
            rows.export_to_txt(
                result, fobj, encoding=output_encoding, frame_style=frame_style
            )
        fobj.seek(0)
        click.echo(fobj.read())
    else:
        if output_locale is not None:
            with rows.locale_context(output_locale):
                export_to_uri(result, output, encoding=output_encoding)
        else:
            export_to_uri(result, output, encoding=output_encoding)


@cli.command(name="schema", help="Identifies table schema")
@click.option("--input-encoding", default=None)
@click.option("--input-locale")
@click.option("--verify-ssl", type=bool, default=True)
@click.option("--input-option", "-i", multiple=True, help="Custom (import) plugin key=value custom option (can be specified multiple times)")
@click.option(
    "-f",
    "--format",
    "output_format",
    default="txt",
    type=click.Choice(("csv", "django", "sql", "txt")),
)
@click.option("--fields", help="A comma-separated list of fields to inspect")
@click.option(
    "--fields-exclude",
    help="A comma-separated list of fields to exclude from inspection",
)
@click.option(
    "--samples",
    type=int,
    default=5000,
    help="Number of rows to determine the field types (0 = all)",
)
@click.option("--quiet", "-q", is_flag=True)
@click.argument("source", required=True)
@click.argument("output", required=False, default="-")
def schema(
    input_encoding,
    input_locale,
    verify_ssl,
    input_option,
    output_format,
    fields,
    fields_exclude,
    samples,
    quiet,
    source,
    output,
):

    input_options = parse_options(input_option)
    progress = not quiet
    source_info = detect_source(uri=source, verify_ssl=verify_ssl, progress=progress)
    input_encoding = input_encoding or input_options.get("encoding", None) or DEFAULT_INPUT_ENCODING

    samples = samples if samples > 0 else None
    import_fields = _get_import_fields(fields, fields_exclude)

    if input_locale is not None:
        with rows.locale_context(input_locale):
            table = import_from_source(
                source_info,
                input_encoding,
                samples=samples,
                import_fields=import_fields,
                max_rows=samples,
                **input_options,
            )
    else:
        table = import_from_source(
            source_info,
            input_encoding,
            samples=samples,
            import_fields=import_fields,
            max_rows=samples,
            **input_options,
        )

    export_fields = _get_export_fields(table.field_names, fields_exclude)
    if export_fields is None:
        export_fields = table.field_names
    if output in ("-", None):
        output = sys.stdout.buffer
    else:
        output = open_compressed(output, mode="wb")
    output = generate_schema(table, export_fields, output_format)
    click.echo(output)


@cli.command(name="csv-to-sqlite", help="Convert one or more CSV files to SQLite")
@click.option("--batch-size", default=10000)
@click.option(
    "--samples",
    type=int,
    default=5000,
    help="Number of rows to determine the field types (0 = all)",
)
@click.option("--input-encoding", default=None)
@click.option("--dialect", default=None)
@click.option("--schemas", default=None)
@click.argument("sources", nargs=-1, required=True)
@click.argument("output", required=True)
def command_csv_to_sqlite(
    batch_size, samples, input_encoding, dialect, schemas, sources, output
):

    # TODO: add --quiet

    # TODO: detect input_encoding for all sources
    input_encoding = input_encoding or DEFAULT_INPUT_ENCODING

    inputs = [pathlib.Path(filename) for filename in sources]
    output = pathlib.Path(output)
    # TODO: if table_name is "2019" the final name will be "field_2019" - must
    #       be "table_2019"
    table_names = make_header([filename.name.split(".")[0] for filename in inputs])
    schemas = _get_schemas_for_inputs(schemas, inputs)

    for filename, table_name, schema in zip(inputs, table_names, schemas):
        prefix = "[{filename} -> {db_filename}#{tablename}]".format(
            db_filename=output.name, tablename=table_name, filename=filename.name
        )
        # TODO: if `schemas` is present, will not detect data types
        pre_prefix = "{} (detecting data types)".format(prefix)
        progress_bar = ProgressBar(prefix=prefix, pre_prefix=pre_prefix)
        csv_to_sqlite(
            six.text_type(filename),
            six.text_type(output),
            dialect=dialect,
            table_name=table_name,
            samples=samples,
            batch_size=batch_size,
            callback=progress_bar.update,
            encoding=input_encoding,
            schema=schema,
        )
        progress_bar.close()


@cli.command(name="sqlite-to-csv", help="Convert a SQLite table into CSV")
@click.option("--batch-size", default=10000)
@click.option("--dialect", default="excel")
@click.argument("source", required=True)
@click.argument("table_name", required=True)
@click.argument("output", required=True)
def command_sqlite_to_csv(batch_size, dialect, source, table_name, output):

    # TODO: add --quiet
    # TODO: add output options/encoding

    input_filename = pathlib.Path(source)
    output_filename = pathlib.Path(output)
    prefix = "[{db_filename}#{tablename} -> {filename}]".format(
        db_filename=input_filename.name,
        tablename=table_name,
        filename=output_filename.name,
    )
    progress_bar = ProgressBar(prefix=prefix, pre_prefix="")
    sqlite_to_csv(
        input_filename=six.text_type(input_filename),
        table_name=table_name,
        dialect=dialect,
        output_filename=six.text_type(output_filename),
        batch_size=batch_size,
        callback=progress_bar.update,
    )
    progress_bar.close()


@cli.command(name="pgimport", help="Import a CSV file into a PostgreSQL table")
@click.option("--input-encoding", default=None)
@click.option("--no-create-table", default=False, is_flag=True)
@click.option("--dialect", default=None)
@click.option("--schema", default=None)
@click.argument("source", required=True)
@click.argument("database_uri", required=True)
@click.argument("table_name", required=True)
def command_pgimport(
    input_encoding, no_create_table, dialect, schema, source, database_uri, table_name
):

    # TODO: add --quiet
    # TODO: may detect encoding here (instead of inside rows.utils.pgimport)

    # First, detect file size
    progress_bar = ProgressBar(
        prefix="Importing data", pre_prefix="Detecting file size", unit="bytes"
    )
    try:
        total_size = uncompressed_size(source)
    except (RuntimeError, ValueError):
        total_size = None
    else:
        progress_bar.total = total_size

    # Then, define its schema
    if schema:
        progress_bar.description = "Reading schema"
        schemas = _get_schemas_for_inputs(schema if schema else None, [source])
    else:
        progress_bar.description = "Detecting schema"
        schemas = [None]

    # So we can finally import it!
    import_meta = pgimport(
        filename=source,
        encoding=input_encoding,
        dialect=dialect,
        database_uri=database_uri,
        create_table=not no_create_table,
        table_name=table_name,
        callback=progress_bar.update,
        schema=schemas[0],
    )
    progress_bar.description = "{} rows imported".format(import_meta["rows_imported"])
    progress_bar.close()


@cli.command(name="pgexport", help="Export a PostgreSQL table into a CSV file")
@click.option("--is-query", default=False, is_flag=True)
@click.option("--output-encoding", default="utf-8")
@click.option("--dialect", default="excel")
@click.argument("database_uri", required=True)
@click.argument("table_name", required=True)
@click.argument("destination", required=True)
def command_pgexport(
    is_query, output_encoding, dialect, database_uri, table_name, destination
):
    # TODO: add --quiet

    updater = ProgressBar(prefix="Exporting data", unit="bytes")
    pgexport(
        database_uri=database_uri,
        table_name_or_query=table_name,
        is_query=is_query,
        filename=destination,
        encoding=output_encoding,
        dialect=dialect,
        callback=updater.update,
    )
    updater.close()


@cli.command(name="pdf-to-text", help="Extract text from a PDF")
@click.option("--input-option", "-i", multiple=True, help="Custom (import) plugin key=value custom option (can be specified multiple times)")
@click.option("--output-encoding", default="utf-8")
@click.option("--quiet", "-q", is_flag=True)
@click.option("--backend", default=None)
@click.option("--pages")
@click.argument("source", required=True)
@click.argument("output", required=False)
def command_pdf_to_text(input_option, output_encoding, quiet, backend, pages, source, output):

    input_options = parse_options(input_option)
    input_options["backend"] = backend or input_options.get("backend", None)

    # Define page range
    input_options["page_numbers"] = pages or input_options.get("page_numbers", None)
    if input_options["page_numbers"]:
        input_options["page_numbers"] = rows.plugins.pdf.extract_intervals(input_options["page_numbers"])

    # Define if output is file or stdout
    if output:
        output = open_compressed(output, mode="w", encoding=output_encoding)
        write = output.write
    else:
        write = click.echo
        quiet = True
    progress = not quiet

    # Download the file if source is an HTTP URL
    downloaded = False
    if source.lower().startswith("http:") or source.lower().startswith("https:"):
        result = download_file(source, progress=progress, detect=False)
        source = result.uri
        downloaded = True

    reader = rows.plugins.pdf.pdf_to_text(source, **input_options)
    if progress:  # Calculate total number of pages and create a progress bar
        if input_options["page_numbers"]:
            total_pages = len(input_options["page_numbers"])
        else:
            total_pages = rows.plugins.pdf.number_of_pages(source, backend=input_options["backend"])
        reader = tqdm(reader, desc="Extracting text", total=total_pages)

    for page in reader:
        write(page)

    if output:
        output.close()
    if downloaded:
        os.unlink(source)


@cli.command(name="csv-merge", help="Lazily merge CSVs (even if the schemas differs)")
@click.option("--input-encoding", default=None)
@click.option("--output-encoding", default="utf-8")
@click.option("--no-strip", is_flag=True)
@click.option("--no-remove-empty-lines", is_flag=True)
@click.argument("sources", nargs=-1, required=True)
@click.argument("destination")
def csv_merge(input_encoding, output_encoding, no_strip, no_remove_empty_lines, sources, destination):

    # TODO: add option to preserve original key names
    # TODO: detect input_encoding for all sources
    # TODO: add input option for sample_size
    # TODO: add --quiet

    strip = not no_strip
    remove_empty_lines = not no_remove_empty_lines

    input_encoding = input_encoding or DEFAULT_INPUT_ENCODING
    sample_size = 1024 * 1024
    dialects, keys, keys_per_file = {}, [], defaultdict(dict)
    for filename in tqdm(sources, desc="Detecting dialects and headers"):
        # Detect dialect
        fobj = open_compressed(filename, mode="rb")
        sample = fobj.read(sample_size)
        fobj.close()
        dialect = rows.plugins.csv.discover_dialect(sample, input_encoding)
        dialects[filename] = dialect

        # Get header
        fobj = open_compressed(filename, encoding=input_encoding)
        reader = csv.DictReader(fobj, dialect=dialect)
        for field_name in reader.fieldnames:
            field_name_slug = rows.fields.slug(field_name)
            keys_per_file[filename][field_name_slug] = field_name
            if field_name_slug not in keys:
                keys.append(field_name_slug)
        fobj.close()
    # TODO: is it needed to use make_header here?

    output_fobj = open_compressed(destination, mode="w", encoding=output_encoding)
    writer = csv.DictWriter(output_fobj, fieldnames=keys)
    writer.writeheader()
    progress_bar = tqdm(desc="Exporting data")
    for index, filename in enumerate(sources):
        progress_bar.desc = "Exporting data {}/{}".format(index + 1, len(sources))
        field_names = keys_per_file[filename]
        fobj = open_compressed(filename, encoding=input_encoding)
        reader = csv.DictReader(fobj, dialect=dialects[filename])
        if strip:
            for row in reader:
                new_row = {
                    key: (row[field_names[key]] or "").strip() if key in field_names else ""
                    for key in keys
                }
                if remove_empty_lines and not any(new_row.values()):
                    continue
                writer.writerow(new_row)
                progress_bar.update()
        else:
            for row in reader:
                new_row = {
                    key: (row[field_names[key]] or "") if key in field_names else ""
                    for key in keys
                }
                if remove_empty_lines and not any(new_row.values()):
                    continue
                writer.writerow(new_row)
                progress_bar.update()
        fobj.close()
    output_fobj.close()


if __name__ == "__main__":
    cli()
