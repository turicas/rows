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
import os
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import six

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
except ImportError:
    requests = None
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

import rows
from rows.plugins.utils import make_header

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
else:
    chardet = None


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
MULTIPLIERS = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3}


def estimate_gzip_uncompressed_size(filename):
    """Guess the uncompressed size of a gzip file (it's truncated if > 4GiB)

    The gzip format stores the uncompressed size in just 4 bytes (the last 4
    bytes of the file), so the uncompressed size stored is actually the size
    modulo 2**32 (4GiB). In cases when the real uncompressed size is less than
    4GiB the value will be correct. For uncompressed files greater than 4GiB
    the only way to have the correct value is by reading the whole file - but
    we can estimate it.

    Using `gzip --list <filename>` to get the uncompressed size is not an
    option here because:
    - Prior to version 2.12, the command run quickly but reported
      the wrong uncompressed size (it just reads the 4 last bytes); and
    - Version 2.12 fixed this bug by reading the whole file
      (just to print the uncompressed size!) - it's not an option, since it's
      going to read the whole file (which is a big one).

    From the release notes <https://lists.gnu.org/archive/html/info-gnu/2022-04/msg00003.html>:
        'gzip -l' no longer misreports file lengths 4 GiB and larger.
        Previously, 'gzip -l' output the 32-bit value stored in the gzip header
        even though that is the uncompressed length modulo 2**32.  Now, 'gzip
        -l' calculates the uncompressed length by decompressing the data and
        counting the resulting bytes.  Although this can take much more time,
        nowadays the correctness pros seem to outweigh the performance cons.
    """
    import struct

    compressed_size = os.stat(filename).st_size
    with open(filename, mode="rb") as fobj:
        fobj.seek(-4, 2)
        uncompressed_size = struct.unpack("<I", fobj.read())[0]
    if compressed_size > uncompressed_size:
        # If the compressed size is greater than the uncompressed, probably the
        # uncompressed is greater than 4GiB and we try to guess the correct
        # size by adding "1" bits to the left until the new size is greater
        # than the compressed one and greater than 4GiB. Note that this guess
        # may be wrong for 2 reasons:
        # - The compressed size may be greater than the uncompressed one in
        #   some cases (like trying to compress an already compressed file); or
        # - For very big files we keep shifting the bit "1" to the left
        #   several times, which makes a "hole" between the digit "1" and the
        #   original 32 bits (e.g.: shifting 5 times lead to in 10000X, where
        #   X are the original 32 bits). The value returned is the minimum
        #   expected size for the uncompressed file, since there's no way to
        #   correctly "fill the hole" without reading the whole file.
        i, value = 32, uncompressed_size
        while value <= 2**32 and value < compressed_size:
            value = (1 << i) ^ uncompressed_size
            i += 1
        uncompressed_size = value
    return uncompressed_size


