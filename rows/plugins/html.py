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

import HTMLParser
import string

from lxml.html import document_fromstring
from lxml.etree import tostring as to_string, strip_tags

from rows.plugins.utils import (create_table, export_data,
                                get_filename_and_fobj, serialize)


unescape = HTMLParser.HTMLParser().unescape


def _get_content(element):
    content = to_string(element)
    content = content[content.find('>') + 1:content.rfind('<')].strip()
    return unescape(content)


def _get_row(row, column_tag, preserve_html, properties):
    if not preserve_html:
        data = map(extract_text_from_node, row.xpath(column_tag))
    else:
        data = map(_get_content, row.xpath(column_tag))

    if properties:
        data.append(dict(row.attrib))

    return data


def import_from_html(filename_or_fobj, encoding='utf-8', index=0,
                     ignore_colspan=True, preserve_html=False,
                     properties=False, table_tag='table', row_tag='tr',
                     column_tag='td|th', *args, **kwargs):

    filename, fobj = get_filename_and_fobj(filename_or_fobj)
    kwargs['encoding'] = encoding
    html = fobj.read().decode(encoding)
    html_tree = document_fromstring(html)
    tables = html_tree.xpath('//{}'.format(table_tag))
    table = tables[index]

    strip_tags(table, 'thead')
    strip_tags(table, 'tbody')
    row_elements = table.xpath(row_tag)

    table_rows = [_get_row(row,
                           column_tag=column_tag,
                           preserve_html=preserve_html,
                           properties=properties)
                  for row in row_elements]

    if properties:
        table_rows[0][-1] = 'properties'

    if preserve_html and kwargs.get('fields', None) is None:
        # The field names will be the first table row, so we need to strip HTML
        # from it even if `preserve_html` is `True` (it's `True` only for rows,
        # not for the header).
        table_rows[0] = map(extract_text_from_node, row_elements[0])

    max_columns = max(map(len, table_rows))
    if ignore_colspan:
        table_rows = filter(lambda row: len(row) == max_columns, table_rows)

    meta = {'imported_from': 'html', 'filename': filename,}
    return create_table(table_rows, meta=meta, *args, **kwargs)


def export_to_html(table, filename_or_fobj=None, encoding='utf-8', *args,
                   **kwargs):
    kwargs['encoding'] = encoding
    serialized_table = serialize(table, *args, **kwargs)
    fields = serialized_table.next()
    result = ['<table>\n\n', '  <thead>\n', '    <tr>\n']
    header = ['      <th> {} </th>\n'.format(field) for field in fields]
    result.extend(header)
    result.extend(['    </tr>\n', '  </thead>\n', '\n', '  <tbody>\n', '\n'])
    for index, row in enumerate(serialized_table, start=1):
        css_class = 'odd' if index % 2 == 1 else 'even'
        result.append('    <tr class="{}">\n'.format(css_class))
        for value in row:
            result.extend(['      <td> ', value, ' </td>\n'])
        result.append('    </tr>\n\n')
    result.append('  </tbody>\n\n</table>\n')
    new_result = [value.encode(encoding) if isinstance(value, unicode)
                  else value
                  for value in result]
    html = ''.encode(encoding).join(new_result)

    return export_data(filename_or_fobj, html)


def count_tables(filename_or_fobj, encoding='utf-8', table_tag='table'):
    filename, fobj = get_filename_and_fobj(filename_or_fobj)
    html = fobj.read().decode(encoding)
    html_tree = document_fromstring(html)
    tables = html_tree.xpath('//{}'.format(table_tag))
    return len(tables)


def tag_to_dict(html):
    "Extract tag's attributes into a `dict`"

    element = document_fromstring(html).xpath('//html/body/child::*')[0]
    attributes = dict(element.attrib)
    attributes['text'] = element.text_content()
    return attributes


def extract_text_from_html(html):
    'Extract text from a given HTML'

    return extract_text_from_node(document_fromstring(html))


def extract_text_from_node(node):
    'Extract text from a given lxml node'

    texts = map(string.strip,
                map(unescape,
                    node.xpath('.//text()')))
    return ' '.join(text for text in texts if text)
