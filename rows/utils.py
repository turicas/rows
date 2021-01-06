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

import cgi
import csv
import gzip
import io
import itertools
import mimetypes
import os
import re
import shlex
import sqlite3
import subprocess
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from textwrap import dedent

import six

try:
    import requests
except ImportError:
    requests = None
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

import rows
from rows.plugins.utils import make_header, slug

try:
    import lzma
except ImportError:
    lzma = None
try:
    import bz2
except ImportError:
    bz2 = None

try:
    from urlparse import urlparse  # Python 2
except ImportError:
    from urllib.parse import urlparse  # Python 3

try:
    import magic
except (ImportError, TypeError):
    magic = None
else:
    if not hasattr(magic, "detect_from_content"):
        # This is not the file-magic library
        magic = None

if requests:
    chardet = requests.compat.chardet
else:
    chardet = None
try:
    import urllib3
except ImportError:
    from requests.packages import urllib3
else:
    try:
        urllib3.disable_warnings()
    except AttributeError:
        # old versions of urllib3 or requests
        pass


# TODO: should get this information from the plugins
COMPRESSED_EXTENSIONS = ("gz", "xz", "bz2")
TEXT_PLAIN = {
    "txt": "text/txt",
    "text": "text/txt",
    "csv": "text/csv",
    "json": "application/json",
}
OCTET_STREAM = {
    "microsoft ooxml": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "par archive data": "application/parquet",
}
FILE_EXTENSIONS = {
    "csv": "text/csv",
    "db": "application/x-sqlite3",
    "htm": "text/html",
    "html": "text/html",
    "json": "application/json",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "parquet": "application/parquet",
    "sqlite": "application/x-sqlite3",
    "text": "text/txt",
    "tsv": "text/csv",
    "txt": "text/txt",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}
MIME_TYPE_TO_PLUGIN_NAME = {
    "application/json": "json",
    "application/parquet": "parquet",
    "application/vnd.ms-excel": "xls",
    "application/vnd.oasis.opendocument.spreadsheet": "ods",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/x-sqlite3": "sqlite",
    "text/csv": "csv",
    "text/html": "html",
    "text/txt": "txt",
    "application/pdf": "pdf",
}
regexp_sizes = re.compile("([0-9,.]+ [a-zA-Z]+B)")
MULTIPLIERS = {"B": 1, "KiB": 1024, "MiB": 1024 ** 2, "GiB": 1024 ** 3}
POSTGRESQL_TYPES = {
    rows.fields.BinaryField: "BYTEA",
    rows.fields.BoolField: "BOOLEAN",
    rows.fields.DateField: "DATE",
    rows.fields.DatetimeField: "TIMESTAMP(0) WITHOUT TIME ZONE",
    rows.fields.DecimalField: "NUMERIC",
    rows.fields.FloatField: "REAL",
    rows.fields.IntegerField: "BIGINT",  # TODO: detect when it's really needed
    rows.fields.JSONField: "JSONB",
    rows.fields.PercentField: "REAL",
    rows.fields.TextField: "TEXT",
    rows.fields.UUIDField: "UUID",
}
DEFAULT_POSTGRESQL_TYPE = "BYTEA"
SQL_CREATE_TABLE = "CREATE {pre_table}TABLE{post_table} " '"{table_name}" ({field_types})'


class ProgressBar:
    def __init__(self, prefix, pre_prefix="", total=None, unit=" rows"):
        self.prefix = prefix
        self.progress = tqdm(
            desc=pre_prefix, total=total, unit=unit, unit_scale=True, dynamic_ncols=True
        )
        self.started = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def description(self):
        return self.progress.desc

    @description.setter
    def description(self, value):
        self.progress.desc = value
        self.progress.refresh()

    @property
    def total(self):
        return self.progress.total

    @total.setter
    def total(self, value):
        self.progress.total = value
        self.progress.refresh()

    def update(self, last_done=1, total_done=None):
        if not last_done and not total_done:
            raise ValueError("Either last_done or total_done must be specified")

        if not self.started:
            self.started = True
            self.progress.desc = self.prefix
            self.progress.unpause()

        if last_done:
            self.progress.n += last_done
        else:
            self.progress.n = total_done
        self.progress.refresh()

    def close(self):
        self.progress.close()


