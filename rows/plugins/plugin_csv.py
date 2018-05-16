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

from io import BytesIO, BufferedReader

import six
import unicodecsv

from rows.plugins.utils import (create_table, get_filename_and_fobj,
                                ipartition, serialize)

sniffer = unicodecsv.Sniffer()


class NotNullBytesWrapper(BufferedReader):

    def read(self, *args, **kwargs):
        data = super().read(*args, **kwargs)
        return data.replace(b'\x00', b'')

    def readline(self, *args, **kwargs):
        data = super().readline(*args, **kwargs)
        return data.replace(b'\x00', b'')


if six.PY2:

    def discover_dialect(sample, encoding=None,
                         delimiters=(b',', b';', b'\t', b'|')):
        """Discover a CSV dialect based on a sample size

        `encoding` is not used (Python 2)
        """

        try:
            dialect = sniffer.sniff(sample, delimiters=delimiters)

        except unicodecsv.Error: # Couldn't detect: fall back to 'excel'
            dialect = unicodecsv.excel

        if not dialect.doublequote and dialect.escapechar is None:
            dialect.doublequote = True

        return dialect

elif six.PY3:

    def discover_dialect(sample, encoding, delimiters=(',', ';', '\t', '|')):
        """Discover a CSV dialect based on a sample size

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
                if error == 'unexpected end of data' and pos == len(sample):
                    sample = sample[:-1]
                else:
                    raise
            else:
                finished = True

        try:
            dialect = sniffer.sniff(decoded, delimiters=delimiters)

        except unicodecsv.Error: # Couldn't detect: fall back to 'excel'
            dialect = unicodecsv.excel

        if not dialect.doublequote and dialect.escapechar is None:
            dialect.doublequote = True

        return dialect


def read_sample(fobj, sample):
    "Read `sample` bytes from `fobj` and return the cursor to where it was"

    cursor = fobj.tell()
    data = fobj.read(sample)
    fobj.seek(cursor)
    return data


def import_from_csv(filename_or_fobj, encoding='utf-8', dialect=None,
                    sample_size=262144, *args, **kwargs):
    """Import data from a CSV file (automatically detects dialect)

    If a file-like object is provided it MUST be in binary mode, like in
    `open(filename, mode='rb')`.
    """

    filename, fobj = get_filename_and_fobj(filename_or_fobj, mode='rb')
    fobj = NotNullBytesWrapper(fobj)

    if dialect is None:
        dialect = discover_dialect(sample=read_sample(fobj, sample_size),
                                   encoding=encoding)

    reader = unicodecsv.reader(fobj, encoding=encoding, dialect=dialect)

    meta = {'imported_from': 'csv',
            'filename': filename,
            'encoding': encoding,}
    return create_table(reader, meta=meta, *args, **kwargs)


def export_to_csv(table, filename_or_fobj=None, encoding='utf-8',
                  dialect=unicodecsv.excel, batch_size=100, callback=None,
                  *args, **kwargs):
    """Export a `rows.Table` to a CSV file

    If a file-like object is provided it MUST be in binary mode, like in
    `open(filename, mode='wb')`.
    If not filename/fobj is provided, the function returns a string with CSV
    contents.
    """

    # TODO: will work only if table.fields is OrderedDict
    # TODO: should use fobj? What about creating a method like json.dumps?

    if filename_or_fobj is not None:
        _, fobj = get_filename_and_fobj(filename_or_fobj, mode='wb')
    else:
        fobj = BytesIO()

    # TODO: may use `io.BufferedWriter` instead of `ipartition` so user can
    # choose the real size (in Bytes) when to flush to the file system, instead
    # number of rows
    writer = unicodecsv.writer(fobj, encoding=encoding, dialect=dialect)

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

    if filename_or_fobj is not None:
        fobj.flush()
        return fobj
    else:
        fobj.seek(0)
        result = fobj.read()
        fobj.close()
        return result
