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

from __future__ import unicode_literals

from io import BytesIO

import unicodecsv

from rows.plugins.utils import create_table, get_filename_and_fobj, serialize

try:
    import magic
except ImportError:
    magic = None
else:
    if 'detect_from_content' not in dir(magic):  # it's not file-magic library!
        magic = None


def import_from_csv(filename_or_fobj, encoding=None, dialect=None, *args,
                    **kwargs):
    'Import data from a CSV file'

    filename, fobj = get_filename_and_fobj(filename_or_fobj)

    if encoding is None:
        if magic is not None:
            encoding = magic.detect_from_content(fobj.read(4096)).encoding
            fobj.seek(0)
        else:
            raise ValueError('You must provide `encoding` or install file-magic')

    if dialect is None:
        sample = fobj.readline().decode(encoding)
        dialect = unicodecsv.Sniffer().sniff(sample)
        fobj.seek(0)

    kwargs['encoding'] = encoding
    csv_reader = unicodecsv.reader(fobj, encoding=encoding, dialect=dialect)

    meta = {'imported_from': 'csv', 'filename': filename,}
    return create_table(csv_reader, meta=meta, *args, **kwargs)


def export_to_csv(table, filename_or_fobj=None, encoding='utf-8', *args, **kwargs):
    # TODO: will work only if table.fields is OrderedDict
    # TODO: should use fobj? What about creating a method like json.dumps?

    kwargs['encoding'] = encoding
    if filename_or_fobj is not None:
        _, fobj = get_filename_and_fobj(filename_or_fobj, mode='w')
    else:
        fobj = BytesIO()

    csv_writer = unicodecsv.writer(fobj, encoding=encoding)
    map(csv_writer.writerow, serialize(table, *args, **kwargs))

    if filename_or_fobj is not None:
        fobj.flush()
        return fobj
    else:
        fobj.seek(0)
        result = fobj.read()
        fobj.close()
        return result
