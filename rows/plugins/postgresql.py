# coding: utf-8

# Copyright 2014-2020 Álvaro Justen <https://github.com/turicas/rows/>

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

from __future__ import unicode_literals

import csv
import io
import itertools
import string
import subprocess
from pathlib import Path

import six
from psycopg2 import connect as pgconnect

import rows.fields as fields
from rows.plugins.plugin_csv import discover_dialect
from rows.plugins.utils import create_table, ipartition, prepare_to_export
from rows.utils import Source, detect_local_source, execute_command, open_compressed

POSTGRESQL_TYPES = {
    fields.BinaryField: "BYTEA",
    fields.BoolField: "BOOLEAN",
    fields.DateField: "DATE",
    fields.DatetimeField: "TIMESTAMP(0) WITHOUT TIME ZONE",
    fields.DecimalField: "NUMERIC",
    fields.FloatField: "REAL",
    fields.IntegerField: "BIGINT",  # TODO: detect when it's really needed
    fields.JSONField: "JSONB",
    fields.PercentField: "REAL",
    fields.TextField: "TEXT",
    fields.UUIDField: "UUID",
}
DEFAULT_POSTGRESQL_TYPE = "BYTEA"
SQL_TABLE_NAMES = """
    SELECT
        tablename
    FROM pg_tables
    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
"""
SQL_CREATE_TABLE = (
    "CREATE {pre_table}TABLE{post_table} " '"{table_name}" ({field_types}){post_fields}'
)
SQL_SELECT_ALL = 'SELECT * FROM "{table_name}"'
SQL_INSERT = 'INSERT INTO "{table_name}" ({field_names}) ' "VALUES ({placeholders})"
DEFAULT_TYPE = "BYTEA"


def get_psql_command(
    command,
    user=None,
    password=None,
    host=None,
    port=None,
    database_name=None,
    database_uri=None,
):

    if database_uri is None:
        if None in (user, password, host, port, database_name):
            raise ValueError(
                "Need to specify either `database_uri` or the complete information"
            )

        database_uri = "postgres://{user}:{password}@{host}:{port}/{name}".format(
            user=user, password=password, host=host, port=port, name=database_name
        )

    return ["psql", "--no-psqlrc", "-c", command, database_uri]


def get_psql_copy_command(
    table_name_or_query,
    header,
    encoding="utf-8",
    user=None,
    password=None,
    host=None,
    port=None,
    database_name=None,
    database_uri=None,
    is_query=False,
    dialect=csv.excel,
    direction="FROM",
    skip_header=False,
):

    direction = direction.upper()
    if direction not in ("FROM", "TO"):
        raise ValueError('`direction` must be "FROM" or "TO"')

    if not is_query:  # Table name
        source = table_name_or_query
    else:
        source = "(" + table_name_or_query + ")"
    if header is None:
        header = ""
    else:
        header = ", ".join(f'"{field_name}"' for field_name in header)
        header = "({header}) ".format(header=header)
    copy = (
        r"\copy {source} {header}{direction} STDIN WITH("
        "DELIMITER '{delimiter}', "
        "QUOTE '{quote}', "
    )
    if direction == "FROM":
        copy += "FORCE_NULL {header}, "
    copy += "ENCODING '{encoding}', "
    copy += "FORMAT CSV{});".format(", HEADER" if not skip_header else "")

    copy_command = copy.format(
        source=source,
        header=header,
        direction=direction,
        delimiter=dialect.delimiter.replace("'", "''"),
        quote=dialect.quotechar.replace("'", "''"),
        encoding=encoding,
    )

    return get_psql_command(
        copy_command,
        user=user,
        password=password,
        host=host,
        port=port,
        database_name=database_name,
        database_uri=database_uri,
    )


def pg_create_table_sql(schema, table_name, unlogged=False, access_method=None):
    field_names = list(schema.keys())
    field_types = list(schema.values())

    columns = [
        '"{}" {}'.format(name, POSTGRESQL_TYPES.get(type_, DEFAULT_POSTGRESQL_TYPE))
        for name, type_ in zip(field_names, field_types)
    ]
    return SQL_CREATE_TABLE.format(
        pre_table="" if not unlogged else "UNLOGGED ",
        post_table=" IF NOT EXISTS",
        table_name=table_name,
        field_types=", ".join(columns),
        post_fields=" USING {}".format(access_method)
        if access_method is not None
        else "",
    )