@dataclass
class Source(object):
    "Define a source to import a `rows.Table`"

    uri: (str, Path)
    plugin_name: str
    encoding: str
    fobj: object = None
    compressed: bool = None
    should_delete: bool = False
    should_close: bool = False
    is_file: bool = None
    local: bool = None

    @classmethod
    def from_file(
        cls,
        filename_or_fobj,
        plugin_name=None,
        encoding=None,
        mode="rb",
        compressed=None,
        should_delete=False,
        should_close=None,
        is_file=True,
        local=True,
    ):
        """Create a `Source` from a filename or fobj"""

        if isinstance(filename_or_fobj, Source):
            return filename_or_fobj

        elif isinstance(filename_or_fobj, (six.binary_type, six.text_type, Path)):
            fobj = open_compressed(filename_or_fobj, mode=mode)
            filename = filename_or_fobj
            should_close = True if should_close is None else should_close

        else:  # Don't know exactly what is, assume file-like object
            fobj = filename_or_fobj
            filename = getattr(fobj, "name", None)
            if not isinstance(
                filename, (six.binary_type, six.text_type)
            ):  # BytesIO object
                filename = None
            should_close = False if should_close is None else should_close

        if is_file and local and filename and not isinstance(filename, Path):
            filename = Path(filename)

        return Source(
            compressed=compressed,
            encoding=encoding,
            fobj=fobj,
            is_file=is_file,
            local=local,
            plugin_name=plugin_name,
            should_close=should_close,
            should_delete=should_delete,
            uri=filename,
        )


def plugin_name_by_uri(uri):
    "Return the plugin name based on the URI"

    # TODO: parse URIs like 'sqlite://' also
    # TODO: integrate this function with detect_source

    parsed = urlparse(uri)
    if parsed.scheme:
        if parsed.scheme == "sqlite":
            return "sqlite"
        elif parsed.scheme == "postgres":
            return "postgresql"

    basename = os.path.basename(parsed.path)
    if not basename.strip():
        raise RuntimeError("Could not identify file format.")

    extension = basename.split(".")[-1].lower()
    if extension in COMPRESSED_EXTENSIONS:
        extension = basename.split(".")[-2].lower()

    plugin_name = extension
    if extension in FILE_EXTENSIONS:
        plugin_name = MIME_TYPE_TO_PLUGIN_NAME[FILE_EXTENSIONS[plugin_name]]

    return plugin_name


def extension_by_source(source, mime_type):
    "Return the file extension used by this plugin"

    extension = source.plugin_name
    if extension:
        return extension

    if mime_type:
        return mime_type.split("/")[-1]


def normalize_mime_type(mime_type, mime_name, file_extension):

    file_extension = file_extension.lower() if file_extension else ""
    mime_name = mime_name.lower() if mime_name else ""
    mime_type = mime_type.lower() if mime_type else ""

    if mime_type == "text/plain" and file_extension in TEXT_PLAIN:
        return TEXT_PLAIN[file_extension]

    elif mime_type == "application/octet-stream" and mime_name in OCTET_STREAM:
        return OCTET_STREAM[mime_name]

    elif file_extension in FILE_EXTENSIONS:
        return FILE_EXTENSIONS[file_extension]

    else:
        return mime_type


def plugin_name_by_mime_type(mime_type, mime_name, file_extension):
    "Return the plugin name based on the MIME type"

    return MIME_TYPE_TO_PLUGIN_NAME.get(
        normalize_mime_type(mime_type, mime_name, file_extension), None
    )


