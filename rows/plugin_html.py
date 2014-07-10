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

import HTMLParser

from lxml.etree import HTML as html_element_tree, tostring as to_string

from .rows import Table


__all__ = ['import_from_html', 'export_to_html']

# TODO: replace 'None' with '' on export_to_*
# TODO: need converters in and out
# TODO: lazy=True|False
# TODO: logging (?)

html_parser = HTMLParser.HTMLParser()

def import_from_html(html, table_index=1, encoding='utf-8'):
    # TODO: unescape before returning
    # html = html_parser.unescape(html.decode(encoding))

    if isinstance(html, str):
        html = html.decode(encoding)
        # TODO: support Python 3

    html_tree = html_element_tree(html)

    if isinstance(table_index, int):
        table_index = (table_index, )

    # select all tables with this depth
    table_tree = html_tree.xpath('//table[{}]'.format(table_index[0] + 1))[0]
    table_html = to_string(table_tree[0])
    # TODO: what about table_index[x > 0]?

    table_children = table_tree.getchildren()
    rows = []
    for row_child in table_children:

        # TODO: tbody, thead
        if row_child.tag != 'tr':
            continue

        new_row = []
        for column_child in row_child.getchildren():
            # TODO: what about th?
            if column_child.tag != 'td':
                continue
            new_row.append(list(column_child.itertext())[0])
        rows.append(new_row)

    # TODO: lxml -> unicode?

    table = Table(fields=[x.strip() for x in rows[0]]) # TODO: unescape
    table._rows = rows[1:]
    table.input_encoding = encoding
    table.identify_data_types(sample_size=None)
    table._rows = [table.convert_row([x.strip() for x in row])
            for row in table._rows] # TODO: unescape

    return table

def export_to_html(table, filename=None, encoding='utf-8'):
    fields = table.fields
    result = [u'<table>', u'', u'  <thead>', u'    <tr>']
    header = [u'      <th>{}</th>'.format(field) for field in fields]
    result.extend(header)
    result.extend([u'    </tr>', u'  </thead>', u'', u'  <tbody>', u''])
    for index, row in enumerate(table, start=1):
        css_class = u'odd' if index % 2 == 1 else u'even'
        result.append(u'    <tr class="{}">'.format(css_class))
        result.extend([u'      <td>{}</td>'.format(row[field] or u'')
            for field in fields])
        result.extend([u'    </tr>', u''])
    result.extend([u'  </tbody>', u'</table>', u''])
    html = u'\n'.join(result)

    if filename is not None:
        with open(filename, 'w') as fobj:
            fobj.write(html.encode(encoding))
    else:
        return html