def pg_execute_psql(database_uri, sql):
    return execute_command(get_psql_command(sql, database_uri=database_uri))


def _python_to_postgresql(field_types):
    def convert_value(field_type, value):
        if field_type in (
            fields.BinaryField,
            fields.BoolField,
            fields.DateField,
            fields.DatetimeField,
            fields.DecimalField,
            fields.FloatField,
            fields.IntegerField,
            fields.PercentField,
            fields.TextField,
            fields.JSONField,
        ):
            return value

        else:  # don't know this field
            return field_type.serialize(value)

    def convert_row(row):
        return [
            convert_value(field_type, value)
            for field_type, value in zip(field_types, row)
        ]

    return convert_row


def get_source(connection_or_uri):

    if isinstance(connection_or_uri, (six.binary_type, six.text_type)):
        connection = pgconnect(connection_or_uri)
        uri = connection_or_uri
        input_is_uri = should_close = True
    else:  # already a connection
        connection = connection_or_uri
        uri = None
        input_is_uri = should_close = False

    # TODO: may improve Source for non-fobj cases (when open() is not needed)
    source = Source.from_file(
        connection,
        plugin_name="postgresql",
        mode=None,
        is_file=False,
        local=False,
        should_close=should_close,
    )
    source.uri = uri if input_is_uri else None

    return source


def _valid_table_name(name):
    """Verify if a given table name is valid for `rows`

    Rules:
    - Should start with a letter or '_'
    - Letters can be capitalized or not
    - Accepts letters, numbers and _
    """

    if name[0] not in "_" + string.ascii_letters or not set(name).issubset(
        "_" + string.ascii_letters + string.digits
    ):
        return False

    else:
        return True


def import_from_postgresql(
    connection_or_uri,
    table_name="table1",
    query=None,
    query_args=None,
    close_connection=None,
    *args,
    **kwargs,
):

    if query is None:
        if not _valid_table_name(table_name):
            raise ValueError("Invalid table name: {}".format(table_name))

        query = SQL_SELECT_ALL.format(table_name=table_name)

    if query_args is None:
        query_args = tuple()

    source = get_source(connection_or_uri)
    connection = source.fobj

    cursor = connection.cursor()
    cursor.execute(query, query_args)
    table_rows = list(cursor.fetchall())  # TODO: make it lazy
    header = [six.text_type(info[0]) for info in cursor.description]
    cursor.close()
    connection.commit()  # WHY?

    meta = {"imported_from": "postgresql", "source": source}
    if close_connection or (close_connection is None and source.should_close):
        connection.close()
    return create_table([header] + table_rows, meta=meta, *args, **kwargs)


def export_to_postgresql(
    table,
    connection_or_uri,
    table_name=None,
    table_name_format="table{index}",
    batch_size=100,
    close_connection=None,
    *args,
    **kwargs,
):
    # TODO: should add transaction support?

    if table_name is not None and not _valid_table_name(table_name):
        raise ValueError("Invalid table name: {}".format(table_name))

    source = get_source(connection_or_uri)
    connection = source.fobj
    cursor = connection.cursor()
    if table_name is None:
        cursor.execute(SQL_TABLE_NAMES)
        table_names = [item[0] for item in cursor.fetchall()]
        table_name = fields.make_unique_name(
            table.name,
            existing_names=table_names,
            name_format=table_name_format,
            start=1,
        )

    prepared_table = prepare_to_export(table, *args, **kwargs)
    field_names = next(prepared_table)
    field_types = list(map(table.fields.get, field_names))
    # TODO: add option to table access method (columnar, for example)
    cursor.execute(pg_create_table_sql(table.fields, table_name))

    insert_sql = SQL_INSERT.format(
        table_name=table_name,
        field_names=", ".join(field_names),
        placeholders=", ".join("%s" for _ in field_names),
    )
    _convert_row = _python_to_postgresql(field_types)
    for batch in ipartition(prepared_table, batch_size):
        cursor.executemany(insert_sql, map(_convert_row, batch))

    connection.commit()
    cursor.close()
    if close_connection or (close_connection is None and source.should_close):
        connection.close()
    return connection, table_name