def detect_local_source(path, content, mime_type=None, encoding=None):

    # TODO: may add sample_size

    filename = os.path.basename(path)
    parts = filename.split(".")
    extension = parts[-1].lower() if len(parts) > 1 else None
    if extension in COMPRESSED_EXTENSIONS:
        extension = parts[-2].lower() if len(parts) > 2 else None

    if magic is not None:
        detected = magic.detect_from_content(content)
        encoding = detected.encoding or encoding
        mime_name = detected.name
        mime_type = detected.mime_type or mime_type

    else:
        if chardet and not encoding:
            encoding = chardet.detect(content)["encoding"] or encoding
        mime_name = None
        mime_type = mime_type or mimetypes.guess_type(filename)[0]

    plugin_name = plugin_name_by_mime_type(mime_type, mime_name, extension)
    if encoding == "binary":
        encoding = None

    return Source(uri=path, plugin_name=plugin_name, encoding=encoding)


def local_file(path, sample_size=1048576):
    # TODO: may change sample_size
    if path.split(".")[-1].lower() in COMPRESSED_EXTENSIONS:
        compressed = True
        fobj = open_compressed(path, mode="rb")
        content = fobj.read(sample_size)
        fobj.close()
    else:
        compressed = False
        with open(path, "rb") as fobj:
            content = fobj.read(sample_size)

    source = detect_local_source(path, content, mime_type=None, encoding=None)

    return Source(
        uri=path,
        plugin_name=source.plugin_name,
        encoding=source.encoding,
        compressed=compressed,
        should_delete=False,
        is_file=True,
        local=True,
    )


def download_file(
    uri,
    filename=None,
    verify_ssl=True,
    timeout=5,
    progress=False,
    detect=False,
    chunk_size=8192,
    sample_size=1048576,
):

    # TODO: add ability to continue download
    response = requests.get(
        uri,
        verify=verify_ssl,
        timeout=timeout,
        stream=True,
        headers={"user-agent": "rows-{}".format(rows.__version__)},
    )
    if not response.ok:
        raise RuntimeError("HTTP response: {}".format(response.status_code))

    # Get data from headers (if available) to help plugin + encoding detection
    real_filename, encoding, mime_type = uri, None, None
    headers = response.headers
    if "content-type" in headers:
        mime_type, options = cgi.parse_header(headers["content-type"])
        encoding = options.get("charset", encoding)
    if "content-disposition" in headers:
        _, options = cgi.parse_header(headers["content-disposition"])
        real_filename = options.get("filename", real_filename)

    if progress:
        total = response.headers.get("content-length", None)
        total = int(total) if total else None
        progress_bar = ProgressBar(prefix="Downloading file", total=total, unit="bytes")
    if filename is None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        fobj = open_compressed(tmp.name, mode="wb")
    else:
        fobj = open_compressed(filename, mode="wb")
    sample_data = b""
    for data in response.iter_content(chunk_size=chunk_size):
        fobj.write(data)
        if detect and len(sample_data) <= sample_size:
            sample_data += data
        if progress:
            progress_bar.update(len(data))
    fobj.close()
    if progress:
        progress_bar.close()

    # Detect file type and rename temporary file to have the correct extension
    if detect:
        # TODO: check if will work for compressed files
        source = detect_local_source(real_filename, sample_data, mime_type, encoding)
        extension = extension_by_source(source, mime_type)
        plugin_name = source.plugin_name
        encoding = source.encoding
    else:
        extension, plugin_name, encoding = None, None, None
        if mime_type:
            extension = mime_type.split("/")[-1]

    if filename is None:
        filename = tmp.name
        if extension:
            filename += "." + extension
        os.rename(tmp.name, filename)

    return Source(
        uri=filename,
        plugin_name=plugin_name,
        encoding=encoding,
        should_delete=True,
        is_file=True,
        local=False,
    )


