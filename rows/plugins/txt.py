# coding: utf-8

# Copyright 2014-2017 Álvaro Justen <https://github.com/turicas/rows/>

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

import unicodedata
from collections import defaultdict

from rows.plugins.utils import (create_table, export_data,
                                get_filename_and_fobj, serialize)



single_frame_prefix = "BOX DRAWINGS LIGHT"
double_frame_prefix = "BOX DRAWINGS DOUBLE"
frame_parts = [name.strip() for name in """
    VERTICAL, HORIZONTAL, DOWN AND RIGHT, DOWN AND LEFT,
    UP AND RIGHT, UP AND LEFT, VERTICAL AND LEFT, VERTICAL AND RIGHT,
    DOWN AND HORIZONTAL, UP AND HORIZONTAL, VERTICAL AND HORIZONTAL""".split(',')
]

SINGLE_FRAME = {
    name.strip(): unicodedata.lookup(
        ' '.join((single_frame_prefix, name.strip())))
    for name in frame_parts
}

DOUBLE_FRAME = {
    name.strip(): unicodedata.lookup(
        ' '.join((double_frame_prefix, name.strip())))
    for name in frame_parts
}

ASCII_FRAME = defaultdict(lambda: '+')
ASCII_FRAME['HORIZONTAL'] = '-'
ASCII_FRAME['VERTICAL'] = '|'

NONE_FRAME = defaultdict(lambda: ' ')

FRAMES = {
    'None': NONE_FRAME,
    'ASCII': ASCII_FRAME,
    'single': SINGLE_FRAME,
    'double': DOUBLE_FRAME,
}

del single_frame_prefix, double_frame_prefix, frame_parts
del NONE_FRAME, ASCII_FRAME, SINGLE_FRAME, DOUBLE_FRAME


def _max_column_sizes(field_names, table_rows):
    columns = zip(*([field_names] + table_rows))
    return {field_name: max(len(value) for value in column)
            for field_name, column in zip(field_names, columns)}


def import_from_txt(filename_or_fobj, encoding='utf-8', *args, **kwargs):
    # TODO: should be able to change DASH, PLUS and PIPE

    DASH, PLUS, PIPE = '-+|'

    filename, fobj = get_filename_and_fobj(filename_or_fobj, mode='rb')
    contents = fobj.read().decode(encoding).strip().splitlines()

    # remove '+----+----+' lines
    contents = contents[1:-1]
    del contents[1]

    table_rows = [[value.strip() for value in row.split(PIPE)[1:-1]]
                  for row in contents]
    meta = {'imported_from': 'txt',
            'filename': filename,
            'encoding': encoding,}
    return create_table(table_rows, meta=meta, *args, **kwargs)


def export_to_txt(table, filename_or_fobj=None, encoding=None,
                  frame_style="ASCII", *args, **kwargs):
    '''Export a `rows.Table` to text

    This function can return the result as a string or save into a file (via
    filename or file-like object).

    `encoding` could be `None` if no filename/file-like object is specified,
    then the return type will be `six.text_type`.

    `frame_style`: will select the frame style to be printed around data.
    Valid values are: ('None', 'ASCII', 'single', 'double') - ASCII is default.
    Warning: no checks are made to check the desired encoding allows the
    characters needed by single and double frame styles.
    '''
    # TODO: will work only if table.fields is OrderedDict

    try:
        frame = FRAMES[frame_style]
    except KeyError as error:
        raise ValueError(
            "Invalid frame style '{}'. Use one of None, "
            "'ASCII', 'single' or 'double'.".format(frame_style)
        )

    serialized_table = serialize(table, *args, **kwargs)
    field_names = next(serialized_table)
    table_rows = list(serialized_table)
    max_sizes = _max_column_sizes(field_names, table_rows)

    dashes = [frame['HORIZONTAL'] * (max_sizes[field] + 2) for field in field_names]
    header = [field.center(max_sizes[field]) for field in field_names]
    header = '{0} {1} {0}'.format(
        frame['VERTICAL'],
        ' {} '.format(frame['VERTICAL']).join(header)
    )
    top_split_line = (
        frame['DOWN AND RIGHT'] +
        frame['DOWN AND HORIZONTAL'].join(dashes) +
        frame['DOWN AND LEFT']
    )

    body_split_line = (
        frame['VERTICAL AND RIGHT'] +
        frame['VERTICAL AND HORIZONTAL'].join(dashes) +
        frame['VERTICAL AND LEFT']
    )

    botton_split_line = (
        frame['UP AND RIGHT'] +
        frame['UP AND HORIZONTAL'].join(dashes) +
        frame['UP AND LEFT']
    )


    result = [top_split_line, header, body_split_line]
    for row in table_rows:
        values = [value.rjust(max_sizes[field_name])
                  for field_name, value in zip(field_names, row)]
        row_data = ' {} '.format(frame['VERTICAL']).join(values)
        result.append('{0} {1} {0}'.format(frame['VERTICAL'], row_data))
    result.extend([botton_split_line, ''])
    data = '\n'.join(result)

    if encoding is not None:
        data = data.encode(encoding)

    return export_data(filename_or_fobj, data, mode='wb')