def subclasses(cls):
    """Return all subclasses of a class, recursively"""
    children = cls.__subclasses__()
    return set(children).union(
        set(grandchild for child in children for grandchild in subclasses(child))
    )


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

    # TODO: use pathlib instead
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

    # TODO: should get this information from the plugin
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

    # TODO: use pathlib instead
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
        import mimetypes

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
    retries=3,
    progress_pattern="Downloading file",
):
    # TODO: add ability to continue download
    import cgi
    import tempfile

    session = requests.Session()
    retry_adapter = HTTPAdapter(max_retries=Retry(total=retries, backoff_factor=1))
    session.mount("http://", retry_adapter)
    session.mount("https://", retry_adapter)

    response = session.get(
        uri,
        verify=verify_ssl,
        timeout=timeout,
        stream=True,
        headers={
            "User-Agent": "python/rows-{} (requests {})".format(
                rows.__version__, requests.__version__
            )
        },
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

    if filename is None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        fobj = open_compressed(tmp.name, mode="wb")
    else:
        fobj = open_compressed(filename, mode="wb")

    if progress:
        total = response.headers.get("content-length", None)
        total = int(total) if total else None
        progress_bar = ProgressBar(
            prefix=progress_pattern.format(
                uri=uri,
                filename=Path(fobj.name),
                mime_type=mime_type,
                encoding=encoding,
            ),
            total=total,
            unit="bytes",
        )

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
        # TODO: use pathlib instead
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


# TODO: check https://docs.python.org/3.7/library/fileinput.html
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
            raise ModuleNotFoundError("lzma support is not installed")
        fobj_binary = lzma.LZMAFile(get_fobj_binary(), mode=mode_binary)

    elif extension == "gz":
        import gzip
        fobj_binary = gzip.GzipFile(fileobj=get_fobj_binary(), mode=mode_binary)

    elif extension == "bz2":
        if bz2 is None:
            raise ModuleNotFoundError("bzip2 support is not installed")
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
    from itertools import islice

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
    import sqlite3

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
    import shlex
    import subprocess
    import typing

    if isinstance(command, typing.Text):
        command = shlex.split(command)
    elif not isinstance(command, typing.Sequence):
        raise ValueError("Unknown command type: {}".format(type(command)))
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
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
    4GiB could have a wrong value (more info on function
    `estimate_gzip_uncompressed_size`).
    """

    # TODO: get filetype from file-magic, if available
    if str(filename).lower().endswith(".xz"):
        # TODO: move this approach to reading the file directly, as in gzip
        output = execute_command(["xz", "--list", filename])
        lines = output.splitlines()
        header = lines[0]
        column_start = [header.find(field_name) for field_name in lines[0].split()]
        values = [lines[1][a:b].strip() for a, b in list(zip(column_start, column_start[1:] + [None]))]
        result = dict(zip(header.split(), values))
        value, unit = result.get("Uncompressed", "").split()
        value = float(value.replace(",", ""))
        return int(value * MULTIPLIERS[unit])

    elif str(filename).lower().endswith(".gz"):
        return estimate_gzip_uncompressed_size(filename)

    else:
        raise ValueError('Unrecognized file type for "{}".'.format(filename))


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
        from textwrap import dedent

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


def scale_number(n, divider=1000, suffix=None, multipliers="KMGTPEZ", decimal_places=2):
    suffix = suffix if suffix is not None else ""
    count = -1
    while n >= divider:
        n /= divider
        count += 1
    multiplier = multipliers[count] if count > -1 else ""
    if not multiplier:
        return str(n) + suffix
    else:
        fmt_str = "{{n:.{}f}}{{multiplier}}{{suffix}}".format(decimal_places)
        return fmt_str.format(n=n, multiplier=multiplier, suffix=suffix)


class NotNullWrapper(io.BufferedReader):
    """BufferedReader which removes NUL (`\x00`) from source stream"""

    def read(self, n):
        return super().read(n).replace(b"\x00", b"")

    def readline(self):
        return super().readline().replace(b"\x00", b"")


# Shortcuts and legacy functions
csv2sqlite = csv_to_sqlite
sqlite2csv = sqlite_to_csv


def pgimport(filename, *args, **kwargs):
    # TODO: add warning (will remove this function from here in the future)
    from rows.plugins.postgresql import pgimport as original_function

    return original_function(filename_or_fobj=filename, *args, **kwargs)


def pgexport(*args, **kwargs):
    # TODO: add warning (will remove this function from here in the future)
    from rows.plugins.postgresql import pgexport as original_function

    return original_function(*args, **kwargs)


def get_psql_command(*args, **kwargs):
    # TODO: add warning (will remove this function from here in the future)
    from rows.plugins.postgresql import get_psql_command as original_function

    return original_function(*args, **kwargs)


def get_psql_copy_command(*args, **kwargs):
    # TODO: add warning (will remove this function from here in the future)
    from rows.plugins.postgresql import get_psql_copy_command as original_function

    return original_function(*args, **kwargs)


def pg_create_table_sql(*args, **kwargs):
    # TODO: add warning (will remove this function from here in the future)
    from rows.plugins.postgresql import pg_create_table_sql as original_function

    return original_function(*args, **kwargs)


def pg_execute_sql(*args, **kwargs):
    # TODO: add warning (will remove this function from here in the future)
    from rows.plugins.postgresql import pg_execute_sql as original_function

    return original_function(*args, **kwargs)
