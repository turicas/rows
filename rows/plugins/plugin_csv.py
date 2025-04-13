# coding: utf-8

# Copyright 2014-2022 Álvaro Justen <https://github.com/turicas/rows/>

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
from io import BytesIO, TextIOWrapper, StringIO

from rows.utils import Source
from rows.compat import BINARY_TYPE, DEFAULT_SAMPLE_ROWS, PYTHON_VERSION, TEXT_TYPE


PY2 = PYTHON_VERSION < (3, 0, 0)

if PY2:

    def _csv_reader(fobj, dialect, encoding):
        for row in csv.reader(fobj, dialect=dialect):
            yield [value.decode(encoding) for value in row]

    class _CsvWriter(object):
        def __init__(self, fobj, dialect, encoding):
            self.fobj = fobj
            self.writer = csv.writer(fobj)
            self.encoding = encoding

        def writerow(self, row):
            self.writer.writerow([value.encode(self.encoding) for value in row])

        def writerows(self, data):
            writerow = self.writer.writerow
            encoding = self.encoding
            for row in data:
                writerow([value.encode(encoding) for value in row])

    class excel_semicolon(csv.excel):
        delimiter = BINARY_TYPE(";")

    def discover_dialect(sample, encoding=None, delimiters=(b",", b";", b"\t", b"|")):
        """Discover a CSV dialect based on a sample size.

        `encoding` is not used (Python 2)
        """
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=delimiters)

        except csv.Error:  # Couldn't detect: fall back to 'excel'
            dialect = csv.excel

        fix_dialect(dialect)
        return dialect
else:
    csv_reader = csv.reader

    class excel_semicolon(csv.excel):
        delimiter = ";"

    def discover_dialect(sample, encoding, delimiters=(",", ";", "\t", "|")):
        """Discover a CSV dialect based on a sample size.

        `sample` must be `bytes` and an `encoding must be provided (Python 3)
        """
        # `csv.Sniffer.sniff` on Python 3 requires a `str` object. If we take a
        # sample from the `bytes` object and it happens to end in the middle of
        # a character which has more than one byte, we're going to have an
        # `UnicodeDecodeError`. This `while` avoid this problem by removing the
        # last byte until this error stops.
        finished = False
        while not finished:
            try:
                decoded = sample.decode(encoding)

            except UnicodeDecodeError as exception:
                _, _, _, pos, error = exception.args
                if error == "unexpected end of data" and pos == len(sample):
                    sample = sample[:-1]
                else:
                    raise
            else:
                finished = True

        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(decoded, delimiters=delimiters)

        except csv.Error:  # Couldn't detect: fall back to 'excel'
            dialect = csv.excel

        fix_dialect(dialect)
        return dialect


# Some CSV files have more than 128kB of data in a cell, so we force this value
# to be greater (16MB).
# TODO: check if it impacts in memory usage.
# TODO: may add option to change it by passing a parameter to import/export.
csv.field_size_limit(16777216)
csv.register_dialect("excel-semicolon", excel_semicolon)


def fix_dialect(dialect):
    if not dialect.doublequote and dialect.escapechar is None:
        dialect.doublequote = True

    if dialect.quoting == csv.QUOTE_MINIMAL and dialect.quotechar == "'":
        # Python csv's Sniffer seems to detect a wrong quotechar when
        # quoting is minimal
        dialect.quotechar = '"'

    if not hasattr(dialect, "strict"):
        dialect.strict = False


def fix_file(csv_reader, csv_writer, logger=None):
    """Read a CSV file, merge down rows (if number of cols differ) and fix quotes

    `csv_reader` and `csv_writer` must be `csv.reader` and `csv.writer`
    instances or compatible objects (read/write lists)
    """
    from rows.fields import make_header

    total, written, fixed, n_col, last_row = 0, 0, 0, None, None
    for row in csv_reader:
        total += 1
        if n_col is None:  # First row - header
            n_col = len(row)
            row = make_header(row)
            if logger is not None:
                logger.warning("Detected number of columns: {}".format(n_col))
        elif last_row is not None:
            if not row:
                if logger is not None:
                    logger.warning("Skipping empty row.")
                continue
            fixed += 1
            tmp = last_row[:-1] + [(last_row[-1] + " " + row[0]).strip()]
            if len(row) > 1:
                tmp += row[1:]
            if logger is not None:
                logger.warning("Merging last row ({} cols) with current one ({} cols) - new row has {} cols.".format(len(last_row), len(row), len(tmp)))
            row, last_row = tmp, None
        if len(row) != n_col:
            if logger is not None:
                logger.warning("Saving current truncated row ({} cols) and skipping".format(len(row)))
            last_row = row
        else:  # Write only if has complete row
            csv_writer.writerow(row)
            written += 1
    if logger is not None:
        if fixed > 0:
            logger.warning("Total fixed rows: {}".format(fixed))
        logger.info("Total written rows: {}".format(written))

    return {
        "columns": n_col,
        "rows_read": total,
        "rows_fixed": fixed,
        "rows_written": written,
    }


def read_sample(fobj, sample):
    """Read `sample` bytes from `fobj` and return the cursor to where it was."""
    # TODO: what if object is not seekable? Like in bz2
    cursor = fobj.tell()
    data = fobj.read(sample)
    fobj.seek(cursor)
    return data


