# coding: utf-8

# Copyright 2014-2018 Álvaro Justen <https://github.com/turicas/rows/>

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
from itertools import islice
try:
    import lzma
except ImportError:
    lzma = None
try:
    import bz2
except ImportError:
    bz2 = None

import requests
import six
from tqdm import tqdm

import rows
from rows.plugins.utils import make_header, slug

try:
    from urlparse import urlparse  # Python 2
except ImportError:
    from urllib.parse import urlparse  # Python 3

try:
    import magic  # TODO: check if it's from file-magic library
except ImportError:
    magic = None
else:
    if not hasattr(magic, 'detect_from_content'):
        # This is not the file-magic library
        magic = None

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


# TODO: should get this information from the plugins
TEXT_PLAIN = {
        'txt': 'text/txt',
        'text': 'text/txt',
        'csv': 'text/csv',
        'json': 'application/json',
}
OCTET_STREAM = {
        'microsoft ooxml': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'par archive data': 'application/parquet',
}
FILE_EXTENSIONS = {
        'csv': 'text/csv',
        'db': 'application/x-sqlite3',
        'htm': 'text/html',
        'html': 'text/html',
        'json': 'application/json',
        'ods': 'application/vnd.oasis.opendocument.spreadsheet',
        'parquet': 'application/parquet',
        'sqlite': 'application/x-sqlite3',
        'text': 'text/txt',
        'tsv': 'text/csv',
        'txt': 'text/txt',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}
MIME_TYPE_TO_PLUGIN_NAME = {
        'application/json': 'json',
        'application/parquet': 'parquet',
        'application/vnd.ms-excel': 'xls',
        'application/vnd.oasis.opendocument.spreadsheet': 'ods',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
        'application/x-sqlite3': 'sqlite',
        'text/csv': 'csv',
        'text/html': 'html',
        'text/txt': 'txt',
}
regexp_sizes = re.compile('([0-9,.]+ [a-zA-Z]+B)')
MULTIPLIERS = {'B': 1, 'KiB': 1024, 'MiB': 1024 ** 2, 'GiB': 1024 ** 3}
POSTGRESQL_TYPES = {
    rows.fields.BinaryField: 'BYTEA',
    rows.fields.BoolField: 'BOOLEAN',
    rows.fields.DateField: 'DATE',
    rows.fields.DatetimeField: 'TIMESTAMP(0) WITHOUT TIME ZONE',
    rows.fields.DecimalField: 'NUMERIC',
    rows.fields.FloatField: 'REAL',
    rows.fields.IntegerField: 'BIGINT',  # TODO: detect when it's really needed
    rows.fields.PercentField: 'REAL',
    rows.fields.TextField: 'TEXT',
    rows.fields.JSONField: 'JSONB',
}
DEFAULT_POSTGRESQL_TYPE = 'BYTEA'
SQL_CREATE_TABLE = ('CREATE TABLE IF NOT EXISTS '
                    '"{table_name}" ({field_types})')


