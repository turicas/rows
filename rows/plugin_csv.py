# coding: utf-8

# Copyright 2014 Álvaro Justen <https://github.com/turicas/rows/>
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

import csv
import logging

from .converters import TYPE_CONVERTERS
from .rows import LazyTable, Table
from .utils import convert_output


__all__ = ['import_from_csv', 'export_to_csv']

# TODO: replace 'None' with '' on export_to_*
# TODO: need converters in and out
# TODO: lazy=True|False
# TODO: use locale on output and/or .utils.convert_output

def import_from_csv(filename, encoding='utf-8', lazy=False, sample_size=None,
        log_level=logging.INFO, converters=None, force_types=None,
        delimiter=',', quotechar='"'):

    csv_reader = csv.reader(open(filename), delimiter=delimiter,
            quotechar=quotechar)
    unicode_csv_reader = ([field.decode(encoding) for field in row]
            for row in csv_reader)
    fields = unicode_csv_reader.next()

    if lazy:
        table = LazyTable(iterable=unicode_csv_reader, fields=fields)
        # TODO: _rows should be converted/types identified
    else:
        table = Table(fields=fields)
        table._rows = list(unicode_csv_reader)

    custom_converters = TYPE_CONVERTERS.copy()
    if converters is not None:
        custom_converters.update(converters)
    table.input_encoding = encoding
    table.converters = custom_converters
    if force_types is not None:
        table.identify_data_types(sample_size, skip=force_types.keys())
        table.types.update(force_types)
    else:
        table.identify_data_types(sample_size)

    return table

def export_to_csv(table, filename, encoding='utf-8', callback=None,
        callback_interval=1000):

    with open(filename, mode='w') as fobj:
        fields = table.fields
        csv_writer = csv.writer(fobj)
        csv_writer.writerow([unicode(field).encode(encoding)
            for field in fields])

        if callback is None:
            for row in table:
                csv_writer.writerow([convert_output(row[field]).encode(encoding)
                    for field in fields])
        else:
            for index, row in enumerate(table, start=1):
                csv_writer.writerow([convert_output(row[field]).encode(encoding)
                    for field in fields])
                if index % callback_interval == 0:
                    callback(index)
