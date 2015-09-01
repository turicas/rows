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

from rows.operations import serialize
from rows.utils import get_filename_and_fobj

DASH, PLUS, PIPE = '-', '+', '|'

def _max_column_sizes(table, encoding, *args, **kwargs):
    header = table.fields.keys()
    max_sizes = {field_name: len(field_name) for field_name in header}
    for row in serialize(table, encoding=encoding, *args, **kwargs):
        for field_name, value in zip(header, row):
            length = len(value)
            if max_sizes[field_name] < length:
                max_sizes[field_name] = length
    return max_sizes


def export_to_txt(table, filename_or_fobj, encoding='utf-8', *args, **kwargs):
    # TODO: will work only if table.fields is OrderedDict
    # TODO: should use fobj? What about creating a method like json.dumps?

    filename, fobj = get_filename_and_fobj(filename_or_fobj, mode='w')
    max_sizes = _max_column_sizes(table, encoding, *args, **kwargs)

    fields = table.fields.keys()
    dashes = [DASH * (max_sizes[field] + 2) for field in fields]
    header = [field.center(max_sizes[field]) for field in fields]
    header = '{} {} {}'.format(PIPE, ' {} '.format(PIPE).join(header), PIPE)
    split_line = PLUS + PLUS.join(dashes) + PLUS

    result = [split_line, header, split_line]
    for row in serialize(table):
        values = [value.rjust(max_sizes[field_name])
                  for field_name, value in zip(fields, row)]
        row_data = ' {} '.format(PIPE).join(values)
        result.append('{} {} {}'.format(PIPE, row_data, PIPE))
    result.extend([split_line, '\n'])

    data = '\n'.join(result).encode(encoding)

    fobj.write(data)
    fobj.flush()
    return fobj
