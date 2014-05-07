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

from lxml.etree import HTML as html_element_tree

from .rows import Table


__all__ = ['import_from_html', 'export_to_html']

# TODO: replace 'None' with '' on export_to_*
# TODO: need converters in and out
# TODO: lazy=True|False
# TODO: logging (?)

html_parser = HTMLParser.HTMLParser()

def import_from_html(html, table_index=0, encoding='utf-8'):
    html = html_parser.unescape(html.decode(encoding))
    html_tree = html_element_tree(html)

    html_table = html_tree.xpath('//table')[table_index]
    rows = [[list(child.itertext())[0] for child in tr.getchildren()]
            for tr in html_table.xpath('//tr')]

    table = Table(fields=rows[0])
    table._rows = rows[1:]
    table.input_encoding = encoding
    table.identify_data_types(sample_size=None)
    table._rows = [table.convert_row(row) for row in table._rows]

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