def import_from_csv(
    filename_or_fobj,
    encoding="utf-8",
    dialect=None,
    sample_size=262144,
    *args,
    **kwargs
):
    """Import data from a CSV file (automatically detects dialect).

    If a file-like object is provided it MUST be in binary mode, like in
    `open(filename, mode='rb')`.
    """
    from rows.plugins.utils import create_table, is_binary_file

    source = Source.from_file(filename_or_fobj, plugin_name="csv", mode="rb", encoding=encoding)

    if dialect is None:
        dialect = discover_dialect(sample=read_sample(source.fobj, sample_size), encoding=source.encoding)

    fobj = source.fobj
    if not PY2:
        if is_binary_file(fobj):
            fobj = TextIOWrapper(fobj, encoding=encoding)
            # TODO: how to detach in this case, so we preventing from having the file object closed when TextIOWrapper
            # is garbage-collected?
        reader = csv.reader(fobj, dialect=dialect)
    else:
        reader = _csv_reader(fobj, dialect=dialect, encoding=encoding)

    meta = {"imported_from": "csv", "source": source}
    return create_table(reader, meta=meta, *args, **kwargs)


def export_to_csv(
    table,
    filename_or_fobj=None,
    encoding="utf-8",
    dialect=csv.excel,
    batch_size=100,
    callback=None,
    *args,
    **kwargs
):
    """Export a `rows.Table` to a CSV file.


    If a file-like object is provided it MUST be in binary mode, like in
    `open(filename, mode='wb')`.
    If not filename/fobj is provided, the function returns a string with CSV
    contents.
    """
    from rows.plugins.utils import ipartition, is_binary_file, is_fobj, serialize
    # TODO: will work only if table.fields is OrderedDict
    # TODO: should use fobj? What about creating a method like json.dumps?

    orig_filename_or_fobj = filename_or_fobj
    return_data, should_close = False, None
    if filename_or_fobj is None:
        filename_or_fobj = BytesIO()
        return_data = should_close = True
    elif is_fobj(filename_or_fobj) and is_binary_file(filename_or_fobj) and encoding is None:
        raise ValueError("export_to_csv must receive an encoding when file is in binary mode")

    source = Source.from_file(
        filename_or_fobj,
        plugin_name="csv",
        mode="wb",
        encoding=encoding,
        should_close=should_close,
    )

    # TODO: may use `io.BufferedWriter` instead of `ipartition` so user can choose the real size (in Bytes) when to
    # flush to the file system, instead number of rows
    fobj = source.fobj
    should_detach = False
    if not PY2:
        if is_binary_file(fobj):
            fobj = TextIOWrapper(fobj, encoding=encoding)
            should_detach = True
        writer = csv.writer(fobj, dialect=dialect)
    else:
        writer = _CsvWriter(fobj, dialect=dialect, encoding=encoding)

    if callback is None:
        for batch in ipartition(serialize(table, *args, **kwargs), batch_size):
            writer.writerows(batch)

    else:
        serialized = serialize(table, *args, **kwargs)
        writer.writerow(next(serialized))  # First, write the header
        total = 0
        for batch in ipartition(serialized, batch_size):
            writer.writerows(batch)
            total += len(batch)
            callback(total)

    fobj.flush()
    if return_data:
        source.fobj.seek(0)
        result = source.fobj.read()
    else:
        result = orig_filename_or_fobj if is_fobj(orig_filename_or_fobj) else fobj
        fobj.flush()

    if source.should_close:
        fobj.close()
    elif should_detach:
        fobj.detach()

    return result


class CsvInspector(object):
    def __init__(
        self, filename, encoding=None, dialect=None, schema=None, chunk_size=1 * 1024 * 1024,
        max_samples=DEFAULT_SAMPLE_ROWS,
    ):
        self.filename = filename
        self._encoding = encoding
        self._field_names = None
        self._dialect = dialect
        if isinstance(dialect, TEXT_TYPE):
            self._dialect = csv.get_dialect(dialect)
        self._schema = schema
        self._chunk_size = chunk_size
        self._sample_binary = self._sample_unicode = None
        self._max_samples = max_samples

    def _read_sample(self, binary=False):
        from rows.utils import open_compressed

        if binary:
            if self._sample_binary is None:
                fobj = open_compressed(self.filename, mode="rb")
                self._sample_binary = fobj.read(self._chunk_size).replace(b"\x00", b"")
                fobj.close()
            return self._sample_binary

        else:
            if self._sample_unicode is None:
                # TODO: may add a skip on some bytes, since the chunk read could end in the middle of a character
                fobj = open_compressed(self.filename, mode="r", encoding=self.encoding)
                self._sample_unicode = fobj.read(self._chunk_size).replace("\x00", "")
                fobj.close()
            return self._sample_unicode

    @property
    def encoding(self):
        if self._encoding is None:
            from rows.utils import detect_local_source

            source = detect_local_source(self.filename, self._read_sample(binary=True))
            self._encoding = source.encoding
        return self._encoding

    @property
    def dialect(self):
        if self._dialect is None:
            sample = self._read_sample(binary=False)
            self._dialect = discover_dialect(sample.encode(self.encoding), encoding=self.encoding)
        return self._dialect

    @property
    def field_names(self):
        if self._field_names is None:
            reader = csv.reader(
                StringIO(self._read_sample(binary=False)),
                dialect=self.dialect,
            )
            self._field_names = [field_name for field_name in next(reader)]
        return self._field_names

    @property
    def schema(self):
        if self._schema is None:
            import itertools

            from rows import fields

            reader = csv.reader(
                StringIO(self._read_sample(binary=False)),
                dialect=self.dialect,
            )
            self._field_names = [field_name for field_name in next(reader)]
            csv_rows = list(itertools.islice(reader, self._max_samples))
            # `_read_sample` will read a fixed amount of bytes and this could lead to the last row being cut in the
            # middle of a cell, so the last row must be discarded.
            # TODO: add a test for this
            self._schema = fields.detect_types(self._field_names, csv_rows[:-1])
        return self._schema
