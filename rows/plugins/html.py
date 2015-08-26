# coding: utf-8

from __future__ import unicode_literals

import HTMLParser

from lxml.html import document_fromstring
from lxml.etree import tostring as to_string, strip_tags

from rows.utils import create_table


html_parser = HTMLParser.HTMLParser()


def _get_content(element):
    content = to_string(element)
    content = content[content.find('>') + 1:content.rfind('<')].strip()
    return html_parser.unescape(content)


def import_from_html(html, index=0, ignore_colspan=True, preserve_html=False,
                     row_tag='tr', column_tag='td|th', *args, **kwargs):
    # TODO: unescape before returning
    # html = html_parser.unescape(html.decode(encoding))

    html_tree = document_fromstring(html)
    tables = html_tree.xpath('//table')
    table = tables[index]

    strip_tags(table, 'thead')
    strip_tags(table, 'tbody')
    row_elements = table.xpath(row_tag)
    if not preserve_html:
        table_rows = [[value_element.text_content().strip()
                       for value_element in row.xpath(column_tag)]
                      for row in row_elements]
    else:
        table_rows = [[_get_content(value_element)
                       for value_element in row.xpath(column_tag)]
                      for row in row_elements]

    max_columns = max(len(row) for row in table_rows)
    if ignore_colspan:
        table_rows = filter(lambda row: len(row) == max_columns, table_rows)

    # TODO: lxml -> unicode?

    return create_table(table_rows, *args, **kwargs)


# TODO: replace 'None' with '' on export_to_*
def export_to_html(table, filename=None, encoding='utf-8'):
    fields = table.fields.keys()
    result = ['<table>', '', '  <thead>', '    <tr>']
    header = ['      <th>{}</th>'.format(field) for field in fields]
    result.extend(header)
    result.extend(['    </tr>', '  </thead>', '', '  <tbody>', ''])
    for index, row in enumerate(table, start=1):
        css_class = 'odd' if index % 2 == 1 else 'even'
        result.append('    <tr class="{}">'.format(css_class))
        for field in fields:
            value = table.fields[field].serialize(getattr(row, field),
                                                  encoding=encoding)
            result.append('      <td>')
            result.append(value)
            result.append('</td>')
        result.extend(['    </tr>', ''])
    result.extend(['  </tbody>', '</table>', ''])
    new_result = []
    for x in result:
        if isinstance(x, unicode):
            x = x.encode(encoding)
        new_result.append(x)
    html = '\n'.encode(encoding).join(new_result)

    if filename is not None:
        with open(filename, 'w') as fobj:
            fobj.write(html)
    else:
        return html


def tag_to_dict(html):
    element = document_fromstring(html).xpath('//html/body/child::*')[0]
    attributes = dict(element.attrib)
    attributes['text'] = element.text_content()
    return attributes


def tag_text(html):
    element = document_fromstring(html).xpath('//html/body/child::*')[0]
    return element.text_content()
