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

# TODO: replace 'None' with '' on export_to_*
# TODO: need converters in and out
# TODO: lazy=True|False - probably only =False
# TODO: convert output using locale (grouping=True|False)
# TODO: support Python 3
# TODO: add `import_from_text`?

from .utils import convert_output


__all__ = ['export_to_text']
DASH, PLUS, PIPE = u'-', u'+', u'|'

def _max_column_sizes(table):
    max_sizes = {field: len(field) for field in table.fields}
    for row in table:
        for field, value in row.items():
            length = len(convert_output(value))
            if max_sizes[field] < length:
                max_sizes[field] = length
    return max_sizes

def _encode(text, encoding):
    if encoding is None:
        return text
    else:
        return text.encode(encoding)

def export_to_text(table, filename_or_fobj=None, encoding=None, dash=DASH,
        plus=PLUS, pipe=PIPE):
    '''Export `Table` object to text.

    If `filename_or_fobj` is provided, use it to write the result. If not,
    return the string/unicode object.

    The table borders/design can be customized using `dash`, `plus` and `pipe`
    parameters.
    '''
    if filename_or_fobj is not None and encoding is None:
        raise ValueError('Encoding needed to exporto to file.')

    max_sizes = _max_column_sizes(table)
    if not len(table._rows):
        return _encode(u'', encoding)

    fields = table.fields
    dashes = [dash * (max_sizes[field] + 2) for field in fields]
    header = [field.center(max_sizes[field])
            for field in fields]
    header = u'{} {} {}'.format(pipe, u' {} '.format(pipe).join(header), pipe)
    split_line = plus + plus.join(dashes) + plus

    result = [split_line, header, split_line]
    for row in table:
        row_data = [convert_output(row[field]).rjust(max_sizes[field])
                for field in fields]
        result.append(u'{} {} {}'.format(pipe,
            u' {} '.format(pipe).join(row_data), pipe))
    result.extend([split_line, u'\n'])

    data = _encode(u'\n'.join(result), encoding)

    if filename_or_fobj is None:
        return data
    else:
        if hasattr(filename_or_fobj, 'read'):
            filename_or_fobj.write(data)
        else:
            with open(filename_or_fobj, 'w') as fobj:
                fobj.write(data)