class ProgressBar:

    def __init__(self, prefix, pre_prefix='', total=None, unit=' rows'):
        self.prefix = prefix
        self.progress = tqdm(
            desc=pre_prefix,
            total=total,
            unit=unit,
            unit_scale=True,
            dynamic_ncols=True,
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
            raise ValueError('Either last_done or total_done must be specified')

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
    'Define a source to import a `rows.Table`'

    __slots__ = ['plugin_name', 'uri', 'encoding', 'delete']

    def __init__(self, plugin_name=None, uri=None, encoding=None,
                 delete=False):
        self.plugin_name = plugin_name
        self.uri = uri
        self.delete = delete
        self.encoding = encoding

    def __repr__(self):
        return 'Source(plugin_name={}, uri={}, encoding={}, delete={})'\
                .format(self.plugin_name, self.uri, self.encoding, self.delete)


def plugin_name_by_uri(uri):
    'Return the plugin name based on the URI'

    # TODO: parse URIs like 'sqlite://' also
    parsed = urlparse(uri)
    basename = os.path.basename(parsed.path)

    if not basename.strip():
        raise RuntimeError('Could not identify file format.')

    plugin_name = basename.split('.')[-1].lower()
    if plugin_name in FILE_EXTENSIONS:
        plugin_name = MIME_TYPE_TO_PLUGIN_NAME[FILE_EXTENSIONS[plugin_name]]

    return plugin_name


def extension_by_source(source, mime_type):
    'Return the file extension used by this plugin'

    # TODO: should get this information from the plugin
    extension = source.plugin_name
    if extension:
        return extension

    if mime_type:
        return mime_type.split('/')[-1]


def normalize_mime_type(mime_type, mime_name, file_extension):

    file_extension = file_extension.lower() if file_extension else ''
    mime_name = mime_name.lower() if mime_name else ''
    mime_type = mime_type.lower() if mime_type else ''

    if mime_type == 'text/plain' and file_extension in TEXT_PLAIN:
        return TEXT_PLAIN[file_extension]

    elif mime_type == 'application/octet-stream' and mime_name in OCTET_STREAM:
        return OCTET_STREAM[mime_name]

    elif file_extension in FILE_EXTENSIONS:
        return FILE_EXTENSIONS[file_extension]

    else:
        return mime_type


def plugin_name_by_mime_type(mime_type, mime_name, file_extension):
    'Return the plugin name based on the MIME type'

    return MIME_TYPE_TO_PLUGIN_NAME.get(
            normalize_mime_type(mime_type, mime_name, file_extension),
            None)


def detect_local_source(path, content, mime_type=None, encoding=None):

    # TODO: may add sample_size

    filename = os.path.basename(path)
    parts = filename.split('.')
    extension = parts[-1] if len(parts) > 1 else None

    if magic is not None:
        detected = magic.detect_from_content(content)
        encoding = detected.encoding or encoding
        mime_name = detected.name
        mime_type = detected.mime_type or mime_type

    else:
        encoding = chardet.detect(content)['encoding'] or encoding
        mime_name = None
        mime_type = mime_type or mimetypes.guess_type(filename)[0]

    plugin_name = plugin_name_by_mime_type(mime_type, mime_name, extension)
    if encoding == 'binary':
        encoding = None

    return Source(uri=path,
                  plugin_name=plugin_name,
                  encoding=encoding)


def local_file(path, sample_size=1048576):

    # TODO: may change sample_size
    with open(path, 'rb') as fobj:
        content = fobj.read(sample_size)

    source = detect_local_source(path, content, mime_type=None, encoding=None)

    return Source(uri=path,
                  plugin_name=source.plugin_name,
                  encoding=source.encoding,
                  delete=False)


def download_file(uri, filename=None, verify_ssl=True, timeout=5,
                  progress=False, detect=False, chunk_size=8192,
                  sample_size=1048576):

    response = requests.get(
        uri, verify=verify_ssl, timeout=timeout,
        stream=True, headers={'user-agent': 'rows-{}'.format(rows.__version__)}
    )
    if not response.ok:
        raise RuntimeError('HTTP response: {}'.format(response.status_code))

    # Get data from headers (if available) to help plugin + encoding detection
    real_filename, encoding, mime_type = uri, None, None
    headers = response.headers
    if 'content-type' in headers:
        mime_type, options = cgi.parse_header(headers['content-type'])
        encoding = options.get('charset', encoding)
    if 'content-disposition' in headers:
        _, options = cgi.parse_header(headers['content-disposition'])
        real_filename = options.get('filename', real_filename)

    if progress:
        total = response.headers.get('content-length', None)
        total = int(total) if total else None
        progress_bar = ProgressBar(
            prefix='Downloading file',
            total=total,
            unit='bytes',
        )
    if filename is None:
        tmp = tempfile.NamedTemporaryFile(delete=False)
        fobj = tmp.file
    else:
        fobj = open(filename, mode='wb')
    sample_data = b''
    for data in response.iter_content(chunk_size=chunk_size):
        fobj.write(data)
        if detect and len(sample_data) <= sample_size:
            sample_data += data
        if progress:
            progress_bar.update(len(data))
    fobj.close()
    if progress:
        progress_bar.close()

    # TODO: add ability to continue download
    # Detect file type and rename temporary file to have the correct extension
    if detect:
        source = detect_local_source(real_filename, sample_data, mime_type, encoding)
        extension = extension_by_source(source, mime_type)
        plugin_name = source.plugin_name
        encoding = source.encoding
    else:
        extension, plugin_name, encoding = None, None, None
        if mime_type:
            extension = mime_type.split('/')[-1]

    if filename is None:
        filename = tmp.name
        if extension:
            filename += '.' + extension
        os.rename(tmp.name, filename)

    return Source(
        uri=filename, plugin_name=plugin_name, encoding=encoding, delete=True
    )


def detect_source(uri, verify_ssl, progress, timeout=5):
    '''Return a `rows.Source` with information for a given URI

    If URI starts with "http" or "https" the file will be downloaded.

    This function should only be used if the URI already exists because it's
    going to download/open the file to detect its encoding and MIME type.
    '''

    # TODO: should also supporte other schemes, like file://, sqlite:// etc.

    if uri.lower().startswith('http://') or uri.lower().startswith('https://'):
        return download_file(uri, verify_ssl=verify_ssl, timeout=timeout,
                             progress=progress, detect=True)

    elif uri.startswith('postgres://'):
        return Source(
            delete=False,
            encoding=None,
            plugin_name='postgresql',
            uri=uri,
        )
    else:
        return local_file(uri)


def import_from_source(source, default_encoding, *args, **kwargs):
    'Import data described in a `rows.Source` into a `rows.Table`'

    plugin_name = source.plugin_name
    kwargs['encoding'] = (kwargs.get('encoding', None) or
                          source.encoding or
                          default_encoding)

    try:
        import_function = getattr(rows, 'import_from_{}'.format(plugin_name))
    except AttributeError:
        raise ValueError('Plugin (import) "{}" not found'.format(plugin_name))

    table = import_function(source.uri, *args, **kwargs)

    if source.delete:
        os.unlink(source.uri)

    return table


def import_from_uri(uri, default_encoding='utf-8', verify_ssl=True,
                    progress=False, *args, **kwargs):
    'Given an URI, detects plugin and encoding and imports into a `rows.Table`'

    # TODO: support '-' also
    # TODO: (optimization) if `kwargs.get('encoding', None) is not None` we can
    #       skip encoding detection.
    source = detect_source(uri, verify_ssl=verify_ssl, progress=progress)
    return import_from_source(source, default_encoding, *args, **kwargs)


def export_to_uri(table, uri, *args, **kwargs):
    'Given a `rows.Table` and an URI, detects plugin (from URI) and exports'

    # TODO: support '-' also
    plugin_name = plugin_name_by_uri(uri)

    try:
        export_function = getattr(rows, 'export_to_{}'.format(plugin_name))
    except AttributeError:
        raise ValueError('Plugin (export) "{}" not found'.format(plugin_name))

    return export_function(table, uri, *args, **kwargs)


def open_compressed(filename, mode='r', encoding=None):
    'Return a text-based file object from a filename, even if compressed'

    # TODO: integrate this function in the library itself, using
    # get_filename_or_fobj
    # TODO: accept .gz/.xz/.bz2 extensions on CLI (convert, print, plugin
    # detection etc.)
    binary_mode = 'b' in mode
    extension = str(filename).split('.')[-1].lower()
    if binary_mode and encoding:
        raise ValueError('encoding should not be specified in binary mode')

    if extension == 'xz':
        if lzma is None:
            raise RuntimeError('lzma support is not installed')

        fobj = lzma.open(filename, mode=mode)
        if binary_mode:
            return fobj
        else:
            return io.TextIOWrapper(fobj, encoding=encoding)

    elif extension == 'gz':
        fobj = gzip.GzipFile(filename, mode=mode)
        if binary_mode:
            return fobj
        else:
            return io.TextIOWrapper(fobj, encoding=encoding)

    elif extension == 'bz2':
        if bz2 is None:
            raise RuntimeError('bzip2 support is not installed')

        if binary_mode:  # ignore encoding
            return bz2.open(filename, mode=mode)
        else:
            if 't' not in mode:
                # For some reason, passing only mode='r' to bzip2 is equivalent
                # to 'rb', not 'rt', so we force it here.
                mode += 't'
            return bz2.open(filename, mode=mode, encoding=encoding)

    else:
        if binary_mode:
            return open(filename, mode=mode)
        else:
            return open(filename, mode=mode, encoding=encoding)


def csv2sqlite(input_filename, output_filename, samples=None, dialect=None,
               batch_size=10000, encoding='utf-8', callback=None,
               force_types=None, chunk_size=8388608, table_name='table1',
               schema=None):
    'Export a CSV file to SQLite, based on field type detection from samples'

    # TODO: automatically detect encoding if encoding == `None`
    # TODO: should be able to specify fields

    if dialect is None:  # Get a sample to detect dialect
        fobj = open_compressed(input_filename, mode='rb')
        sample = fobj.read(chunk_size)
        dialect = rows.plugins.csv.discover_dialect(sample, encoding=encoding)
    elif isinstance(dialect, six.text_type):
        dialect = csv.get_dialect(dialect)

    if schema is None:  # Identify data types
        fobj = open_compressed(input_filename, encoding=encoding)
        data = list(islice(csv.DictReader(fobj, dialect=dialect), samples))
        schema = rows.import_from_dicts(data).fields
        if force_types is not None:
            schema.update(force_types)

    # Create lazy table object to be converted
    # TODO: this lazyness feature will be incorported into the library soon so
    #       we can call here `rows.import_from_csv` instead of `csv.reader`.
    reader = csv.reader(
        open_compressed(input_filename, encoding=encoding),
        dialect=dialect,
    )
    header = make_header(next(reader))  # skip header
    table = rows.Table(fields=OrderedDict([(field, schema[field])
                                           for field in header]))
    table._rows = reader

    # Export to SQLite
    return rows.export_to_sqlite(
        table, output_filename, table_name=table_name,
        batch_size=batch_size, callback=callback,
    )


def sqlite2csv(input_filename, table_name, output_filename, dialect=csv.excel,
               batch_size=10000, encoding='utf-8', callback=None, query=None):
    """Export a table inside a SQLite database to CSV"""

    # TODO: should be able to specify fields
    # TODO: should be able to specify custom query

    if isinstance(dialect, six.text_type):
        dialect = csv.get_dialect(dialect)

    if query is None:
        query = 'SELECT * FROM {}'.format(table_name)
    connection = sqlite3.Connection(input_filename)
    cursor = connection.cursor()
    result = cursor.execute(query)
    header = [item[0] for item in cursor.description]
    fobj = open_compressed(output_filename, mode='w', encoding=encoding)
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

    def __init__(self, filename_or_fobj, encoding='utf-8'):
        self.writer = None
        self.filename_or_fobj = filename_or_fobj
        self.encoding = encoding
        self._fobj = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def fobj(self):
        if self._fobj is None:
            if getattr(self.filename_or_fobj, 'read', None) is not None:
                self._fobj = self.filename_or_fobj
            else:
                self._fobj = open_compressed(
                    self.filename_or_fobj,
                    mode='w',
                    encoding=self.encoding,
                )

        return self._fobj

    def writerow(self, row):
        if self.writer is None:
            self.writer = csv.DictWriter(self.fobj, fieldnames=list(row.keys()))
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
        raise RuntimeError('Command not found: {}'.format(repr(command)))
    process.wait()
    # TODO: may use another codec to decode
    if process.returncode > 0:
        stderr = process.stderr.read().decode('utf-8')
        raise ValueError('Error executing command: {}'.format(repr(stderr)))
    return process.stdout.read().decode('utf-8')


def uncompressed_size(filename):
    """Return the uncompressed size for a file by executing commands

    Note: due to a limitation in gzip format, uncompressed files greather than
    4GiB will have a wrong value.
    """

    quoted_filename = shlex.quote(filename)

    # TODO: get filetype from file-magic, if available
    if str(filename).lower().endswith('.xz'):
        output = execute_command('xz --list "{}"'.format(quoted_filename))
        compressed, uncompressed = regexp_sizes.findall(output)
        value, unit = uncompressed.split()
        value = float(value.replace(',', ''))
        return int(value * MULTIPLIERS[unit])

    elif str(filename).lower().endswith('.gz'):
        # XXX: gzip only uses 32 bits to store uncompressed size, so if the
        # uncompressed size is greater than 4GiB, the value returned will be
        # incorrect.
        output = execute_command('gzip --list "{}"'.format(quoted_filename))
        lines = [line.split() for line in output.splitlines()]
        header, data = lines[0], lines[1]
        gzip_data = dict(zip(header, data))
        return int(gzip_data['uncompressed'])

    else:
        raise ValueError('Unrecognized file type for "{}".'.format(filename))


def get_psql_command(command, user=None, password=None, host=None, port=None,
                     database_name=None, database_uri=None):

    if database_uri is None:
        if None in (user, password, host, port, database_name):
            raise ValueError('Need to specify either `database_uri` or the complete information')

        database_uri = \
            "postgres://{user}:{password}@{host}:{port}/{name}".format(
                user=user,
                password=password,
                host=host,
                port=port,
                name=database_name,
            )

    return 'psql -c {} {}'.format(
        shlex.quote(command),
        shlex.quote(database_uri),
    )

def get_psql_copy_command(table_name, header, encoding='utf-8',
                          user=None, password=None, host=None, port=None,
                          database_name=None, database_uri=None,
                          dialect=csv.excel, direction='FROM'):

    direction = direction.upper()
    if direction not in ('FROM', 'TO'):
        raise ValueError('`direction` must be "FROM" or "TO"')

    table_name = slug(table_name)
    if header is None:
        header = ''
    else:
        header = ', '.join(slug(field_name) for field_name in header)
        header = '({header}) '.format(header=header)
    copy = (
        "\copy {table_name} {header}{direction} STDIN "
        "DELIMITER '{delimiter}' "
        "QUOTE '{quote}' "
        "ENCODING '{encoding}' "
        "CSV HEADER;"
    ).format(table_name=table_name, header=header, direction=direction,
             delimiter=dialect.delimiter.replace("'", "''"),
             quote=dialect.quotechar.replace("'", "''"), encoding=encoding)

    return get_psql_command(copy, user=user, password=password, host=host,
                            port=port, database_name=database_name,
                            database_uri=database_uri)


def pgimport(filename, database_uri, table_name, encoding='utf-8',
             dialect=None, create_table=True, schema=None, callback=None,
             timeout=0.1, chunk_size=8388608, max_samples=10000):
    """Import data from CSV into PostgreSQL using the fastest method

    Required: psql command
    """

    fobj = open_compressed(filename, mode='r', encoding=encoding)
    sample = fobj.read(chunk_size)

    if dialect is None:  # Detect dialect
        dialect = rows.plugins.csv.discover_dialect(
            sample.encode(encoding),
            encoding=encoding,
        )
    elif isinstance(dialect, six.text_type):
        dialect = csv.get_dialect(dialect)

    if schema is None:
        # Detect field names
        reader = csv.reader(io.StringIO(sample), dialect=dialect)
        field_names = [slug(field_name) for field_name in next(reader)]

    else:
        field_names = list(schema.keys())

    if create_table:
        if schema is None:
            data = [dict(zip(field_names, row))
                    for row in itertools.islice(reader, max_samples)]
            table = rows.import_from_dicts(data)
            field_types = [table.fields[field_name] for field_name in field_names]
        else:
            field_types = list(schema.values())

        columns = ['{} {}'.format(name, POSTGRESQL_TYPES.get(type_, DEFAULT_POSTGRESQL_TYPE))
                   for name, type_ in zip(field_names, field_types)]
        create_table = SQL_CREATE_TABLE.format(
            table_name=table_name,
            field_types=', '.join(columns),
        )
        execute_command(
            get_psql_command(create_table, database_uri=database_uri)
        )

    # Prepare the `psql` command to be executed based on collected metadata
    command = get_psql_copy_command(
        database_uri=database_uri,
        dialect=dialect,
        direction='FROM',
        encoding=encoding,
        header=field_names,
        table_name=table_name,
    )
    rows_imported, error = 0, None
    fobj = open_compressed(filename, mode='rb')
    try:
        process = subprocess.Popen(
            shlex.split(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        data = fobj.read(chunk_size)
        total_written = 0
        while data != b'':
            written = process.stdin.write(data)
            total_written += written
            if callback:
                callback(written, total_written)
            data = fobj.read(chunk_size)
        stdout, stderr = process.communicate()
        if stderr != b'':
            raise RuntimeError(stderr.decode('utf-8'))
        rows_imported = int(stdout.replace(b'COPY ', b'').strip())

    except FileNotFoundError:
        raise RuntimeError('Command `psql` not found')

    except BrokenPipeError:
        raise RuntimeError(process.stderr.read().decode('utf-8'))

    return {'bytes_written': total_written, 'rows_imported': rows_imported}


def pgexport(database_uri, table_name, filename, encoding='utf-8',
             dialect=csv.excel, callback=None, timeout=0.1, chunk_size=8388608):
    """Export data from PostgreSQL into a CSV file using the fastest method

    Required: psql command
    """
    if isinstance(dialect, six.text_type):
        dialect = csv.get_dialect(dialect)

    # Prepare the `psql` command to be executed to export data
    command = get_psql_copy_command(
        database_uri=database_uri,
        direction='TO',
        encoding=encoding,
        header=None,  # Needed when direction = 'TO'
        table_name=table_name,
        dialect=dialect,
    )
    fobj = open_compressed(filename, mode='wb')
    try:
        process = subprocess.Popen(
            shlex.split(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        total_written = 0
        data = process.stdout.read(chunk_size)
        while data != b'':
            written = fobj.write(data)
            total_written += written
            if callback:
                callback(written, total_written)
            data = process.stdout.read(chunk_size)
        stdout, stderr = process.communicate()
        if stderr != b'':
            raise RuntimeError(stderr.decode('utf-8'))

    except FileNotFoundError:
        raise RuntimeError('Command `psql` not found')

    except BrokenPipeError:
        raise RuntimeError(process.stderr.read().decode('utf-8'))

    return {'bytes_written': total_written}