def detect_source(uri, verify_ssl, progress, timeout=5):
    """Return a `rows.Source` with information for a given URI

    If URI starts with "http" or "https" the file will be downloaded.

    This function should only be used if the URI already exists because it's
    going to download/open the file to detect its encoding and MIME type.
    """

    # TODO: should also supporte other schemes, like file://, sqlite:// etc.

    if uri.lower().startswith("http://") or uri.lower().startswith("https://"):
        return download_file(
            uri, verify_ssl=verify_ssl, timeout=timeout, progress=progress, detect=True
        )

    elif uri.startswith("postgres://"):
        return Source(
            should_delete=False,
            encoding=None,
            plugin_name="postgresql",
            uri=uri,
            is_file=False,
            local=None,
        )
    else:
        return local_file(uri)


def import_from_source(source, default_encoding, *args, **kwargs):
    "Import data described in a `rows.Source` into a `rows.Table`"

    # TODO: test open_compressed
    plugin_name = source.plugin_name
    kwargs["encoding"] = (
        kwargs.get("encoding", None) or source.encoding or default_encoding
    )

    try:
        import_function = getattr(rows, "import_from_{}".format(plugin_name))
    except AttributeError:
        raise ValueError('Plugin (import) "{}" not found'.format(plugin_name))

    table = import_function(source.uri, *args, **kwargs)

    return table


def import_from_uri(
    uri, default_encoding="utf-8", verify_ssl=True, progress=False, *args, **kwargs
):
    "Given an URI, detects plugin and encoding and imports into a `rows.Table`"

    # TODO: support '-' also
    # TODO: (optimization) if `kwargs.get('encoding', None) is not None` we can
    #       skip encoding detection.
    source = detect_source(uri, verify_ssl=verify_ssl, progress=progress)
    return import_from_source(source, default_encoding, *args, **kwargs)


def export_to_uri(table, uri, *args, **kwargs):
    "Given a `rows.Table` and an URI, detects plugin (from URI) and exports"

    # TODO: support '-' also
    plugin_name = plugin_name_by_uri(uri)

    try:
        export_function = getattr(rows, "export_to_{}".format(plugin_name))
    except AttributeError:
        raise ValueError('Plugin (export) "{}" not found'.format(plugin_name))

    return export_function(table, uri, *args, **kwargs)


def open_compressed(
    filename,
    mode="r",
    buffering=-1,
    encoding=None,
    errors=None,
    newline=None,
    closefd=True,
    opener=None,
):
    """Return a text-based file object from a filename, even if compressed

    NOTE: if the file is compressed, options like `buffering` are valid to the
    compressed file-object (not the uncompressed file-object returned).
    """

    binary_mode = "b" in mode
    if not binary_mode and "t" not in mode:
        # For some reason, passing only mode='r' to bzip2 is equivalent
        # to 'rb', not 'rt', so we force it here.
        mode += "t"
    if binary_mode and encoding:
        raise ValueError("encoding should not be specified in binary mode")

    extension = str(filename).split(".")[-1].lower()
    mode_binary = mode.replace("t", "b")
    get_fobj_binary = lambda: open(
        filename,
        mode=mode_binary,
        buffering=buffering,
        errors=errors,
        newline=newline,
        closefd=closefd,
        opener=opener,
    )
    get_fobj_text = lambda: open(
        filename,
        mode=mode,
        buffering=buffering,
        encoding=encoding,
        errors=errors,
        newline=newline,
        closefd=closefd,
        opener=opener,
    )
    known_extensions = ("xz", "gz", "bz2")

    if extension not in known_extensions:  # No compression
        if binary_mode:
            return get_fobj_binary()
        else:
            return get_fobj_text()

    elif extension == "xz":
        if lzma is None:
            raise RuntimeError("lzma support is not installed")
        fobj_binary = lzma.LZMAFile(get_fobj_binary(), mode=mode_binary)

    elif extension == "gz":
        fobj_binary = gzip.GzipFile(fileobj=get_fobj_binary())

    elif extension == "bz2":
        if bz2 is None:
            raise RuntimeError("bzip2 support is not installed")
        fobj_binary = bz2.BZ2File(get_fobj_binary(), mode=mode_binary)

    if binary_mode:
        return fobj_binary
    else:
        return io.TextIOWrapper(fobj_binary, encoding=encoding)


