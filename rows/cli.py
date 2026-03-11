# coding: utf-8

# Copyright 2014-2025 Álvaro Justen <https://github.com/turicas/rows/>
#    This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
#    Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
#    any later version.
#    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
#    warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
#    more details.
#    You should have received a copy of the GNU Lesser General Public License along with this program.  If not, see
#    <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import os
import sys
from pathlib import Path

from rows.compat import DEFAULT_SAMPLE_ROWS, PYTHON_VERSION, TEXT_TYPE, library_installed
from rows.version import as_string as rows_version

# TODO: define exit codes
# TODO: move default options to base command
# TODO: may move all 'destination' to '--output'
# TODO: test this whole module
# TODO: add option to pass 'create_table' options in command-line (like force
#       fields)


if PYTHON_VERSION < (3, 0, 0):
    import warnings

    warnings.filterwarnings("ignore", message="Click detected the use of the unicode_literals", category=Warning)

import click

# TODO: move constants to compat?
DEFAULT_BUFFER_SIZE = 8 * 1024 * 1024
DEFAULT_INPUT_ENCODING = "utf-8"
DEFAULT_OUTPUT_ENCODING = "utf-8"
DEFAULT_SAMPLE_SIZE = 8 * 1024 * 1024
HOME_PATH = Path(os.path.expanduser("~"))
CACHE_PATH = HOME_PATH / ".cache" / "rows" / "http"
_SAMPLES_HELP = "Number of rows to determine the field types. 0 = none (all field types are set to 'text'), -1 = all rows (use with care - consumes a lot of memory)"


def parse_options(options):
    options_dict = {}
    for option in options:
        equal_position = option.find("=")
        if equal_position == -1:
            raise ValueError("Equal sign not found for {}".format(repr(option)))
        else:
            options_dict[option[:equal_position]] = option[equal_position + 1 :]
    return options_dict


_tqdm_available = library_installed("tqdm")


def _tqdm_if_available(*args, **kwargs):
    if _tqdm_available:
        from tqdm import tqdm

        return tqdm(*args, **kwargs)

    return args[0]  # Iterable


def _import_table(source, encoding, verify_ssl=True, progress=True, timeout=10, *args, **kwargs):
    from rows.utils import import_from_uri

    uri = source.uri if hasattr(source, "uri") else source
    try:
        table = import_from_uri(
            uri,
            default_encoding=DEFAULT_INPUT_ENCODING,
            verify_ssl=verify_ssl,
            encoding=encoding,
            progress=progress,
            *args,
            **kwargs
        )
    except Exception as exception:
        from rows.utils import response_exception_type

        exp_type = response_exception_type(exception)
        if exp_type is not None:
            if exp_type == "ssl":
                click.echo("ERROR: SSL verification failed! Use `--verify-ssl=no` if you want to ignore.", err=True)
            elif exp_type == "timeout":
                click.echo("ERROR: timeout! Use `--timeout=X` if you want to change.", err=True)
            sys.exit(2)
        raise
    else:
        return table


def _get_field_names(field_names, table_field_names, permit_not=False):
    from rows.fields import make_header

    new_field_names = make_header(field_names.split(","), permit_not=permit_not)
    if not permit_not:
        diff = set(new_field_names) - set(table_field_names)
    else:
        diff = set(field_name.replace("^", "") for field_name in new_field_names) - set(table_field_names)

    if diff:
        missing = ", ".join(['"{}"'.format(field) for field in diff])
        click.echo("Table does not have fields: {}".format(missing), err=True)
        sys.exit(1)
    else:
        return new_field_names


def _get_import_fields(fields, fields_exclude):
    from rows.fields import make_header

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
        return [field_name for field_name in table_field_names if field_name not in fields_exclude]
    else:
        return None


def _get_schemas_for_inputs(schemas, inputs):
    from rows.utils import load_schema

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
@click.option("--http-cache-path", default=TEXT_TYPE(CACHE_PATH.absolute()))
@click.version_option(version=rows_version, prog_name="rows")
def cli(http_cache, http_cache_path):
    if http_cache:
        import requests_cache

        http_cache_path = Path(http_cache_path).absolute()
        if not http_cache_path.parent.exists():
            os.makedirs(TEXT_TYPE(http_cache_path.parent), exist_ok=True)
        if TEXT_TYPE(http_cache_path).lower().endswith(".sqlite"):
            http_cache_path = Path(TEXT_TYPE(http_cache_path)[:-7]).absolute()

        requests_cache.install_cache(TEXT_TYPE(http_cache_path))