class PostgresCopy:
    """Import data from CSV into PostgreSQL using the fastest method

    Required: psql command
    """

    # TODO: implement export
    # TODO: add option to run parallel COPY processes
    # TODO: add logging to the process
    # TODO: detect when error ocurred and interrupt the process immediatly

    def __init__(self, database_uri, chunk_size=8388608, max_samples=10000):
        self.database_uri = database_uri
        self.chunk_size = chunk_size
        self.max_samples = max_samples

    def _convert_encoding(self, encoding):
        pg_encoding = encoding
        if pg_encoding in ("us-ascii", "ascii"):
            # TODO: convert all possible encodings
            pg_encoding = "SQL_ASCII"
        return pg_encoding

    def _import(
        self,
        fobj,
        encoding,
        dialect,
        field_names,
        table_name,
        skip_header=False,
        callback=None,
    ):
        # Prepare the `psql` command to be executed based on collected metadata
        command = get_psql_copy_command(
            database_uri=self.database_uri,
            dialect=dialect,
            direction="FROM",
            encoding=self._convert_encoding(encoding),
            header=field_names,
            table_name_or_query=table_name,
            is_query=False,
            skip_header=skip_header,
        )
        rows_imported, error = 0, None
        try:
            # TODO: use env instead of passing full database URI to
            # command-line? (other system users could see the process and its
            # parameters)
            # TODO: we may need to set other parameters explicitly (depending
            # on psqlrc's configs, the defaults could be changed)
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            data = fobj.read(self.chunk_size).replace(b"\x00", b"")
            total_written = 0
            while data != b"":
                written = process.stdin.write(data)
                total_written += written
                if callback:
                    callback(written, total_written)
                data = fobj.read(self.chunk_size).replace(b"\x00", b"")
            stdout, stderr = process.communicate()
            if stderr != b"":
                for line in stderr.splitlines():
                    if line.startswith(b"NOTICE:"):
                        continue
                    else:
                        raise RuntimeError(stderr.decode("utf-8"))
            rows_imported = None
            for line in stdout.splitlines():
                if line.startswith(b"COPY "):
                    rows_imported = int(line.replace(b"COPY ", b"").strip())
                    break

        except FileNotFoundError:
            fobj.close()
            raise

        except BrokenPipeError:
            fobj.close()
            raise RuntimeError(process.stderr.read().decode("utf-8"))

        else:
            fobj.close()
            return {"bytes_written": total_written, "rows_imported": rows_imported}

    def import_from_filename(
        self,
        filename,
        table_name,
        encoding=None,
        dialect=None,
        schema=None,
        skip_header=False,
        create_table=True,
        unlogged=False,
        access_method=None,
        callback=None,
    ):
        if encoding is None:
            fobj = open_compressed(filename, mode="rb")
            sample_bytes = fobj.read(self.chunk_size).replace(b"\x00", b"")
            fobj.close()
            source = detect_local_source(filename, sample_bytes)
            encoding = source.encoding

        fobj = open_compressed(filename, mode="r", encoding=encoding)
        sample = fobj.read(self.chunk_size).replace("\x00", "")
        fobj.close()

        if dialect is None:  # Detect dialect
            dialect = discover_dialect(sample.encode(encoding), encoding=encoding)
        elif isinstance(dialect, six.text_type):
            dialect = csv.get_dialect(dialect)
        # TODO: add `else` to check if `dialect` is instace of correct class

        if skip_header:
            field_names = list(schema.keys())
        else:
            reader = csv.reader(io.StringIO(sample), dialect=dialect)
            csv_field_names = [field_name for field_name in next(reader)]
            if schema is None:
                field_names = csv_field_names
            else:
                field_names = list(schema.keys())
                if not set(csv_field_names).issubset(set(field_names)):
                    raise ValueError(
                        "CSV field names are not a subset of schema field names"
                    )
                field_names = [
                    field for field in csv_field_names if field in field_names
                ]

        if create_table:
            # If we need to create the table, it creates based on schema
            # (automatically identified or forced), not on CSV directly (field
            # order will be schema's field order).
            if schema is None:
                schema = fields.detect_types(
                    csv_field_names, itertools.islice(reader, self.max_samples)
                )
            create_table_sql = pg_create_table_sql(
                schema,
                table_name,
                unlogged=unlogged,
                access_method=access_method,
            )
            # TODO: we may check if the server has support to the selected
            # access method with the following query:
            # `SELECT EXISTS(SELECT 1 FROM pg_catalog.pg_am WHERE amname = %s)`
            pg_execute_psql(self.database_uri, create_table_sql)

        fobj = open_compressed(filename, mode="rb")
        return self._import(
            fobj=fobj,
            encoding=encoding,
            dialect=dialect,
            field_names=field_names,
            table_name=table_name,
            skip_header=skip_header,
            callback=callback,
        )

    def import_from_fobj(
        self,
        fobj,
        table_name,
        encoding,
        dialect,
        schema,
        skip_header=False,
        create_table=True,
        unlogged=False,
        access_method=None,
        callback=None,
    ):
        if isinstance(dialect, six.text_type):
            dialect = csv.get_dialect(dialect)
        # TODO: add `else` to check if `dialect` is instace of correct class

        if create_table:
            # If we need to create the table, it creates based on schema, not
            # on CSV directly (field order will be schema's field order).
            pg_execute_psql(
                self.database_uri,
                pg_create_table_sql(
                    schema, table_name, unlogged=unlogged, access_method=access_method
                ),
            )

        # TODO: if reading from fobj, the schema must be in the same order as
        # the file

        # TODO: check if the file is open in binary mode

        return self._import(
            fobj=fobj,
            encoding=encoding,
            dialect=dialect,
            field_names=list(schema.keys()),
            table_name=table_name,
            skip_header=skip_header,
            callback=callback,
        )