def csv_to_sqlite(
    input_filename,
    output_filename,
    samples=None,
    dialect=None,
    batch_size=10000,
    encoding="utf-8",
    callback=None,
    force_types=None,
    chunk_size=8388608,
    table_name="table1",
    schema=None,
):
    "Export a CSV file to SQLite, based on field type detection from samples"

    # TODO: automatically detect encoding if encoding == `None`
    # TODO: should be able to specify fields
    # TODO: if schema is provided and the names are in uppercase, this function
    #       will fail

    if dialect is None:  # Get a sample to detect dialect
        fobj = open_compressed(input_filename, mode="rb")
        sample = fobj.read(chunk_size)
        fobj.close()
        dialect = rows.plugins.csv.discover_dialect(sample, encoding=encoding)
    elif isinstance(dialect, six.text_type):
        dialect = csv.get_dialect(dialect)

    if schema is None:  # Identify data types
        fobj = open_compressed(input_filename, encoding=encoding)
        data = list(islice(csv.DictReader(fobj, dialect=dialect), samples))
        fobj.close()
        schema = rows.import_from_dicts(data).fields
        if force_types is not None:
            schema.update(force_types)

    # Create lazy table object to be converted
    # TODO: this lazyness feature will be incorported into the library soon so
    #       we can call here `rows.import_from_csv` instead of `csv.reader`.
    fobj = open_compressed(input_filename, encoding=encoding)
    csv_reader = csv.reader(fobj, dialect=dialect)
    header = make_header(next(csv_reader))  # skip header
    table = rows.Table(fields=OrderedDict([(field, schema[field]) for field in header]))
    table._rows = csv_reader

    # Export to SQLite
    result = rows.export_to_sqlite(
        table,
        output_filename,
        table_name=table_name,
        batch_size=batch_size,
        callback=callback,
    )
    fobj.close()
    return result


def sqlite_to_csv(
    input_filename,
    table_name,
    output_filename,
    dialect=csv.excel,
    batch_size=10000,
    encoding="utf-8",
    callback=None,
    query=None,
):
    """Export a table inside a SQLite database to CSV"""

    # TODO: should be able to specify fields
    # TODO: should be able to specify custom query

    if isinstance(dialect, six.text_type):
        dialect = csv.get_dialect(dialect)

    if query is None:
        query = "SELECT * FROM {}".format(table_name)
    connection = sqlite3.Connection(input_filename)
    cursor = connection.cursor()
    result = cursor.execute(query)
    header = [item[0] for item in cursor.description]
    fobj = open_compressed(output_filename, mode="w", encoding=encoding)
    writer = csv.writer(fobj, dialect=dialect)
    writer.writerow(header)
    total_written = 0
    for batch in rows.plugins.utils.ipartition(result, batch_size):
        writer.writerows(batch)
        written = len(batch)
        total_written += written
        if callback:
            callback(written, total_written)
    fobj.close()


class CsvLazyDictWriter:
    """Lazy CSV dict writer, with compressed output option

    This class is almost the same as `csv.DictWriter` with the following
    differences:

    - You don't need to pass `fieldnames` (it's extracted on the first
      `.writerow` call);
    - You can pass either a filename or a fobj (like `sys.stdout`);
    - If passing a filename, it can end with `.gz`, `.xz` or `.bz2` and the
      output file will be automatically compressed.
    """

    def __init__(self, filename_or_fobj, encoding="utf-8", *args, **kwargs):
        self.writer = None
        self.filename_or_fobj = filename_or_fobj
        self.encoding = encoding
        self._fobj = None
        self.writer_args = args
        self.writer_kwargs = kwargs
        self.writer_kwargs["lineterminator"] = kwargs.get("lineterminator", "\n")
        # TODO: check if it should be the same in other OSes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def fobj(self):
        if self._fobj is None:
            if getattr(self.filename_or_fobj, "read", None) is not None:
                self._fobj = self.filename_or_fobj
            else:
                self._fobj = open_compressed(
                    self.filename_or_fobj, mode="w", encoding=self.encoding
                )

        return self._fobj

    def writerow(self, row):
        if self.writer is None:
            self.writer = csv.DictWriter(
                self.fobj,
                fieldnames=list(row.keys()),
                *self.writer_args,
                **self.writer_kwargs
            )
            self.writer.writeheader()

        self.writerow = self.writer.writerow
        return self.writerow(row)

    def __del__(self):
        self.close()

    def close(self):
        if self._fobj and not self._fobj.closed:
            self._fobj.close()


