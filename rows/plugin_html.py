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
from .converters import TYPE_CONVERTERS


__all__ = ['import_from_html', 'export_to_html']

# TODO: replace 'None' with '' on export_to_*
# TODO: need converters in and out
# TODO: lazy=True|False
# TODO: logging (?)

html_parser = HTMLParser.HTMLParser()

def import_from_html(html, fields=None, table_index=0, include_fields=None,
                     exclude_fields=None, converters=None, force_types=None):
    # TODO: unescape before returning
    # html = html_parser.unescape(html.decode(encoding))

    html_tree = html_element_tree(html)
    table_tree = html_tree.xpath('//table')
    try:
        table_tree = table_tree[table_index]
    except IndexError:
        raise IndexError('Table index {} not found'.format(table_index))

    table_html = to_string(table_tree)
    tr_elements = html_element_tree(table_html).xpath('//tr')
    rows = []
    for tr_element in tr_elements:
        td_elements = html_element_tree(to_string(tr_element)).xpath('//td')
        new_row = []
        for td_element in td_elements:
            data = u'\n'.join([x.strip()
                    for x in list(td_element.itertext(with_tail=False))])
            new_row.append(data)
        rows.append(new_row)

    # TODO: lxml -> unicode?

    # TODO: unescape
    if fields is None:
        fields = [x.strip() for x in rows[0]]
        rows = rows[1:]

    table = Table(fields=fields)
    table._rows = rows
    table.input_encoding = 'utf-8' # TODO: change this

    custom_converters = TYPE_CONVERTERS.copy()
    if converters is not None:
        custom_converters.update(converters)
    table.converters = custom_converters

    if force_types is not None:
        table.identify_data_types(sample_size=None, skip=force_types.keys())
        table.types.update(force_types)
    else:
        table.identify_data_types(sample_size=None)

    table._rows = [table.convert_row([x.strip() for x in row])
            for row in table._rows] # TODO: unescape

    to_exclude = set()
    if include_fields is not None:
        to_exclude = set(table.fields) - set(include_fields)
    elif exclude_fields is not None:
        to_exclude = exclude_fields
    for field in to_exclude:
        table.remove_field(field)

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
