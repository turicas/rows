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

from io import BufferedReader

from rows.fileio import COMPRESSED_EXTENSIONS, cfopen
from rows.compat import BINARY_TYPE, DEFAULT_SAMPLE_ROWS, PYTHON_VERSION, TEXT_TYPE


if PYTHON_VERSION < (3, 0, 0):
    def str_repr(string):
        return (b"'" + string.replace("'", "\\'").encode("utf-8") + b"'").decode("utf-8")
else:
    str_repr = repr

# TODO: should get this information from the plugins
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
    import os
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


class ProgressBar(object):
    def __init__(self, prefix, pre_prefix="", total=None, unit=" rows"):
        from tqdm import tqdm

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


class Source(object):
    "Define a source to import a `rows.Table`"

    def __init__(self, uri, plugin_name, encoding, fobj=None, compressed=None, should_delete=None, should_close=None,
                 is_file=None, local=None):
        self.uri = uri  # str, Path
        self.plugin_name = plugin_name  # str
        self.encoding = encoding  # str
        self.fobj = fobj  # object?
        self.compressed = compressed  # bool
        self.should_delete = should_delete  # bool
        self.should_close = should_close  # bool
        self.is_file = is_file  # bool
        self.local = local  # bool

    # TODO: may add a general way to get the decoded version of the file-like object

    # TODO: add `__del__` and call `self.fobj.close()` if `fobj is None and self.should_close`

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
        from pathlib import Path

        # TODO: this method may encapsulate `io.TextIOWrapper` if `filename_or_fobj` is a file-like object open in
        # binary mode and `mode` does not have `"b"` on it.

        if isinstance(filename_or_fobj, Source):
            return filename_or_fobj

        elif isinstance(filename_or_fobj, (BINARY_TYPE, TEXT_TYPE, Path)):
            binary_mode = TEXT_TYPE("b") in TEXT_TYPE(mode)
            filename = filename_or_fobj
            fobj = cfopen(filename, mode=mode, encoding=None if binary_mode else encoding)
            should_close = True if should_close is None else should_close

        else:  # Don't know exactly what is, assume file-like object
            fobj = filename_or_fobj
            filename = getattr(fobj, "name", None)
            if not isinstance(
                filename, (BINARY_TYPE, TEXT_TYPE)
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
    import os

    if PYTHON_VERSION < (3, 0, 0):
        from urlparse import urlparse
    else:
        from urllib.parse import urlparse

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

def _try_to_import_file_magic():
    try:
        import magic
    except (AttributeError, ImportError, TypeError):
        magic = None
    else:
        if not hasattr(magic, "detect_from_content"):
            # This is not the file-magic library
            magic = None
        elif hasattr(magic, "MagicDetect"):
            def fixed__del__(self):
                if magic._close is None:
                    return
                if self.mime_magic is not None:
                    self.mime_magic.close()
                if self.none_magic is not None:
                    self.none_magic.close()
            magic.MagicDetect.__del__ = fixed__del__
    return magic

def _try_to_import_chardet():
    try:
        from requests.compat import chardet
    except ImportError:
        chardet = None

    return chardet


def detect_local_source(path, content, mime_type=None, encoding=None):
    import os

    chardet = _try_to_import_chardet()
    magic = _try_to_import_file_magic()

    # TODO: may add sample_size
    # TODO: use pathlib instead
    filename = os.path.basename(path)
    parts = filename.split(".")
    extension = parts[-1].lower() if len(parts) > 1 else None
    if extension in COMPRESSED_EXTENSIONS:
        compressed = True
        extension = parts[-2].lower() if len(parts) > 2 else None
    else:
        compressed = False

    if chardet and not encoding:
        encoding = chardet.detect(content)["encoding"] or encoding

    if magic is not None and hasattr(magic, "detect_from_content"):
        detected = magic.detect_from_content(content)
        encoding = encoding or detected.encoding
        mime_name = detected.name
        mime_type = detected.mime_type or mime_type

    else:
        import mimetypes

        mime_name = None
        mime_type = mime_type or mimetypes.guess_type(filename)[0]

    plugin_name = plugin_name_by_mime_type(mime_type, mime_name, extension)
    if encoding == "binary":
        encoding = None

    return Source(uri=path, plugin_name=plugin_name, encoding=encoding, compressed=compressed)


def local_file(path, sample_size=1048576):
    # TODO: may change sample_size
    if path.split(".")[-1].lower() in COMPRESSED_EXTENSIONS:
        compressed = True
        fobj = cfopen(path, mode="rb")
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

def _disable_urllib3_warnings():
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

if PYTHON_VERSION < (3, 0, 0):
    from cgi import parse_header
else:
    def parse_header(value):
        from email.message import Message

        msg = Message()
        msg["content-type"] = value
        params = msg.get_params()
        mime_type = params[0][0] if params and params[0] else None
        options = dict(params[1:]) if len(params) > 1 else {}
        return (mime_type, options)


def response_exception_type(exception):
    """Checks if exception is SSL or timeout error even if requests is not installed"""
    from rows.compat import library_installed

    if PYTHON_VERSION < (3, 0, 0):
        from urllib2 import URLError
    else:
        from urllib.request import URLError

    if isinstance(exception, URLError):
        text = TEXT_TYPE(exception).lower()
        if "certificate_verify_failed" in text:
            return "ssl"
        elif "timed out" in text:
            return "timeout"

    elif library_installed("requests"):
        from requests.exceptions import SSLError, Timeout

        if isinstance(exception, SSLError):
            return "ssl"
        elif isinstance(exception, Timeout):
            return "timeout"

    return None  # Could not determine

def _download_file_stdlib(
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
    user_agent=None
):
    # TODO: add ability to continue download
    import os
    import ssl
    import tempfile
    from pathlib import Path

    from rows.version import as_string as rows_version

    # TODO: unify with `download_file`

    if user_agent is None:
        user_agent = "python/rows-{} (Python {})".format(rows_version, PYTHON_VERSION)

    if PYTHON_VERSION < (3, 0, 0):
        from urllib2 import Request, urlopen
    else:
        from urllib.request import Request, urlopen

    request = Request(uri, headers={"User-Agent": user_agent})
    if not verify_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        response = urlopen(request, context=ctx, timeout=timeout)
    else:
        response = urlopen(request, timeout=timeout)

    if response.getcode() >= 400:
        raise RuntimeError("HTTP response: {}".format(response.getcode()))

    # Get data from headers (if available) to help plugin + encoding detection
    real_filename, encoding, mime_type = uri, None, None
    headers = response.headers
    if "content-type" in headers:
        mime_type, options = parse_header(headers["content-type"])
        encoding = options.get("charset", encoding)
    if "content-disposition" in headers:
        _, options = parse_header(headers["content-disposition"])
        real_filename = options.get("filename", real_filename)

    if filename is None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        fobj = cfopen(tmp.name, mode="wb")
    else:
        fobj = cfopen(filename, mode="wb")

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

    # TODO: implement stream reading
    data = response.read()
    fobj.write(data)
    fobj.close()
    if progress:
        progress_bar.update(len(data))
        progress_bar.close()

    # Detect file type and rename temporary file to have the correct extension
    sample_data = data[:sample_size]
    if detect:
        # TODO: check if will work for compressed files
        source = detect_local_source(real_filename, sample_data, mime_type, encoding)
        extension = extension_by_source(source, mime_type)
        last_extension = real_filename.split(".")[-1].lower()
        if source.compressed and last_extension in COMPRESSED_EXTENSIONS and extension not in COMPRESSED_EXTENSIONS:
            extension += "." + last_extension
        plugin_name = source.plugin_name
        encoding = source.encoding
    else:
        extension, plugin_name, encoding = None, None, None
    if not extension and mime_type:
        extension = mime_type.split("/")[-1].lower().strip()
        if extension == "gzip":
            extension = "gz"

    if filename is None:
        filename = tmp.name
        if extension:
            filename += "." + extension
        # TODO: use pathlib instead
        os.rename(tmp.name, filename)
    else:
        extension = filename.split(".")[-1].lower().strip()

    return Source(
        uri=filename,
        plugin_name=plugin_name,
        encoding=encoding,
        should_delete=True,
        compressed=extension in COMPRESSED_EXTENSIONS,
        is_file=True,
        local=True,  # We just downloaded it!
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
    user_agent=None
):
    from rows.compat import library_installed

    if not library_installed("requests"):
        return _download_file_stdlib(
            uri,
            filename=filename,
            verify_ssl=verify_ssl,
            timeout=timeout,
            progress=progress,
            detect=detect,
            chunk_size=chunk_size,
            sample_size=sample_size,
            retries=retries,
            progress_pattern=progress_pattern,
            user_agent=user_agent,
        )

    # TODO: add ability to continue download
    import os
    import tempfile
    from pathlib import Path

    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry

    from rows.version import as_string as rows_version

    _disable_urllib3_warnings()

    if user_agent is None:
        user_agent = "python/rows-{} (requests {})".format(rows_version, requests.__version__)
    session = requests.Session()
    retry_adapter = HTTPAdapter(max_retries=Retry(total=retries, backoff_factor=1))
    session.mount("http://", retry_adapter)
    session.mount("https://", retry_adapter)

    response = session.get(
        uri,
        verify=verify_ssl,
        timeout=timeout,
        stream=True,
        headers={"User-Agent": user_agent},
    )
    if not response.ok:
        raise RuntimeError("HTTP response: {}".format(response.status_code))

    # Get data from headers (if available) to help plugin + encoding detection
    real_filename, encoding, mime_type = uri, None, None
    headers = response.headers
    if "content-type" in headers:
        mime_type, options = parse_header(headers["content-type"])
        encoding = options.get("charset", encoding)
    if "content-disposition" in headers:
        _, options = parse_header(headers["content-disposition"])
        real_filename = options.get("filename", real_filename)

    if filename is None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        fobj = cfopen(tmp.name, mode="wb")
    else:
        fobj = cfopen(filename, mode="wb")

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
        last_extension = real_filename.split(".")[-1].lower()
        if source.compressed and last_extension in COMPRESSED_EXTENSIONS and extension not in COMPRESSED_EXTENSIONS:
            extension += "." + last_extension
        plugin_name = source.plugin_name
        encoding = source.encoding
    else:
        extension, plugin_name, encoding = None, None, None
    if not extension and mime_type:
        extension = mime_type.split("/")[-1].lower().strip()
        if extension == "gzip":
            extension = "gz"

    if filename is None:
        filename = tmp.name
        if extension:
            filename += "." + extension
        # TODO: use pathlib instead
        os.rename(tmp.name, filename)
    else:
        extension = filename.split(".")[-1].lower().strip()

    return Source(
        uri=filename,
        plugin_name=plugin_name,
        encoding=encoding,
        should_delete=True,
        compressed=extension in COMPRESSED_EXTENSIONS,
        is_file=True,
        local=True,  # We just downloaded it!
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

    import rows.plugins as plugins

    # TODO: test cfopen
    plugin_name = source.plugin_name
    kwargs["encoding"] = (
        kwargs.get("encoding", None) or source.encoding or default_encoding
    )

    if not plugin_name or not hasattr(plugins, plugin_name):
        raise ValueError('Plugin (import) "{}" not found'.format(plugin_name))
    plugin = getattr(plugins, plugin_name)
    try:
        import_function = getattr(plugin, "import_from_{}".format(plugin_name))
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
    import rows

    # TODO: support '-' also
    plugin_name = plugin_name_by_uri(uri)

    try:
        export_function = getattr(rows, "export_to_{}".format(plugin_name))
    except AttributeError:
        raise ValueError('Plugin (export) "{}" not found'.format(plugin_name))

    return export_function(table, uri, *args, **kwargs)


def open_compressed(*args, **kwargs):
    # TODO: add warning deprecated
    return cfopen(*args, **kwargs)


def csv_to_sqlite(
    input_filename,
    output_filename,
    samples=DEFAULT_SAMPLE_ROWS,
    dialect=None,
    batch_size=10000,
    encoding=None,
    callback=None,
    force_types=None,
    chunk_size=8388608,
    table_name="table1",
    schema=None,
):
    "Export a CSV file to SQLite, based on field type detection from samples"
    import csv
    from itertools import islice
    from collections import OrderedDict

    from rows.plugins.plugin_csv import CsvInspector
    from rows.plugins.plugin_sqlite import export_to_sqlite
    from rows.plugins.utils import make_header
    from rows.table import Table

    # TODO: move to rows.plugins.plugin_sqlite
    # TODO: we may move all inspection (encoding, dialect etc.) to outside this
    # function
    # TODO: should be able to specify fields
    # TODO: if schema is provided and the names are in uppercase, this function
    #       will fail

    inspector = CsvInspector(input_filename, chunk_size=chunk_size, max_samples=samples, encoding=encoding)
    encoding = encoding or inspector.encoding
    dialect = dialect or inspector.dialect
    if isinstance(dialect, TEXT_TYPE):
        dialect = csv.get_dialect(dialect)
    if schema is None:
        schema = inspector.schema
        if force_types is not None:
            schema.update(force_types)

    # Create lazy table object to be converted
    # TODO: this lazyness feature will be incorported into the library soon so
    #       we can call here `rows.import_from_csv` instead of `csv.reader`.
    fobj = cfopen(input_filename, encoding=encoding)
    csv_reader = csv.reader(fobj, dialect=dialect)
    original_header = next(csv_reader)
    header = make_header(original_header)
    table = Table(
        fields=OrderedDict([
            (field, schema[original_field])
            for field, original_field in zip(header, original_header)
        ]))
    table._rows = csv_reader

    # Export to SQLite
    result = export_to_sqlite(
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
    dialect="excel",
    batch_size=10000,
    encoding="utf-8",
    callback=None,
    query=None,
):
    """Export a table inside a SQLite database to CSV"""
    import csv
    import sqlite3

    from rows.plugins.utils import ipartition

    # TODO: should be able to specify fields
    # TODO: should be able to specify custom query

    if isinstance(dialect, TEXT_TYPE):
        dialect = csv.get_dialect(dialect)

    if query is None:
        query = "SELECT * FROM {}".format(table_name)
    connection = sqlite3.Connection(input_filename)
    cursor = connection.cursor()
    result = cursor.execute(query)
    header = [item[0] for item in cursor.description]
    fobj = cfopen(output_filename, mode="w", encoding=encoding)
    writer = csv.writer(fobj, dialect=dialect)
    writer.writerow(header)
    total_written = 0
    for batch in ipartition(result, batch_size):
        writer.writerows(batch)
        written = len(batch)
        total_written += written
        if callback:
            callback(written, total_written)
    fobj.close()


class CsvLazyDictWriter(object):
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
                self._fobj = cfopen(
                    self.filename_or_fobj, mode="w", encoding=self.encoding
                )

        return self._fobj

    def writerow(self, row):
        import csv

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


def execute_command(command, timeout=30.0, encoding="utf-8"):
    """Execute a command and return its output"""
    import shlex
    import subprocess
    from rows.compat import BINARY_TYPE, PYTHON_VERSION, TEXT_TYPE

    if PYTHON_VERSION < (3, 0, 0):
        from collections import Sequence
    else:
        from collections.abc import Sequence

    if isinstance(command, (BINARY_TYPE, TEXT_TYPE)):
        command = shlex.split(command)
    elif not isinstance(command, Sequence):
        raise ValueError("Unknown command type: {}".format(type(command)))
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if PYTHON_VERSION < (3, 0, 0):
        stdout, stderr = process.communicate()
    else:
        stdout, stderr = process.communicate(timeout=timeout)
    if process.returncode > 0:
        stderr = stderr.decode(encoding)
        raise ValueError("Error executing command: {}".format(repr(stderr)))
    data = stdout.decode(encoding)
    process.wait()
    return data


def uncompressed_size(filename):
    """Return the uncompressed size for a file by executing commands

    Note: due to a limitation in gzip format, uncompressed files greather than
    4GiB could have a wrong value (more info on function
    `estimate_gzip_uncompressed_size`).
    """

    # TODO: get filetype from file-magic, if available
    if TEXT_TYPE(filename).lower().endswith(".xz"):
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

    elif TEXT_TYPE(filename).lower().endswith(".gz"):
        return estimate_gzip_uncompressed_size(filename)

    else:
        raise ValueError('Unrecognized file type for "{}".'.format(filename))


def generate_schema(table, export_fields, output_format, max_choices=100, exclude_choices=None):
    """Generate table schema for a specific output format and write

    Current supported output formats: 'txt', 'sql' and 'django'.
    The table name and all fields names pass for a slugifying process (table
    name is taken from file name).
    """
    import json
    from collections import OrderedDict, defaultdict

    from rows import fields as rows_fields
    # Detect field features
    # TODO: move this code to detect algorithm and for each plugin (if possible), so we have this metadata available on
    # all tables
    # TODO: use rows.fields.NULL (or move NULL to rows.constants and use it)?
    null_values = (None, "", "-", "N/A", "NA", "null", "NULL", "none", "NONE", "None")
    exclude_choices = set() if exclude_choices is None else set(exclude_choices)
    field_metadata = {}
    for field_name, field_type in table.fields.items():
        field_metadata[field_name] = {"type": field_type}
        values = table[field_name]
        field_metadata[field_name]["null"] = any(value in null_values for value in values)
        if field_type is rows_fields.TextField:
            field_metadata[field_name]["max_length"] = max(1, max(len(value) for value in values if value is not None))
            if any("\n" in value or len(value) > 65533 for value in values):  # MySQL VARCHAR stores up to 65,533
                field_metadata[field_name]["subtype"] = "TEXT"
            else:
                field_metadata[field_name]["subtype"] = "VARCHAR"
            if field_name not in exclude_choices:
                field_choices = set()
                for value in values:
                    if value != "":
                        field_choices.add(value)
                    if len(field_choices) > max_choices:
                        field_choices = None
                        break
                if field_choices is not None:
                    field_metadata[field_name]["choices"] = field_choices

        elif field_type in (rows_fields.IntegerField, rows_fields.FloatField, rows_fields.DecimalField):
            min_value = field_metadata[field_name]["min"] = min(value for value in values if value is not None)
            max_value = field_metadata[field_name]["max"] = max(value for value in values if value is not None)
            if field_type is rows_fields.IntegerField:
                # TODO: add TINYINT and MEDIUMINT? (MySQL)
                if -32768 <= min_value and 32767 >= max_value:  # 2 bytes
                    field_metadata[field_name]["subtype"] = "SMALLINT"
                elif -2147483648 <= min_value and 2147483647 >= max_value:  # 4 bytes
                    field_metadata[field_name]["subtype"] = "INTEGER"
                elif -9223372036854775808 <= min_value and 9223372036854775807 >= max_value:  # 8 bytes
                    field_metadata[field_name]["subtype"] = "BIGINT"
            if field_type is rows_fields.DecimalField:
                max_left = max_right = 0
                for value in values:
                    value_str = TEXT_TYPE(value).strip("-")
                    if "." in value_str:
                        left, right = value_str.split(".")
                    else:
                        left, right = value_str, ""
                    max_left = max(max_left, len(left))
                    max_right = max(max_right, len(right))
                field_metadata[field_name]["decimal_places"] = max_right
                field_metadata[field_name]["max_digits"] = max_left + max_right

    # Check if any of the fields have the same choices
    same_choices = defaultdict(list)
    added_as_repeated = set()
    for index_1, (field_name_1, metadata_1) in enumerate(field_metadata.items()):
        if "choices" not in metadata_1:
            continue
        for index_2, (field_name_2, metadata_2) in enumerate(field_metadata.items()):
            if "choices" not in metadata_2 or index_1 >= index_2:
                continue
            if metadata_1["choices"] == metadata_2["choices"] and field_name_2 not in added_as_repeated:
                same_choices[field_name_1].append(field_name_2)
                added_as_repeated.add(field_name_2)
    reuse_choices = {}
    if same_choices:
        for original_choice, repeated_choices in same_choices.items():
            for repeated_choice in repeated_choices:
                reuse_choices[repeated_choice] = original_choice

    if output_format in ("csv", "txt"):
        from rows import plugins

        data = []
        for field_name in table.field_names:
            metadata = field_metadata[field_name]
            if field_name not in export_fields:
                continue
            if "choices" in metadata:
                metadata["choices"] = json.dumps(sorted(metadata["choices"]))
            data.append(
                OrderedDict([
                    ("field_name", field_name),
                    ("field_type", metadata["type"].__name__.replace("Field", "").lower()),
                    ("null", metadata.get("null")),
                    ("min", metadata.get("min")),
                    ("max", metadata.get("max")),
                    ("subtype", metadata.get("subtype")),
                    ("decimal_places", metadata.get("decimal_places")),
                    ("max_digits", metadata.get("max_digits")),
                    ("max_length", metadata.get("max_length")),
                    ("choices", metadata.get("choices")),
                ])
            )
        table = plugins.dicts.import_from_dicts(data)
        if output_format == "txt":
            return plugins.txt.export_to_txt(table)
        elif output_format == "csv":
            return plugins.csv.export_to_csv(table).decode("utf-8")

    elif output_format == "sql":
        from textwrap import dedent

        # TODO: may use dict from rows.plugins.sqlite or postgresql
        sql_fields = {
            rows_fields.BinaryField: "BLOB",
            rows_fields.BoolField: "BOOL",
            rows_fields.IntegerField: "INTEGER",
            rows_fields.FloatField: "FLOAT",
            rows_fields.PercentField: "FLOAT",
            rows_fields.DateField: "DATE",
            rows_fields.DatetimeField: "TIMESTAMP",
            rows_fields.TextField: "TEXT",
            rows_fields.DecimalField: "DECIMAL",
            rows_fields.EmailField: "TEXT",
            rows_fields.JSONField: "TEXT",
        }
        choices_sql = []
        fields = []
        for field_name in table.field_names:
            if field_name not in export_fields:
                continue
            metadata = field_metadata[field_name]
            sql_type = sql_fields[metadata["type"]]
            if sql_type == "DECIMAL":
                sql_type += "({}, {})".format(metadata["max_digits"], metadata["decimal_places"])
            elif sql_type == "INTEGER":
                sql_type = metadata["subtype"]
            elif sql_type == "TEXT":
                if metadata.get("subtype") == "VARCHAR":
                    sql_type = "VARCHAR({})".format(metadata["max_length"])
                field_choices = metadata.get("choices")
                if field_choices is not None:
                    if field_name not in reuse_choices:
                        enum_name = "enum_{}".format(field_name)
                        choices_sql.append(
                            """CREATE TYPE "{}" AS ENUM ({}\n);""".format(
                                enum_name, ",".join("\n  " + str_repr(value) for value in sorted(field_choices))
                            )
                        )
                        sql_type = enum_name
                    else:
                        original_choices = reuse_choices[field_name]
                        enum_name = "enum_{}".format(original_choices)
                        sql_type = enum_name
            # TODO: detect/add 'WITH TIME ZONE' when sql_type == "TIMESTAMP"
            # TODO: should add comments, like max_length when sql_type == "TEXT"?
            not_null = " NOT NULL" if not metadata["null"] else ""
            fields.append('    "{}" {}{}'.format(field_name, sql_type, not_null))
        sql = (
            dedent(
                """
                CREATE TABLE IF NOT EXISTS "{name}" (
                {fields}
                );
                """
            )
            .strip()
            .format(name=table.name, fields=",\n".join(fields))
            + "\n"
        )
        if choices_sql:
            sql = "\n".join(choices_sql) + "\n\n" + sql
        return sql

    elif output_format == "django":
        django_fields = {
            rows_fields.BinaryField: "BinaryField",
            rows_fields.BoolField: "BooleanField",
            rows_fields.IntegerField: "IntegerField",
            rows_fields.FloatField: "FloatField",
            rows_fields.PercentField: "DecimalField",
            rows_fields.DateField: "DateField",
            rows_fields.DatetimeField: "DateTimeField",
            rows_fields.TextField: "TextField",
            rows_fields.DecimalField: "DecimalField",
            rows_fields.EmailField: "EmailField",
            rows_fields.JSONField: "JSONField",
        }
        table_name = "".join(word.capitalize() for word in table.name.split("_"))

        lines = [
            "from django.db import models",
            "",
            "",
            "class {}(models.Model):".format(table_name),
        ]
        model_choices = []
        for field_name in table.field_names:
            if field_name not in export_fields:
                continue
            metadata = field_metadata[field_name]
            django_type_name = django_fields[metadata["type"]]
            comment = OrderedDict()
            options = OrderedDict([
                ("null", metadata["null"]),
                ("blank", metadata["null"]),
            ])
            for key in ("max_length", "decimal_places", "max_digits"):
                if key in metadata:
                    options[key] = metadata[key]
            for key in ("max", "min"):
                if key in metadata:
                    comment["{} value".format(key)] = metadata[key]
            if django_type_name == "TextField":
                if metadata["subtype"] == "VARCHAR":
                    django_type_name = "CharField"
                field_choices = metadata.get("choices")
                if field_choices is not None:
                    if field_name not in reuse_choices:
                        choices_name = "{}_CHOICES".format(field_name.upper())
                        options["choices"] = choices_name
                        model_choices.append(
                            "    {} = (\n        {},\n    )".format(
                                choices_name,
                                ",\n        ".join(
                                    "({}, {})".format(index, str_repr(value))
                                    for index, value in enumerate(sorted(field_choices))
                                )
                            )
                        )
                    else:
                        original_choice = reuse_choices[field_name]
                        choices_name = "{}_CHOICES".format(original_choice.upper())
                        options["choices"] = choices_name
                    django_type_name = "SmallIntegerField"
                    del options["max_length"]
            options_str = ", ".join("{}={}".format(key, value) for key, value in options.items())
            comment_str = "  # " + ", ".join("{}={}".format(key, value) for key, value in comment.items())
            if django_type_name == "IntegerField":
                subtypes = {
                    "SMALLINT": "SmallIntegerField",
                    "INTEGER": "IntegerField",
                    "BIGINT": "BigIntegerField",
                }
                django_type_name = subtypes[metadata["subtype"]]
                if metadata["min"] > 0:
                    django_type_name = "Positive" + django_type_name
            django_type = "models.{}({})".format(django_type_name, options_str)
            lines.append("    {} = {}{}".format(field_name, django_type, comment_str if comment else ""))

        if model_choices:  # Add choice definitions before any field definitions
            for index, line in enumerate(lines):
                if line.startswith("class "):
                    break
            lines.insert(index + 1, "")
            for choice_def in reversed(model_choices):
                lines.insert(index + 1, choice_def)

        # TODO: Add a method to create ORM object from a dict, mapping the choices
        # TODO: must convert all types (int, float etc.)
        #lines.append("")
        #lines.append(
        #    indent(
        #        dedent(
        #            f"""
        #            @classmethod
        #            def from_dict(cls, data):
        #                "Converts a dictionary into `{table_name}`, mapping choices"
        #                new = {{key: value for key, value in data.items()}}
        #                new[]
        #                for field_name in ({field_names_str}):
        #                    cls._CHOICES
        #                return cls(**new)
        #            """
        #        ),
        #        4
        #    )
        #)
        # TODO: implement to_dict also
        result = "\n".join(lines) + "\n"
        return result


def load_schema(filename, context=None):
    """Load schema from file in any of the supported formats

    The table must have at least the fields `field_name` and `field_type`.
    `context` is a `dict` with field_type as key pointing to field class, like:
        {"text": rows.fields.TextField, "value": MyCustomField}
    """
    from collections import OrderedDict

    from rows import fields as rows_fields
    # TODO: load_schema must support Path objects

    table = import_from_uri(filename)
    field_names = table.field_names
    assert "field_name" in field_names
    assert "field_type" in field_names

    context = context or {
        key.replace("Field", "").lower(): getattr(rows_fields, key)
        for key in dir(rows_fields)
        if "Field" in key and key != "Field"
    }
    return OrderedDict([(row.field_name, context[row.field_type]) for row in table])


def scale_number(n, divider=1000, suffix=None, multipliers="KMGTPEZ", decimal_places=2):
    suffix = suffix if suffix is not None else ""
    count = -1
    divider = float(divider)
    while n >= divider:
        n /= divider
        count += 1
    multiplier = multipliers[count] if count > -1 else ""
    if not multiplier:
        return TEXT_TYPE(n) + suffix
    else:
        fmt_str = "{{n:.{}f}}{{multiplier}}{{suffix}}".format(decimal_places)
        return fmt_str.format(n=n, multiplier=multiplier, suffix=suffix)


class NotNullWrapper(BufferedReader):
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
    from rows.plugins import postgresql

    return postgresql.pgimport(filename_or_fobj=filename, *args, **kwargs)


def pgexport(*args, **kwargs):
    # TODO: add warning (will remove this function from here in the future)
    from rows.plugins import postgresql

    return postgresql.pgexport(*args, **kwargs)


def get_psql_command(*args, **kwargs):
    # TODO: add warning (will remove this function from here in the future)
    from rows.plugins import postgresql

    return postgresql.get_psql_command(*args, **kwargs)


def get_psql_copy_command(*args, **kwargs):
    # TODO: add warning (will remove this function from here in the future)
    from rows.plugins import postgresql

    return postgresql.get_psql_copy_command(*args, **kwargs)


def pg_create_table_sql(*args, **kwargs):
    # TODO: add warning (will remove this function from here in the future)
    from rows.plugins import postgresql
    return postgresql.pg_create_table_sql(*args, **kwargs)


def pg_execute_sql(*args, **kwargs):
    # TODO: add warning (will remove this function from here in the future)
    from rows.plugins import postgresql
    return postgresql.pg_execute_sql(*args, **kwargs)