def execute_command(command):
    """Execute a command and return its output"""

    command = shlex.split(command)
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        raise RuntimeError("Command not found: {}".format(repr(command)))
    process.wait()
    # TODO: may use another codec to decode
    if process.returncode > 0:
        stderr = process.stderr.read().decode("utf-8")
        raise ValueError("Error executing command: {}".format(repr(stderr)))
    data = process.stdout.read().decode("utf-8")
    process.stdin.close()
    process.stdout.close()
    process.stderr.close()
    process.wait()
    return data


def uncompressed_size(filename):
    """Return the uncompressed size for a file by executing commands

    Note: due to a limitation in gzip format, uncompressed files greather than
    4GiB will have a wrong value.
    """

    quoted_filename = shlex.quote(filename)

    # TODO: get filetype from file-magic, if available
    if str(filename).lower().endswith(".xz"):
        output = execute_command('xz --list "{}"'.format(quoted_filename))
        compressed, uncompressed = regexp_sizes.findall(output)
        value, unit = uncompressed.split()
        value = float(value.replace(",", ""))
        return int(value * MULTIPLIERS[unit])

    elif str(filename).lower().endswith(".gz"):
        # XXX: gzip only uses 32 bits to store uncompressed size, so if the
        # uncompressed size is greater than 4GiB, the value returned will be
        # incorrect.
        output = execute_command('gzip --list "{}"'.format(quoted_filename))
        lines = [line.split() for line in output.splitlines()]
        header, data = lines[0], lines[1]
        gzip_data = dict(zip(header, data))
        return int(gzip_data["uncompressed"])

    else:
        raise ValueError('Unrecognized file type for "{}".'.format(filename))

# TODO: move all PostgreSQL-related utils to rows/plugins/postgresql.py

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

    return "psql -c {} {}".format(shlex.quote(command), shlex.quote(database_uri))


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
        header = ", ".join(slug(field_name) for field_name in header)
        header = "({header}) ".format(header=header)
    copy = (
        r"\copy {source} {header}{direction} STDIN WITH("
        "DELIMITER '{delimiter}', "
        "QUOTE '{quote}', "
    )
    if direction == "FROM":
        copy += "FORCE_NULL {header}, "
    copy += "ENCODING '{encoding}', " "FORMAT CSV, HEADER);"

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


def pg_create_table_sql(schema, table_name, unlogged=False):
    field_names = list(schema.keys())
    field_types = list(schema.values())

    columns = [
        "{} {}".format(name, POSTGRESQL_TYPES.get(type_, DEFAULT_POSTGRESQL_TYPE))
        for name, type_ in zip(field_names, field_types)
    ]
    return SQL_CREATE_TABLE.format(
        pre_table="" if not unlogged else "UNLOGGED ",
        post_table=" IF NOT EXISTS",
        table_name=table_name, field_types=", ".join(columns),
    )


def pg_execute_psql(database_uri, sql):
    return execute_command(
        get_psql_command(sql, database_uri=database_uri)
    )