def pgimport(
    filename_or_fobj,
    database_uri,
    table_name,
    encoding=None,
    dialect=None,
    schema=None,
    skip_header=False,
    chunk_size=8388608,
    max_samples=10000,
    create_table=True,
    unlogged=False,
    access_method=None,
    callback=None,
):
    """Import data from CSV into PostgreSQL using the fastest method

    Required: `psql` command installed.
    """

    # TODO: add warning if table already exists and create_table=True

    pgcopy = PostgresCopy(
        database_uri=database_uri,
        chunk_size=chunk_size,
        max_samples=max_samples,
    )

    if isinstance(filename_or_fobj, (six.binary_type, six.text_type, Path)):
        return pgcopy.import_from_filename(
            filename=filename_or_fobj,
            table_name=table_name,
            encoding=encoding,
            dialect=dialect,
            schema=schema,
            skip_header=skip_header,
            create_table=create_table,
            unlogged=unlogged,
            access_method=access_method,
            callback=callback,
        )
    else:
        # File-object, so some fields are required
        if schema is None or encoding is None or dialect is None:
            raise ValueError(
                "File-object pgimport requires schema, encoding and dialect"
            )
        return pgcopy.import_from_fobj(
            fobj=filename_or_fobj,
            table_name=table_name,
            encoding=encoding,
            dialect=dialect,
            schema=schema,
            skip_header=skip_header,
            create_table=create_table,
            unlogged=unlogged,
            access_method=access_method,
            callback=callback,
        )


def pgexport(
    database_uri,
    table_name_or_query,
    filename,
    encoding="utf-8",
    dialect=csv.excel,
    callback=None,
    is_query=False,
    chunk_size=8388608,
):
    """Export data from PostgreSQL into a CSV file using the fastest method

    Required: psql command
    """
    # TODO: integrate with PostgresCopy

    # TODO: add logging to the process
    if isinstance(dialect, six.text_type):
        dialect = csv.get_dialect(dialect)

    # Prepare the `psql` command to be executed to export data
    command = get_psql_copy_command(
        database_uri=database_uri,
        direction="TO",
        encoding=encoding,
        header=None,  # Needed when direction = 'TO'
        table_name_or_query=table_name_or_query,
        is_query=is_query,
        dialect=dialect,
    )
    fobj = open_compressed(filename, mode="wb")
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        total_written = 0
        data = process.stdout.read(chunk_size).replace(b"\x00", b"")
        while data != b"":
            written = fobj.write(data)
            total_written += written
            if callback:
                callback(written, total_written)
            data = process.stdout.read(chunk_size).replace(b"\x00", b"")
        stdout, stderr = process.communicate()
        if stderr != b"":
            raise RuntimeError(stderr.decode("utf-8"))

    except FileNotFoundError:
        fobj.close()
        raise

    except BrokenPipeError:
        fobj.close()
        raise RuntimeError(process.stderr.read().decode("utf-8"))

    else:
        fobj.close()
        return {"bytes_written": total_written}


# TODO: run `psql` with --filename=tempfile instead of -c (prevent other users
# seeing the query). only current user must be able to read the temp file
# TODO: run `psql` with env vars to pass connection info:
# - PGDATABASE, PGHOST, PGPORT, PGUSER and PGPASSFILE. only current user must
# be able to read the temp file on PGPASSFILE
# To securely set the file permissions, may use https://github.com/YakDriver/oschmod