@cli.command(help="Convert table on `source` URI to `destination`")
@click.option("--input-encoding", default=None)
@click.option("--output-encoding", default="utf-8")
@click.option("--input-locale")
@click.option("--output-locale")
@click.option("--verify-ssl", type=bool, default=True)
@click.option("--timeout", type=int, default=10)
@click.option("--order-by")
@click.option("--fields", help="A comma-separated list of fields to import")
@click.option("--fields-exclude", help="A comma-separated list of fields to exclude")
@click.option("--samples", type=int, default=DEFAULT_SAMPLE_ROWS, help=_SAMPLES_HELP)
@click.option(
    "--input-option",
    "-i",
    multiple=True,
    help="Custom (import) plugin key=value custom option (can be specified multiple times)",
)
@click.option(
    "--output-option",
    "-o",
    multiple=True,
    help="Custom (export) plugin key=value custom option (can be specified multiple times)",
)
@click.option("--quiet", "-q", is_flag=True)
@click.argument("source")
@click.argument("destination")
def convert(
    input_encoding,
    output_encoding,
    input_locale,
    output_locale,
    verify_ssl,
    timeout,
    order_by,
    fields,
    fields_exclude,
    samples,
    input_option,
    output_option,
    quiet,
    source,
    destination,
):
    import rows
    from rows.utils import detect_source, export_to_uri

    input_options = parse_options(input_option)
    output_options = parse_options(output_option)
    progress = not quiet and _tqdm_available

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
                timeout=timeout,
                import_fields=import_fields,
                progress=progress,
                samples=samples,
                mode="stream" if order_by is None else "eager",
                **input_options
            )
    else:
        table = _import_table(
            source_info or source,
            encoding=input_encoding,
            verify_ssl=verify_ssl,
            timeout=timeout,
            import_fields=import_fields,
            progress=progress,
            samples=samples,
            mode="stream" if order_by is None else "eager",
            **input_options
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
            export_to_uri(table, destination, encoding=output_encoding, export_fields=export_fields, **output_options)
    else:
        export_to_uri(table, destination, encoding=output_encoding, export_fields=export_fields, **output_options)


@cli.command(help="Join tables from `source` URIs using `key(s)` to group " "rows and save into `destination`")
@click.option("--quiet", "-q", is_flag=True)
@click.option("--input-encoding", default=None)
@click.option("--output-encoding", default="utf-8")
@click.option("--input-locale")
@click.option("--output-locale")
@click.option("--verify-ssl", type=bool, default=True)
@click.option("--timeout", type=int, default=10)
@click.option("--order-by")
@click.option("--fields", help="A comma-separated list of fields to export")
@click.option(
    "--fields-exclude",
    help="A comma-separated list of fields to exclude when exporting",
)
@click.option("--samples", type=int, default=DEFAULT_SAMPLE_ROWS, help=_SAMPLES_HELP)
@click.argument("keys")
@click.argument("sources", nargs=-1, required=True)
@click.argument("destination")
def join(
    quiet,
    input_encoding,
    output_encoding,
    input_locale,
    output_locale,
    verify_ssl,
    timeout,
    order_by,
    fields,
    fields_exclude,
    samples,
    keys,
    sources,
    destination,
):
    import rows
    from rows.fields import make_header
    from rows.utils import export_to_uri

    # TODO: detect input_encoding for all sources
    input_encoding = input_encoding or DEFAULT_INPUT_ENCODING
    progress = not quiet and _tqdm_available

    export_fields = _get_import_fields(fields, fields_exclude)
    keys = make_header(keys.split(","), permit_not=False)

    if input_locale is not None:
        with rows.locale_context(input_locale):
            tables = [
                _import_table(
                    source,
                    encoding=input_encoding,
                    verify_ssl=verify_ssl,
                    timeout=timeout,
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
                timeout=timeout,
                samples=samples,
                progress=progress,
            )
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
        export_to_uri(result, destination, encoding=output_encoding, export_fields=export_fields)


@cli.command(name="sum", help="Sum tables from `source` URIs and save into `destination`")
@click.option("--quiet", "-q", is_flag=True)
@click.option("--input-encoding", default=None)
@click.option("--output-encoding", default="utf-8")
@click.option("--input-locale")
@click.option("--output-locale")
@click.option("--verify-ssl", type=bool, default=True)
@click.option("--timeout", type=int, default=10)
@click.option("--order-by")
@click.option("--fields", help="A comma-separated list of fields to import")
@click.option("--fields-exclude", help="A comma-separated list of fields to exclude")
@click.option("--samples", type=int, default=DEFAULT_SAMPLE_ROWS, help=_SAMPLES_HELP)
@click.argument("sources", nargs=-1, required=True)
@click.argument("destination")
def sum_(
    quiet,
    input_encoding,
    output_encoding,
    input_locale,
    output_locale,
    verify_ssl,
    timeout,
    order_by,
    fields,
    fields_exclude,
    samples,
    sources,
    destination,
):
    import rows
    from rows.utils import export_to_uri

    # TODO: detect input_encoding for all sources
    input_encoding = input_encoding or DEFAULT_INPUT_ENCODING
    progress = not quiet and _tqdm_available

    import_fields = _get_import_fields(fields, fields_exclude)
    if input_locale is not None:
        with rows.locale_context(input_locale):
            tables = [
                _import_table(
                    source,
                    encoding=input_encoding,
                    verify_ssl=verify_ssl,
                    timeout=timeout,
                    import_fields=import_fields,
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
                timeout=timeout,
                import_fields=import_fields,
                samples=samples,
                progress=progress,
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
        export_to_uri(result, destination, encoding=output_encoding, export_fields=export_fields)


@cli.command(name="print", help="Print a table")
@click.option("--input-encoding", default=None)
@click.option("--output-encoding", default="utf-8")
@click.option("--input-locale")
@click.option(
    "--input-option",
    "-i",
    multiple=True,
    help="Custom (import) plugin key=value custom option (can be specified multiple times)",
)
@click.option("--output-locale")
@click.option("--frame-style", default="ascii", help="Options: ascii, single, double, none")
@click.option("--samples", type=int, default=DEFAULT_SAMPLE_ROWS, help=_SAMPLES_HELP)
@click.option("--table-index", default=0)
@click.option("--verify-ssl", type=bool, default=True)
@click.option("--timeout", type=int, default=10)
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
    samples,
    table_index,
    verify_ssl,
    timeout,
    fields,
    fields_exclude,
    order_by,
    quiet,
    source,
):
    import io

    import rows
    from rows.utils import detect_source

    input_options = parse_options(input_option)
    progress = not quiet and _tqdm_available
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
                timeout=timeout,
                index=table_index,
                import_fields=import_fields,
                samples=samples,
                progress=progress,
                **input_options
            )
    else:
        table = _import_table(
            source_info or source,
            encoding=input_encoding,
            verify_ssl=verify_ssl,
            timeout=timeout,
            index=table_index,
            import_fields=import_fields,
            samples=samples,
            progress=progress,
            **input_options
        )

    if order_by is not None:
        order_by = _get_field_names(order_by, table.field_names, permit_not=True)
        # TODO: use complete list of `order_by` fields
        table.order_by(order_by[0].replace("^", "-"))

    export_fields = _get_export_fields(table.field_names, fields_exclude)
    output_encoding = output_encoding or sys.stdout.encoding or DEFAULT_OUTPUT_ENCODING
    # TODO: may use output_options instead of custom TXT plugin options
    fobj = io.BytesIO()
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


def remove_sql_comments(query):
    """Strip inline and multiline comments from a SQL query using regular expressions"""
    import re

    REGEXP_SQL_MULTILINE_COMMENTS = re.compile(r"/\*.*?\*/", flags=re.MULTILINE | re.DOTALL)
    REGEXP_SQL_INLINE_COMMENT = re.compile(r"^\s*--.*?\n", flags=re.MULTILINE)

    return REGEXP_SQL_INLINE_COMMENT.sub("\n", REGEXP_SQL_MULTILINE_COMMENTS.sub("\n", query)).strip()


def is_select_query(text):
    """Check whether a text is a SQL SELECT query, after removing comments
    >>> is_select_query('SELECT * FROM foo')
    True
    >>> is_select_query('WITH a AS (SELECT * FROM foo) SELECT * FROM a')
    True
    >>> is_select_query('foo')
    False
    """
    clean_query = remove_sql_comments(text)
    first_word = clean_query.lower().split(" ", 1)[0].strip()
    # TODO: there will be cases where it starts with "WITH" but the main query is not "SELECT". Proper parsing will be
    # needed for those cases
    return first_word in ("select", "with")


def create_complete_query(query, table_names):
    """Return a complete SQL query - allows user to specify only the part after 'WHERE'
    >>> create_complete_query('SELECT * FROM foo', [])
    'SELECT * FROM foo'
    >>> create_complete_query('a > 10', ['foo'])
    'SELECT * FROM foo WHERE a > 10'
    """
    if is_select_query(query):
        return query
    return "SELECT * FROM {} WHERE {}".format(", ".join(table_names), query)


@cli.command(name="query", help="Query a table using SQL")
@click.option("--input-encoding", default=None)
@click.option("--output-encoding", default="utf-8")
@click.option("--input-locale")
@click.option("--output-locale")
@click.option("--verify-ssl", type=bool, default=True)
@click.option("--timeout", type=int, default=10)
@click.option("--samples", type=int, default=DEFAULT_SAMPLE_ROWS, help=_SAMPLES_HELP)
@click.option(
    "--input-option",
    "-i",
    multiple=True,
    help="Custom (import) plugin key=value custom option (can be specified multiple times)",
)
@click.option("--output")
@click.option("--frame-style", default="ascii", help="Options: ascii, single, double, none")
@click.option("--quiet", "-q", is_flag=True)
@click.argument("query", required=True)
@click.argument("sources", nargs=-1, required=True)
def query(
    input_encoding,
    output_encoding,
    input_locale,
    output_locale,
    verify_ssl,
    timeout,
    samples,
    input_option,
    output,
    frame_style,
    quiet,
    query,
    sources,
):
    import io
    import sqlite3

    import rows
    from rows.utils import detect_source, export_to_uri, import_from_source

    # TODO: support multiple input options
    # TODO: detect input_encoding for all sources
    input_encoding = input_encoding or DEFAULT_INPUT_ENCODING
    progress = not quiet and _tqdm_available

    table_names = ["table{}".format(index) for index in range(1, len(sources) + 1)]
    query = create_complete_query(query, table_names)

    if len(sources) == 1:
        source = detect_source(sources[0], verify_ssl=verify_ssl, progress=progress)

        if source.plugin_name in ("sqlite", "postgresql"):
            # TODO: add "queryable" as a plugin capability -- and if it's OK for using SQL
            # Optimization: query the db directly
            result = import_from_source(source, input_encoding, query=query, samples=samples, mode="stream")
        else:
            if input_locale is not None:
                with rows.locale_context(input_locale):
                    table = import_from_source(source, input_encoding, samples=samples, mode="stream")
            else:
                table = import_from_source(source, input_encoding, samples=samples, mode="stream")

            sqlite_connection = sqlite3.Connection(":memory:")
            rows.export_to_sqlite(table, sqlite_connection, table_name="table1")
            result = rows.import_from_sqlite(sqlite_connection, query=query, samples=samples, mode="stream")

    else:
        # TODO: if all sources are SQLite we can also optimize the import
        if input_locale is not None:
            with rows.locale_context(input_locale):
                tables = [
                    _import_table(
                        source,
                        encoding=input_encoding,
                        verify_ssl=verify_ssl,
                        timeout=timeout,
                        samples=samples,
                        mode="stream",
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
                    timeout=timeout,
                    samples=samples,
                    mode="stream",
                    progress=progress,
                )
                for source in sources
            ]

        sqlite_connection = sqlite3.Connection(":memory:")
        for index, table in enumerate(tables, start=1):
            rows.export_to_sqlite(table, sqlite_connection, table_name="table{}".format(index))

        result = rows.import_from_sqlite(sqlite_connection, query=query)

    # TODO: may use sys.stdout.encoding if output_file = '-'
    output_encoding = output_encoding or sys.stdout.encoding or DEFAULT_OUTPUT_ENCODING
    if output is None:
        fobj = io.BytesIO()
        if output_locale is not None:
            with rows.locale_context(output_locale):
                rows.export_to_txt(result, fobj, encoding=output_encoding, frame_style=frame_style)
        else:
            rows.export_to_txt(result, fobj, encoding=output_encoding, frame_style=frame_style)
        fobj.seek(0)
        click.echo(fobj.read())
    else:
        if output_locale is not None:
            with rows.locale_context(output_locale):
                export_to_uri(result, output, encoding=output_encoding)
        else:
            export_to_uri(result, output, encoding=output_encoding)


def parse_comma_separated(ctx, param, value):
    if not value:
        return []
    return [item.strip() for item in value.split(",")]


@cli.command(name="schema", help="Identifies table schema")
@click.option("--input-encoding", default=None)
@click.option("--input-locale")
@click.option("--verify-ssl", type=bool, default=True)
@click.option("--detect-all-types", is_flag=True)
@click.option("--align", "-a", is_flag=True, help="Reorder fields based on column alignment (saves space)")
@click.option(
    "--input-option",
    "-i",
    multiple=True,
    help="Custom (import) plugin key=value custom option (can be specified multiple times)",
)
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
@click.option("--samples", type=int, default=DEFAULT_SAMPLE_ROWS, help=_SAMPLES_HELP)
@click.option(
    "--max-choices",
    type=int,
    default=100,
    help="Maximum number of different values to treat a field as choices/enums. Use 0 to disable the creation of choices/enums",
)
@click.option(
    "--exclude-choices",
    callback=parse_comma_separated,
    help="Comma-separated list of field names to not consider as choices/enums. Example: field1,field2,field3",
)
@click.option("--quiet", "-q", is_flag=True)
@click.argument("source", required=True)
@click.argument("output", required=False, default="-")
def command_schema(
    input_encoding,
    input_locale,
    verify_ssl,
    detect_all_types,
    align,
    input_option,
    output_format,
    fields,
    fields_exclude,
    samples,
    max_choices,
    exclude_choices,
    quiet,
    source,
    output,
):
    from rows import fields as rows_fields
    from rows import locale_context
    from rows.fileio import cfopen
    from rows.utils import detect_source, generate_schema, import_from_source

    if not Path(source).exists():
        click.echo("ERROR: file '{}' not found.".format(source), err=True)
        sys.exit(3)

    field_names = fields
    fields = rows_fields

    input_options = parse_options(input_option)
    progress = not quiet and _tqdm_available
    source_info = detect_source(uri=source, verify_ssl=verify_ssl, progress=progress)
    input_encoding = input_encoding or input_options.get("encoding", None) or source_info.encoding

    import_fields = _get_import_fields(field_names, fields_exclude)

    if detect_all_types:
        field_types_names = [field_name for field_name in fields.__all__ if field_name not in ("Field", "FloatField")]
    else:
        field_types_names = [
            FieldClass.__name__
            for FieldClass in fields.DEFAULT_TYPES
            if FieldClass not in (fields.Field, fields.FloatField)
        ]
    field_types = [getattr(fields, field_name) for field_name in field_types_names]

    if input_locale is not None:
        with locale_context(input_locale):
            table = import_from_source(
                source_info,
                input_encoding,
                encoding=input_encoding,
                samples=samples,
                import_fields=import_fields,
                max_rows=samples,  # TODO: change according to the new samples behavior
                mode="eager",
                field_types=field_types,
                **input_options
            )
    else:
        table = import_from_source(
            source_info,
            input_encoding,
            encoding=input_encoding,
            samples=samples,
            import_fields=import_fields,
            max_rows=samples,  # TODO: change according to the new samples behavior
            mode="eager",
            field_types=field_types,
            **input_options
        )

    export_fields = _get_export_fields(table.field_names, fields_exclude)
    if export_fields is None:
        export_fields = table.field_names
    if output in ("-", None):
        output_fobj = sys.stdout.buffer
    else:
        output_fobj = cfopen(output, mode="wb")
    # TODO: check if all field names in `exclude_choices` actually exists on source dataset
    content = generate_schema(
        table, export_fields, output_format, max_choices=max_choices, exclude_choices=exclude_choices, align=align
    )
    output_fobj.write(content.encode("utf-8"))


@cli.command(name="csv-inspect", help="Identifies encoding, dialect and schema")
@click.option("--encoding", default=None)
@click.option("--dialect")
@click.option("--samples", type=int, default=DEFAULT_SAMPLE_ROWS, help=_SAMPLES_HELP)
@click.argument("source", required=True)
def csv_inspect(encoding, dialect, samples, source):
    import csv

    from rows.plugins import csv as rows_csv

    # TODO: change according to the new samples behavior
    inspector = rows_csv.CsvInspector(source, encoding=encoding, dialect=dialect, max_samples=samples)

    click.echo("encoding = {}".format(repr(inspector.encoding)))

    dialect = inspector.dialect
    quote_codes = {getattr(csv, item): item for item in dir(csv) if item.startswith("QUOTE_")}
    dialect_field_names = (
        "delimiter",
        "doublequote",
        "escapechar",
        "lineterminator",
        "quotechar",
        "quoting",
        "skipinitialspace",
        "strict",
    )
    for field_name in dialect_field_names:
        value = getattr(dialect, field_name, None)
        if field_name == "quoting":
            if value in quote_codes:
                value = "csv.{}".format(quote_codes[value])
        else:
            value = repr(value)
        click.echo("dialect.{} = {}".format(field_name, value))


@cli.command(name="csv-fix", help="Read a CSV file, merge down rows (if number of cols differ) and fix quotes")
@click.option("--log-filename")
@click.option(
    "--log-level", default="NONE", type=click.Choice(["NONE", "CRITICAL", "DEBUG", "ERROR", "FATAL", "INFO", "WARNING"])
)
@click.option("--input-dialect")
@click.option("--input-encoding")
@click.option("--output-encoding", default="utf-8")
@click.option("--output-dialect", default="excel")
@click.argument("input_filename")
@click.argument("output_filename")
def command_csv_fix(
    log_filename,
    log_level,
    input_dialect,
    input_encoding,
    output_encoding,
    output_dialect,
    input_filename,
    output_filename,
):
    import csv
    import io
    import logging

    from rows.fileio import cfopen
    from rows.plugins import csv as rows_csv

    inspector = rows_csv.CsvInspector(input_filename)
    input_encoding = input_encoding or inspector.encoding
    input_dialect = input_dialect or inspector.dialect

    if input_filename == "-":
        fobj_in = io.TextIOWrapper(sys.stdin.buffer, encoding=input_encoding)
    else:
        fobj_in = cfopen(input_filename, encoding=input_encoding)
    if output_filename == "-":
        fobj_out = io.TextIOWrapper(sys.stdout.buffer, encoding=output_encoding)
    else:
        fobj_out = cfopen(output_filename, mode="w", encoding=output_encoding)

    if log_level == "NONE":
        logger = None
    else:
        log_level = getattr(logging, log_level)
        config = {
            "format": "%(asctime)-15s [%(name)s] %(levelname)s: %(message)s",
            "level": log_level,
        }
        if log_filename:
            config["filename"] = log_filename
            if not Path(log_filename).parent.exists():
                Path(log_filename).parent.mkdir(parents=True)
        else:
            config["stream"] = sys.stdout
        logging.basicConfig(**config)
        logger = logging.getLogger("converter")
        logger.setLevel(log_level)

    reader = csv.reader(fobj_in, dialect=input_dialect)
    writer = csv.writer(fobj_out, dialect=output_dialect)
    reader = reader if logger is not None else _tqdm_if_available(reader, desc="Converting file")
    rows_csv.fix_file(reader, writer, logger=logger)


@cli.command(name="csv-to-sqlite", help="Convert one or more CSV files to SQLite")
@click.option("--batch-size", default=10000)
@click.option("--samples", type=int, default=DEFAULT_SAMPLE_ROWS, help=_SAMPLES_HELP)
@click.option("--input-encoding", default=None)
@click.option("--dialect", default=None)
@click.option("--schemas", default=None)
@click.argument("sources", nargs=-1, required=True)
@click.argument("output", required=True)
def command_csv_to_sqlite(batch_size, samples, input_encoding, dialect, schemas, sources, output):
    from rows.fields import make_header
    from rows.plugins import csv as rows_csv
    from rows.utils import ProgressBar, csv_to_sqlite

    # TODO: add --quiet
    # TODO: check if all filenames exist (if not, exit with error)

    inputs = [Path(filename) for filename in sources]
    output = Path(output)
    # TODO: implement schema=:text:, like in pgimport
    table_names = make_header([filename.name.split(".")[0] for filename in inputs], prefix="table_")
    schemas = _get_schemas_for_inputs(schemas, inputs)

    for filename, table_name, schema in zip(inputs, table_names, schemas):
        prefix = "[{filename} -> {db_filename}#{tablename}]".format(
            db_filename=output.name, tablename=table_name, filename=filename.name
        )
        # TODO: change according to the new samples behavior
        inspector = rows_csv.CsvInspector(
            TEXT_TYPE(filename), encoding=input_encoding, dialect=dialect, schema=schema, max_samples=samples
        )
        if not schema:
            pre_prefix = "{} (detecting schema)".format(prefix)
        else:
            pre_prefix = "{} (reading schema)".format(prefix)
        if _tqdm_available:
            progress_bar = ProgressBar(prefix=prefix, pre_prefix=pre_prefix)
            progress_bar_update = progress_bar.update
        else:

            def progress_bar_update(*args, **kwargs):
                pass

        csv_to_sqlite(
            TEXT_TYPE(filename),
            TEXT_TYPE(output),
            dialect=inspector.dialect,
            table_name=table_name,
            samples=samples,
            batch_size=batch_size,
            callback=progress_bar_update,
            encoding=inspector.encoding,
            schema=inspector.schema,
        )
        if _tqdm_available:
            progress_bar.close()


@cli.command(name="sqlite-to-csv", help="Convert a SQLite table into CSV")
@click.option("--batch-size", default=10000)
@click.option("--dialect", default="excel")
@click.argument("source", required=True)
@click.argument("table_name", required=True)
@click.argument("output", required=True)
def command_sqlite_to_csv(batch_size, dialect, source, table_name, output):
    from rows.utils import ProgressBar, sqlite_to_csv

    # TODO: add --quiet
    # TODO: add output options/encoding

    input_filename = Path(source)
    output_filename = Path(output)
    prefix = "[{db_filename}#{tablename} -> {filename}]".format(
        db_filename=input_filename.name,
        tablename=table_name,
        filename=output_filename.name,
    )
    if _tqdm_available:
        progress_bar = ProgressBar(prefix=prefix, pre_prefix="")
        progress_bar_update = progress_bar.update
    else:

        def progress_bar_update(*args, **kwargs):
            pass

    sqlite_to_csv(
        input_filename=TEXT_TYPE(input_filename),
        table_name=table_name,
        dialect=dialect,
        output_filename=TEXT_TYPE(output_filename),
        batch_size=batch_size,
        callback=progress_bar_update,
    )
    if _tqdm_available:
        progress_bar.close()


@cli.command(name="pgimport", help="Import a CSV file into a PostgreSQL table")
@click.option("--input-encoding", "-e", default=None)
@click.option("--no-create-table", "-C", default=False, is_flag=True)
@click.option("--no-header", "-H", default=False, is_flag=True)
@click.option("--skip-rows", "-S", type=int, default=0)
@click.option("--dialect", "-d", default=None)
@click.option("--schema", "-s", default=None)
@click.option("--original-field-names", "-o", is_flag=True)
@click.option("--unlogged", "-u", is_flag=True)
@click.option("--access-method", "-a")
@click.option(
    "--sample-size",
    type=int,
    default=DEFAULT_SAMPLE_SIZE,
    help="Number of bytes to read from CSV to define encoding, dialect and field types",
)
@click.argument("source", required=True)
@click.argument("database_uri", required=True)
@click.argument("table_name", required=True)
def command_pgimport(
    input_encoding,
    no_create_table,
    no_header,
    skip_rows,
    dialect,
    schema,
    original_field_names,
    unlogged,
    access_method,
    sample_size,
    source,
    database_uri,
    table_name,
):
    from rows.compat import ORDERED_DICT, PYTHON_VERSION
    from rows.fields import TextField, make_header
    from rows.plugins import csv as rows_csv
    from rows.utils import ProgressBar, pgimport, uncompressed_size

    if PYTHON_VERSION < (3, 0, 0):
        NotFoundError = OSError
    else:
        NotFoundError = FileNotFoundError

    # TODO: implement parameter to import CSVs with no header on the first line
    #       (if schema is not provided, must use field_1, field_2, ...)
    # TODO: add --quiet
    if schema and schema != ":text:" and not Path(schema).exists():
        click.echo("ERROR: file '{}' not found.".format(schema), err=True)
        sys.exit(3)
    elif not Path(source).exists():
        click.echo("ERROR: file '{}' not found.".format(source), err=True)
        sys.exit(3)
    elif no_header and schema is None:
        click.echo("ERROR: cannot import a file with no header and no schema.", err=True)
        sys.exit(5)

    # First, detect file size
    if _tqdm_available:

        class CustomProgressBar(ProgressBar):
            def update(self, *args, **kwargs):
                # TODO: update total when finish (total = n)?
                super().update(*args, **kwargs)
                if self.progress.total is not None and self.progress.n > self.progress.total:
                    # The total size reached a level above the detected one,
                    # probabaly an error on gzip (it has only 32 bits to store
                    # uncompressed size, so if uncompressed size is greater than
                    # 4GiB, it will have truncated data). If this happens, we
                    # update the total by adding a bit `1` to left of the original
                    # size (in bits). It may not be the correct uncompressed size
                    # (more than one bit could be truncated, so the process will
                    # repeat. For more details, see comments on
                    # `rows.utils.uncompressed_size`.
                    self.progress.total = (1 << self.bit_updates) ^ self.original_total
                    self.bit_updates += 1

        progress_bar = CustomProgressBar(prefix="Importing data", pre_prefix="Detecting file size", unit="bytes")
        progress_bar_update = progress_bar.update
    else:

        def progress_bar_update(*args, **kwargs):
            pass

    compressed_size = os.stat(source).st_size
    total_size = None
    try:
        total_size = uncompressed_size(source)
    except (NotFoundError, ValueError):
        total_size = compressed_size
    finally:
        if _tqdm_available:
            progress_bar.total = (
                total_size if total_size is not None and total_size > compressed_size else compressed_size
            )
            progress_bar.original_total = total_size
            progress_bar.bit_updates = 0

    inspector = rows_csv.CsvInspector(source, encoding=input_encoding, dialect=dialect, chunk_size=sample_size)
    input_encoding = input_encoding or inspector.encoding
    dialect = dialect or inspector.dialect

    # Then, define its schema
    schema = TEXT_TYPE(schema or "").strip()
    if schema:
        if _tqdm_available:
            progress_bar.description = "Reading schema"
        if schema == ":text:":
            schemas = [
                ORDERED_DICT(
                    [(field_name, TextField) for field_name in make_header(inspector.field_names, max_size=63)]
                )
            ]
            no_header = True
            skip_rows += 1
        else:
            schemas = _get_schemas_for_inputs(schema, [source])
    else:
        if _tqdm_available:
            progress_bar.description = "Detecting schema"
        schemas = [inspector.schema]
    _, schema = schema, schemas[0]

    if not original_field_names:
        header = make_header(schema.keys())
        schema = ORDERED_DICT(
            [(header_name, field_type) for (header_name, (_, field_type)) in zip(header, schema.items())]
        )

    # So we can finally import it!
    import_meta = pgimport(
        filename=source,
        encoding=input_encoding,
        dialect=dialect,
        has_header=not no_header,
        skip_rows=skip_rows,
        database_uri=database_uri,
        create_table=not no_create_table,
        table_name=table_name,
        schema=schema,
        unlogged=unlogged,
        access_method=access_method,
        callback=progress_bar_update,
    )
    if _tqdm_available:
        rows_imported = import_meta["rows_imported"]
        plural = ""
        if rows_imported is not None:
            plural = "s" if rows_imported != 1 else ""
        progress_bar.description = "{} row{} imported".format(rows_imported, plural)
        progress_bar.close()


@cli.command(
    name="pgexport",
    help=(
        "Export a PostgreSQL table into a (possibly compressed) CSV file. Arguments:\n\n"
        "DATABASE_URI: PostgreSQL database URI to connect to in the format `postgres://user:pass@host:port/dbname`.\n"
        "TABLE_NAME_OR_QUERY: Source of data to be exported. Can be a table, view, materialized view or a query.\n"
        "DESTINATION: Output CSV filename (for compression, use the compressed extension)."
    ),
)
@click.option(
    "--is-query", "-q", default=None, is_flag=True, help="(DEPRECATED) Flag TABLE_NAME_OR_QUERY as a query"
)  # TODO: remove (deprecated)
@click.option("--output-encoding", "-e", default="utf-8", help="Encoding for output CSV")
@click.option("--dialect", "-d", default="excel", help="Dialect for output CSV")
@click.option(
    "--quiet", is_flag=True, help="Do not show progress bar"
)  # TODO: add `-q` as a shortcut after removing `--is-query`
@click.argument("database_uri", required=True)
@click.argument("table_name_or_query", required=True)
@click.argument("destination", required=True)
def command_pgexport(is_query, output_encoding, dialect, quiet, database_uri, table_name_or_query, destination):
    import warnings

    from rows.utils import ProgressBar, pgexport

    if is_query is not None and not quiet:
        warnings.simplefilter("default", DeprecationWarning)
        warnings.warn(
            "'--is-query' is deprecated and will be removed in a future version. "
            "This setting is not needed anymore (rows will automatically detect if it's a query or table/view name).",
            DeprecationWarning,
        )

    if is_select_query(table_name_or_query):
        query = table_name_or_query  # Already a query
    else:
        query = '''SELECT * FROM "{}"'''.format(table_name_or_query)

    if _tqdm_available and not quiet:
        progress_bar = ProgressBar(prefix="Exporting data", unit="bytes")
        progress_bar_update = progress_bar.update
    else:

        def progress_bar_update(*args, **kwargs):
            pass

    pgexport(
        database_uri=database_uri,
        table_name_or_query=query,
        is_query=True,
        filename=destination,
        encoding=output_encoding,
        dialect=dialect,
        callback=progress_bar_update,
    )
    if _tqdm_available and not quiet:
        progress_bar.close()


@cli.command(name="pg2pg", help="Copy data from one PostgreSQL instance to another")
@click.option("-b", "--binary", default=False, is_flag=True)
@click.option("--chunk-size", default=8 * 1024 * 1024)
@click.option("-e", "--encoding", default="utf-8")
@click.option("--no-create-table", default=False, is_flag=True)
@click.argument("database_uri_from", required=True)
@click.argument("table_name_or_query_from", required=True)
@click.argument("database_uri_to", required=True)
@click.argument("table_name_to", required=True)
def command_pg2pg(
    binary,
    chunk_size,
    encoding,
    no_create_table,
    database_uri_from,
    table_name_or_query_from,
    database_uri_to,
    table_name_to,
):
    from rows.plugins import postgresql as rows_postgresql
    from rows.utils import ProgressBar

    if _tqdm_available:
        progress_bar = ProgressBar(prefix="Importing data", unit="bytes")
        progress_bar_update = progress_bar.update
    else:

        def progress_bar_update(*args, **kwargs):
            pass

    import_meta = rows_postgresql.pg2pg(
        database_uri_from=database_uri_from,
        database_uri_to=database_uri_to,
        table_name_from=table_name_or_query_from,
        table_name_to=table_name_to,
        chunk_size=chunk_size,
        callback=progress_bar_update,
        encoding=encoding,
        create_table=not no_create_table,
        binary=binary,
    )
    if _tqdm_available:
        rows_imported = import_meta["rows_imported"]
        plural = ""
        if rows_imported is not None:
            plural = "s" if rows_imported != 1 else ""
        progress_bar.description = "{} row{} imported".format(rows_imported, plural)
        progress_bar.close()


@cli.command(name="pdf-to-text", help="Extract text from a PDF")
@click.option("--verify-ssl", type=bool, default=True)
@click.option(
    "--input-option",
    "-i",
    multiple=True,
    help="Custom (import) plugin key=value custom option (can be specified multiple times)",
)
@click.option("--timeout", type=int, default=10)
@click.option("--output-encoding", default="utf-8")
@click.option("--quiet", "-q", is_flag=True)
@click.option("--backend", default=None)
@click.option("--pages")
@click.argument("source", required=True)
@click.argument("output", required=False)
def command_pdf_to_text(verify_ssl, timeout, input_option, output_encoding, quiet, backend, pages, source, output):
    from rows.fileio import cfopen
    from rows.plugins import pdf as rows_pdf
    from rows.utils import download_file

    if rows_pdf is None:
        click.echo("No PDF backends available - install rows[pdf]", err=True)
        sys.exit(3)

    input_options = parse_options(input_option)
    input_options["backend"] = backend or input_options.get("backend", None)

    # Define page range
    input_options["page_numbers"] = pages or input_options.get("page_numbers", None)
    if input_options["page_numbers"]:
        input_options["page_numbers"] = rows_pdf.extract_intervals(input_options["page_numbers"])

    # Define if output is file or stdout
    if output:
        output = cfopen(output, mode="w", encoding=output_encoding)
        write = output.write
    else:
        write = click.echo
        quiet = True
    progress = not quiet and _tqdm_available

    # Download the file if source is an HTTP URL
    downloaded = False
    if source.lower().startswith("http:") or source.lower().startswith("https:"):
        try:
            result = download_file(source, progress=progress, detect=False, verify_ssl=verify_ssl, timeout=timeout)
        except Exception as exception:
            from rows.utils import response_exception_type

            exp_type = response_exception_type(exception)
            if exp_type is not None:
                if exp_type == "ssl":
                    click.echo("ERROR: SSL verification failed! Use `--verify-ssl=no` if you want to ignore.", err=True)
                elif exp_type == "timeout":
                    click.echo("ERROR: timeout! Use `--timeout=X` if you want to change.", err=True)
                sys.exit(2)
            raise
        source = result.uri
        downloaded = True

    reader = rows_pdf.pdf_to_text(source, **input_options)
    if progress:  # Calculate total number of pages and create a progress bar
        if input_options["page_numbers"]:
            total_pages = len(input_options["page_numbers"])
        else:
            total_pages = rows_pdf.number_of_pages(source, backend=input_options["backend"])
        reader = _tqdm_if_available(reader, desc="Extracting text", total=total_pages)

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
@click.option("--sample-size", default=DEFAULT_SAMPLE_SIZE)
@click.option("--buffer-size", default=DEFAULT_BUFFER_SIZE)
@click.argument("sources", nargs=-1, required=True)
@click.argument("destination")
def csv_merge(
    input_encoding,
    output_encoding,
    no_strip,
    no_remove_empty_lines,
    sample_size,
    buffer_size,
    sources,
    destination,
):
    import csv
    from collections import defaultdict

    from rows.fields import make_header, slug
    from rows.fileio import cfopen
    from rows.plugins import csv as rows_csv

    # TODO: add option to preserve original key names
    # TODO: add --quiet

    strip = not no_strip
    remove_empty_lines = not no_remove_empty_lines

    metadata = defaultdict(dict)
    final_header = []
    for filename in _tqdm_if_available(sources, desc="Detecting dialects and headers"):
        inspector = rows_csv.CsvInspector(filename, chunk_size=sample_size, encoding=input_encoding)
        metadata[filename]["dialect"] = inspector.dialect

        # Get header
        # TODO: fix final header in case of empty field names (a command like
        # `rows csv-clean` would fix the problem if run before `csv-merge` for
        # each file).
        metadata[filename]["fobj"] = cfopen(filename, encoding=inspector.encoding, buffering=buffer_size)
        metadata[filename]["reader"] = csv.reader(metadata[filename]["fobj"], dialect=metadata[filename]["dialect"])
        metadata[filename]["header"] = make_header(next(metadata[filename]["reader"]))
        metadata[filename]["header_map"] = {}
        for field_name in metadata[filename]["header"]:
            field_name_slug = slug(field_name)
            metadata[filename]["header_map"][field_name_slug] = field_name
            if field_name_slug not in final_header:
                final_header.append(field_name_slug)
    # TODO: is it needed to use make_header here?

    progress_bar = _tqdm_if_available(desc="Exporting data") if _tqdm_available else None
    output_fobj = cfopen(destination, mode="w", encoding=output_encoding, buffering=buffer_size)
    writer = csv.writer(output_fobj)
    writer.writerow(final_header)
    for index, filename in enumerate(sources):
        if progress_bar is not None:
            progress_bar.desc = "Exporting data {}/{}".format(index + 1, len(sources))
        meta = metadata[filename]
        field_indexes = [
            meta["header"].index(field_name) if field_name in meta["header"] else None for field_name in final_header
        ]
        if strip:

            def create_new_row(row):
                return [row[index].strip() if index is not None else None for index in field_indexes]

        else:

            def create_new_row(row):
                return [row[index] if index is not None else None for index in field_indexes]

        for row in meta["reader"]:
            new_row = create_new_row(row)
            if remove_empty_lines and not any(new_row):
                continue
            writer.writerow(new_row)
            if progress_bar is not None:
                progress_bar.update()
        meta["fobj"].close()
    output_fobj.close()
    if progress_bar is not None:
        progress_bar.close()


@cli.command(name="csv-clean")
@click.option("--input-encoding", default=None)
@click.option("--output-encoding", default="utf-8")
@click.option("--sample-size", default=DEFAULT_SAMPLE_SIZE)
@click.option("--buffer-size", default=DEFAULT_BUFFER_SIZE)
@click.option("--in-place", is_flag=True)
@click.argument("source", required=True)
@click.argument("destination", required=False)
def csv_clean(
    input_encoding,
    output_encoding,
    sample_size,
    buffer_size,
    in_place,
    source,
    destination,
):
    """Create a consistent and clean version of a CSV file

    The tasks this command executes are:

    - Slugify column names
    - Rename columns with empty name to "field_N"
    - Remove empty rows
    - Remove empty columns
    - Output dialect: excel
    - Output encoding: UTF-8
    """
    import csv
    import tempfile

    from rows.fields import make_header
    from rows.fileio import cfopen
    from rows.plugins import csv as rows_csv

    # TODO: add option to preserve original key names
    # TODO: add --quiet
    # TODO: fix if destination is empty

    inspector = rows_csv.CsvInspector(source, chunk_size=sample_size, encoding=input_encoding)
    dialect = inspector.dialect
    header = make_header(inspector.field_names)
    input_encoding = input_encoding or inspector.encoding

    # Detect empty columns
    with cfopen(source, encoding=input_encoding, buffering=buffer_size) as fobj:
        reader = csv.reader(fobj, dialect=dialect)
        next(reader)  # Skip header
        empty_columns = list(header)
        for row in _tqdm_if_available(reader, desc="Detecting empty columns"):
            row = [value.strip() for value in row]
            if not any(row):  # Empty row
                continue
            for key, value in zip(header, row):
                if key in empty_columns and value:
                    empty_columns.remove(key)
            if not empty_columns:
                break
    if empty_columns:
        field_indexes = [header.index(field_name) for field_name in header if field_name not in empty_columns]

        def create_new_row(row):
            return [row[index].strip() for index in field_indexes]

    else:

        def create_new_row(row):
            return [value.strip() for value in row]

    if in_place:
        temp_path = Path(tempfile.mkdtemp())
        destination = temp_path / Path(source).name

    fobj = cfopen(source, encoding=input_encoding, buffering=buffer_size)
    reader = csv.reader(fobj, dialect=dialect)
    _ = next(reader)  # Skip header
    output_fobj = cfopen(destination, mode="w", encoding=output_encoding, buffering=buffer_size)
    writer = csv.writer(output_fobj, dialect=csv.excel)
    writer.writerow(create_new_row(header))
    for row in _tqdm_if_available(reader, desc="Converting file"):
        row = create_new_row(row)
        if not any(row):  # Empty row
            continue
        writer.writerow(row)
    fobj.close()
    output_fobj.close()

    if in_place:
        os.rename(TEXT_TYPE(destination.absolute()), source)
        os.rmdir(TEXT_TYPE(temp_path))


@cli.command(name="csv-row-count", help="Lazily count CSV rows")
@click.option("--input-encoding", default=None)
@click.option("--buffer-size", default=DEFAULT_BUFFER_SIZE)
@click.option("--dialect")
@click.option("--sample-size", default=DEFAULT_SAMPLE_SIZE)
@click.argument("source")
def csv_row_count(input_encoding, buffer_size, dialect, sample_size, source):
    import csv

    from rows.fileio import cfopen
    from rows.plugins import csv as rows_csv

    inspector = rows_csv.CsvInspector(source, chunk_size=sample_size, encoding=input_encoding)
    dialect = dialect or inspector.dialect
    input_encoding = input_encoding or inspector.encoding

    fobj = cfopen(source, encoding=input_encoding, buffering=buffer_size)
    reader = csv.reader(fobj, dialect=dialect)
    next(reader)  # Skip header
    count = sum(1 for _ in reader)
    fobj.close()

    click.echo(count)


@cli.command(name="csv-split")
@click.option("--input-encoding", default=None)
@click.option("--output-encoding", default="utf-8")
@click.option("--buffer-size", default=DEFAULT_BUFFER_SIZE)
@click.option("--quiet", "-q", is_flag=True)
@click.option(
    "--destination-pattern",
    default=None,
    help="Template name for destination files, like: `myfile-{part:03d}.csv`",
)
@click.argument("source")
@click.argument("lines", type=int)
def csv_split(
    input_encoding,
    output_encoding,
    buffer_size,
    quiet,
    destination_pattern,
    source,
    lines,
):
    """Split CSV into equal parts (by number of lines).

    Input and output files can be compressed.
    """
    import csv

    from rows.fileio import cfopen
    from rows.utils import COMPRESSED_EXTENSIONS

    input_encoding = input_encoding or DEFAULT_INPUT_ENCODING
    if destination_pattern is None:
        first_part, extension = source.rsplit(".", 1)
        if extension.lower() in COMPRESSED_EXTENSIONS:
            first_part, new_extension = first_part.rsplit(".", 1)
            extension = new_extension + "." + extension
        destination_pattern = first_part + "-{part:03d}." + extension

    part = 0
    output_fobj = None
    writer = None
    input_fobj = cfopen(source, encoding=input_encoding, buffering=buffer_size)
    reader = csv.reader(input_fobj)
    header = next(reader)
    if not quiet:
        reader = _tqdm_if_available(reader)
    for index, row in enumerate(reader):
        if index % lines == 0:
            if output_fobj is not None:
                output_fobj.close()
            part += 1
            output_fobj = cfopen(
                destination_pattern.format(part=part),
                mode="w",
                encoding=output_encoding,
                buffering=buffer_size,
            )
            writer = csv.writer(output_fobj)
            writer.writerow(header)
        writer.writerow(row)
    input_fobj.close()


@cli.command(name="list-sheets", help="List sheets")
@click.argument("source")
def list_sheets(source):
    import rows

    extension = source[source.rfind(".") + 1 :].lower()
    if extension not in ("xls", "xlsx", "ods"):
        # TODO: support for 'sheet_names' should be introspected from plugins
        click.echo("ERROR: file type '{}' not supported.".format(extension), err=True)
        sys.exit(30)
    elif extension not in dir(rows.plugins) or getattr(rows.plugins, extension) is None:
        click.echo("ERROR: extension '{}' not installed.".format(extension), err=True)
        sys.exit(30)

    sheet_names_function = getattr(getattr(rows.plugins, extension), "sheet_names")
    for sheet_name in sheet_names_function(source):
        click.echo(sheet_name)


_PREMISE_VALID_TYPES = frozenset([
    "test-count", "test-zero", "test-gt", "test-gte", "test-lt", "test-lte",
    "test-error", "info", "info-count",
])
_PREMISE_REQUIRED_FIELDS = ["id", "type", "title", "query", "expected"]
_PREMISE_STATUS_OK = "OK"
_PREMISE_STATUS_ERR = "ERR"
_PREMISE_STATUS_INFO = "INFO"
_PREMISE_DEFAULT_TIMEOUT = 60


def _premise_first_numeric_value(row):
    """Return the first numeric value found in a dict, or None.

    Handles int, float and Decimal (returned by psycopg2 for PostgreSQL
    numeric/decimal columns).
    """
    from decimal import Decimal

    for value in row.values():
        if isinstance(value, (int, float, Decimal)):
            return value
    return None


def _premise_execute_sql(connection, sql):
    """Execute a SQL query and return (header, rows). Always closes the cursor."""
    cursor = connection.cursor()
    try:
        cursor.execute(sql)
        header = [item[0] for item in cursor.description]
        return header, cursor.fetchall()
    finally:
        cursor.close()


def _premise_evaluate_result(check_type, row_data, expected_raw):
    """Given a result row and the test type, return (status, display_value)."""
    if check_type == "info":
        return _PREMISE_STATUS_INFO, row_data

    if check_type == "info-count":
        return _PREMISE_STATUS_INFO, row_data.get("count", row_data)

    if check_type == "test-zero":
        value = row_data.get("count")
        if value is None:
            return _PREMISE_STATUS_ERR, "No 'count' column in result"
        return (_PREMISE_STATUS_OK if value == 0 else _PREMISE_STATUS_ERR), value

    if check_type == "test-count":
        value = row_data.get("count")
        if value is None:
            return _PREMISE_STATUS_ERR, "No 'count' column in result"
        expected = int(expected_raw)
        return (_PREMISE_STATUS_OK if value == expected else _PREMISE_STATUS_ERR), value

    if check_type in ("test-gt", "test-gte", "test-lt", "test-lte"):
        value = _premise_first_numeric_value(row_data)
        if value is None:
            return _PREMISE_STATUS_ERR, "No numeric column in result"
        expected = float(expected_raw)
        comparisons = {
            "test-gt": value > expected,
            "test-gte": value >= expected,
            "test-lt": value < expected,
            "test-lte": value <= expected,
        }
        return (_PREMISE_STATUS_OK if comparisons[check_type] else _PREMISE_STATUS_ERR), value

    return _PREMISE_STATUS_ERR, "Unknown type: {}".format(check_type)


def _premise_run_test(connection, test):
    """Execute a single premise test and return a result dict."""
    import time

    import psycopg2

    check_type = test["type"].strip().lower()
    sql = test["query"].strip()
    result = {
        "id": test["id"],
        "type": check_type,
        "title": test["title"],
        "query": sql,
        "expected": test["expected"],
        "status": _PREMISE_STATUS_ERR,
        "result": "",
        "duration_ms": 0,
    }

    start = time.time()
    try:
        if check_type == "test-error":
            try:
                _premise_execute_sql(connection, sql)
                result["result"] = "Expected SQL error but query succeeded"
            except psycopg2.Error:
                result["status"] = _PREMISE_STATUS_OK
                result["result"] = "Query raised error as expected"
            return result

        header, rows_result = _premise_execute_sql(connection, sql)

        if len(rows_result) != 1:
            result["result"] = "Expected 1 row, got {}".format(len(rows_result))
            return result

        row_data = dict(zip(header, rows_result[0]))
        result["status"], result["result"] = _premise_evaluate_result(
            check_type, row_data, test["expected"],
        )

    except psycopg2.Error as exc:
        # A SQL error on a non-test-error query: the implicit transaction (autocommit mode) is already rolled back by
        # PostgreSQL, so the connection remains usable for subsequent tests.
        error_message = getattr(exc, "pgerror", None) or TEXT_TYPE(exc)
        result["status"] = _PREMISE_STATUS_ERR
        result["result"] = "SQL error: {}".format(error_message.strip())
    except Exception as exc:
        result["status"] = _PREMISE_STATUS_ERR
        result["result"] = "Error: {}".format(exc)
    finally:
        elapsed = time.time() - start
        result["duration_ms"] = round(elapsed * 1000, 1)

    return result


@cli.command(
    name="validate-premises",
    help=(
        "Validate data premises by running SQL queries from a CSV file against a PostgreSQL database.\n\n"
        "The CSV file must have columns: id, type, title, query, expected.\n\n"
        "Supported types: test-count, test-zero, test-gt, test-gte, test-lt, test-lte, test-error, info, info-count.\n\n"
        "Exit code is 1 if any test fails, 0 otherwise."
    ),
)
@click.option(
    "--timeout",
    type=int,
    default=_PREMISE_DEFAULT_TIMEOUT,
    help="Statement timeout in seconds (default: {})".format(_PREMISE_DEFAULT_TIMEOUT),
)
@click.option("--quiet", "-q", is_flag=True, help="Do not show progress bar")
@click.argument("csv_filename", required=True)
@click.argument("database_uri", required=False, default=None)
def command_validate_premises(timeout, quiet, csv_filename, database_uri):
    import csv
    from collections import Counter

    import psycopg2

    import rows as rows_lib
    from rows.fileio import cfopen

    if database_uri is None:
        database_uri = os.environ.get("DATABASE_URL")
    if not database_uri:
        click.echo("ERROR: database URI not provided and DATABASE_URL env var is not set.", err=True)
        sys.exit(1)
    if not Path(csv_filename).exists():
        click.echo("ERROR: file '{}' not found.".format(csv_filename), err=True)
        sys.exit(3)

    table = rows_lib.import_from_csv(csv_filename)
    missing = set(_PREMISE_REQUIRED_FIELDS) - set(table.field_names or [])
    if missing:
        click.echo("ERROR: missing columns in CSV: {}".format(sorted(missing)), err=True)
        sys.exit(1)
    tests = [row._asdict() for row in table]

    found_types = set(row["type"].strip().lower() for row in tests)
    invalid_types = found_types - _PREMISE_VALID_TYPES
    if invalid_types:
        click.echo("ERROR: unknown test types: {}".format(sorted(invalid_types)), err=True)
        click.echo("Valid types: {}".format(sorted(_PREMISE_VALID_TYPES)), err=True)
        sys.exit(1)

    connection = psycopg2.connect(database_uri)
    connection.autocommit = True
    cursor = connection.cursor()
    cursor.execute("SET statement_timeout TO %s", (timeout * 1000,))
    cursor.close()

    results = []
    progress = not quiet and _tqdm_available
    iterator = _tqdm_if_available(tests, desc="Running premises") if progress else tests
    try:
        for test in iterator:
            results.append(_premise_run_test(connection, test))
            if progress:
                counter = Counter(r["status"] for r in results)
                stats = {
                    "ok": counter.get(_PREMISE_STATUS_OK, 0),
                    "err": counter.get(_PREMISE_STATUS_ERR, 0),
                    "info": counter.get(_PREMISE_STATUS_INFO, 0),
                }
                iterator.set_postfix(**stats)
    except KeyboardInterrupt:
        click.echo("\nInterrupted by user.", err=True)
    finally:
        connection.close()

    if results:
        display_keys = ["status", "id", "title", "result", "expected", "duration_ms"]
        display_rows = [{key: row[key] for key in display_keys} for row in results]
        table = rows_lib.import_from_dicts(display_rows)
        click.echo("")
        click.echo(rows_lib.export_to_txt(table))

        counter = Counter(r["status"] for r in results)
        total = len(results)
        ok = counter.get(_PREMISE_STATUS_OK, 0)
        err = counter.get(_PREMISE_STATUS_ERR, 0)
        info = counter.get(_PREMISE_STATUS_INFO, 0)
        click.echo("")
        click.echo("Total: {} | OK: {} | ERR: {} | INFO: {}".format(total, ok, err, info))

        failed = [r for r in results if r["status"] == _PREMISE_STATUS_ERR]
        if failed:
            click.echo("")
            click.echo("Failed tests:")
            for r in failed:
                click.echo("  [{}] {}: got {}, expected {}".format(r["id"], r["title"], r["result"], r["expected"]))

        if any(r["status"] == _PREMISE_STATUS_ERR for r in results):
            sys.exit(1)


if __name__ == "__main__":
    cli()