def pgimport(
    filename,
    database_uri,
    table_name,
    encoding=None,
    dialect=None,
    create_table=True,
    schema=None,
    callback=None,
    timeout=0.1,
    chunk_size=8388608,
    max_samples=10000,
    unlogged=False,
):
    """Import data from CSV into PostgreSQL using the fastest method

    Required: psql command
    """

    # TODO: add option to run parallel COPY processes
    # TODO: add logging to the process
    # TODO: detect when error ocurred and interrupt the process immediatly

    if encoding is None:
        fobj = open_compressed(filename, mode="rb")
        sample_bytes = fobj.read(chunk_size)
        fobj.close()
        source = detect_local_source(filename, sample_bytes)
        encoding = source.encoding

    pg_encoding = encoding
    if pg_encoding in ("us-ascii", "ascii"):
        # TODO: convert all possible encodings
        pg_encoding = "SQL_ASCII"

    fobj = open_compressed(filename, mode="r", encoding=encoding)
    sample = fobj.read(chunk_size)
    fobj.close()

    if dialect is None:  # Detect dialect
        dialect = rows.plugins.csv.discover_dialect(
            sample.encode(encoding), encoding=encoding
        )
    elif isinstance(dialect, six.text_type):
        dialect = csv.get_dialect(dialect)
    # TODO: add `else` to check if `dialect` is instace of correct class

    reader = csv.reader(io.StringIO(sample), dialect=dialect)
    csv_field_names = [slug(field_name) for field_name in next(reader)]
    if schema is None:
        field_names = csv_field_names
    else:
        field_names = list(schema.keys())
        if not set(csv_field_names).issubset(set(field_names)):
            raise ValueError('CSV field names are not a subset of schema field names')

    if create_table:
        # If we need to create the table, it creates based on schema
        # (automatically identified or forced), not on CSV directly (field
        # order will be schema's field order).
        if schema is None:
            schema = rows.fields.detect_types(
                csv_field_names,
                itertools.islice(reader, max_samples)
            )
        create_table_sql = pg_create_table_sql(schema, table_name, unlogged=unlogged)
        pg_execute_psql(database_uri, create_table_sql)

    # Prepare the `psql` command to be executed based on collected metadata
    command = get_psql_copy_command(
        database_uri=database_uri,
        dialect=dialect,
        direction="FROM",
        encoding=pg_encoding,
        header=csv_field_names,
        table_name_or_query=table_name,
        is_query=False,
    )
    rows_imported, error = 0, None
    fobj = open_compressed(filename, mode="rb")
    try:
        process = subprocess.Popen(
            shlex.split(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        data = fobj.read(chunk_size)
        total_written = 0
        while data != b"":
            written = process.stdin.write(data)
            total_written += written
            if callback:
                callback(written, total_written)
            data = fobj.read(chunk_size)
        stdout, stderr = process.communicate()
        if stderr != b"":
            for line in stderr.splitlines():
                if line.startswith(b"NOTICE:"):
                    continue
                else:
                    raise RuntimeError(stderr.decode("utf-8"))
        rows_imported = int(stdout.replace(b"COPY ", b"").strip())

    except FileNotFoundError:
        fobj.close()
        raise RuntimeError("Command `psql` not found")

    except BrokenPipeError:
        fobj.close()
        raise RuntimeError(process.stderr.read().decode("utf-8"))

    else:
        fobj.close()
        return {"bytes_written": total_written, "rows_imported": rows_imported}


def pgexport(
    database_uri,
    table_name_or_query,
    filename,
    encoding="utf-8",
    dialect=csv.excel,
    callback=None,
    is_query=False,
    timeout=0.1,
    chunk_size=8388608,
):
    """Export data from PostgreSQL into a CSV file using the fastest method

    Required: psql command
    """

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
            shlex.split(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        total_written = 0
        data = process.stdout.read(chunk_size)
        while data != b"":
            written = fobj.write(data)
            total_written += written
            if callback:
                callback(written, total_written)
            data = process.stdout.read(chunk_size)
        stdout, stderr = process.communicate()
        if stderr != b"":
            raise RuntimeError(stderr.decode("utf-8"))

    except FileNotFoundError:
        fobj.close()
        raise RuntimeError("Command `psql` not found")

    except BrokenPipeError:
        fobj.close()
        raise RuntimeError(process.stderr.read().decode("utf-8"))

    else:
        fobj.close()
        return {"bytes_written": total_written}


def generate_schema(table, export_fields, output_format):
    """Generate table schema for a specific output format and write

    Current supported output formats: 'txt', 'sql' and 'django'.
    The table name and all fields names pass for a slugifying process (table
    name is taken from file name).
    """

    if output_format in ("csv", "txt"):
        from rows import plugins

        data = [
            {
                "field_name": fieldname,
                "field_type": fieldtype.__name__.replace("Field", "").lower(),
            }
            for fieldname, fieldtype in table.fields.items()
            if fieldname in export_fields
        ]
        table = plugins.dicts.import_from_dicts(
            data, import_fields=["field_name", "field_type"]
        )
        if output_format == "txt":
            return plugins.txt.export_to_txt(table)
        elif output_format == "csv":
            return plugins.csv.export_to_csv(table).decode("utf-8")

    elif output_format == "sql":
        # TODO: may use dict from rows.plugins.sqlite or postgresql
        sql_fields = {
            rows.fields.BinaryField: "BLOB",
            rows.fields.BoolField: "BOOL",
            rows.fields.IntegerField: "INT",
            rows.fields.FloatField: "FLOAT",
            rows.fields.PercentField: "FLOAT",
            rows.fields.DateField: "DATE",
            rows.fields.DatetimeField: "DATETIME",
            rows.fields.TextField: "TEXT",
            rows.fields.DecimalField: "FLOAT",
            rows.fields.EmailField: "TEXT",
            rows.fields.JSONField: "TEXT",
        }
        fields = [
            "    {} {}".format(field_name, sql_fields[field_type])
            for field_name, field_type in table.fields.items()
            if field_name in export_fields
        ]
        sql = (
            dedent(
                """
                CREATE TABLE IF NOT EXISTS {name} (
                {fields}
                );
                """
            )
            .strip()
            .format(name=table.name, fields=",\n".join(fields))
            + "\n"
        )
        return sql

    elif output_format == "django":
        django_fields = {
            rows.fields.BinaryField: "BinaryField",
            rows.fields.BoolField: "BooleanField",
            rows.fields.IntegerField: "IntegerField",
            rows.fields.FloatField: "FloatField",
            rows.fields.PercentField: "DecimalField",
            rows.fields.DateField: "DateField",
            rows.fields.DatetimeField: "DateTimeField",
            rows.fields.TextField: "TextField",
            rows.fields.DecimalField: "DecimalField",
            rows.fields.EmailField: "EmailField",
            rows.fields.JSONField: "JSONField",
        }
        table_name = "".join(word.capitalize() for word in table.name.split("_"))

        lines = ["from django.db import models"]
        if rows.fields.JSONField in [
            table.fields[field_name] for field_name in export_fields
        ]:
            lines.append("from django.contrib.postgres.fields import JSONField")
        lines.append("")

        lines.append("class {}(models.Model):".format(table_name))
        for field_name, field_type in table.fields.items():
            if field_name not in export_fields:
                continue

            if field_type is not rows.fields.JSONField:
                django_type = "models.{}()".format(django_fields[field_type])
            else:
                django_type = "JSONField()"
            lines.append("    {} = {}".format(field_name, django_type))

        result = "\n".join(lines) + "\n"
        return result


def load_schema(filename, context=None):
    """Load schema from file in any of the supported formats

    The table must have at least the fields `field_name` and `field_type`.
    `context` is a `dict` with field_type as key pointing to field class, like:
        {"text": rows.fields.TextField, "value": MyCustomField}
    """
    # TODO: load_schema must support Path objects

    table = import_from_uri(filename)
    field_names = table.field_names
    assert "field_name" in field_names
    assert "field_type" in field_names

    context = context or {
        key.replace("Field", "").lower(): getattr(rows.fields, key)
        for key in dir(rows.fields)
        if "Field" in key and key != "Field"
    }
    return OrderedDict([(row.field_name, context[row.field_type]) for row in table])


# Shortcuts
csv2sqlite = csv_to_sqlite
sqlite2csv = sqlite_to_csv
