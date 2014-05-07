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

from .rows import LazyTable
from .utils import convert_output


__all__ = ['export_to_text']

# TODO: replace 'None' with '' on export_to_*
# TODO: need converters in and out
# TODO: lazy=True|False - probably only =False
# TODO: convert output using locale (grouping=True|False)

DASH = u'-'
PLUS = u'+'
PIPE = u'|'

def _max_column_sizes(table):
    max_sizes = {field: len(field) for field in table.fields}
    for row in table:
        for field, value in row.items():
            length = len(convert_output(value))
            if max_sizes[field] < length:
                max_sizes[field] = length
    return max_sizes

def export_to_text(table, filename, encoding='utf-8'):
    max_sizes = _max_column_sizes(table)
    if not len(table._rows):
        return u''

    fields = table.fields
    dashes = [DASH * (max_sizes[field] + 2) for field in fields]
    header = [field.center(max_sizes[field]) for field in fields]
    header = u'{} {} {}'.format(PIPE, u' {} '.format(PIPE).join(header), PIPE)
    split_line = PLUS + PLUS.join(dashes) + PLUS

    result = [split_line, header, split_line]
    for row in table:
        row_data = [convert_output(row[field]).rjust(max_sizes[field])
                for field in fields]
        result.append(u'{} {} {}'.format(PIPE,
            u' {} '.format(PIPE).join(row_data), PIPE))
    result.extend([split_line, u'\n'])

    data = u'\n'.join(result).encode(encoding)
    with open(filename, 'w') as fobj:
        fobj.write(data)
