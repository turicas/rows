# coding: utf-8

from __future__ import unicode_literals

import HTMLParser

from lxml.etree import HTML as html_element_tree, tostring as to_string

from rows.fields import detect_field_types
from rows.table import Table
from rows.utils import slug


html_parser = HTMLParser.HTMLParser()

def import_from_html(html, fields=None, table_index=0, ignore_colspan=True,
                     force_headers=None):
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
    table_rows = []
    for tr_element in tr_elements:
        # TODO: test 'td' and 'th'
        td_elements = html_element_tree(to_string(tr_element)).xpath('//td')
        td_elements += html_element_tree(to_string(tr_element)).xpath('//th')
        new_row = []
        for td_element in td_elements:
            data = u'\n'.join([x.strip()
                    for x in list(td_element.itertext(with_tail=False))])
            new_row.append(data)
        table_rows.append(new_row)

    max_columns = max(len(row) for row in table_rows)
    if ignore_colspan:
        table_rows = filter(lambda row: len(row) == max_columns, table_rows)

    # TODO: lxml -> unicode?

    if fields is not None:
        assert len(fields) == max_columns
        header = [slug(field_name) for field_name in fields.keys()]
    else:
        if force_headers is None:
            header = [x.strip() for x in table_rows[0]]
            # TODO: test this feature
            new_header = []
            for index, field_name in enumerate(header):
                if not field_name:
                    field_name = 'field_{}'.format(index)
                new_header.append(field_name)
            header = [slug(field_name) for field_name in new_header]
            table_rows = table_rows[1:]
        else:
            header = force_headers
        fields = detect_field_types(header, table_rows, encoding='utf-8')

    table = Table(fields=fields)
    for row in table_rows:
        table.append({field_name: value.strip()
                      for field_name, value in zip(header, row)})
    return table


# TODO: replace 'None' with '' on export_to_*
def export_to_html(table, filename=None, encoding='utf-8'):
    fields = table.fields.keys()
    result = [u'<table>', u'', u'  <thead>', u'    <tr>']
    header = [u'      <th>{}</th>'.format(field) for field in fields]
    result.extend(header)
    result.extend([u'    </tr>', u'  </thead>', u'', u'  <tbody>', u''])
    for index, row in enumerate(table, start=1):
        css_class = u'odd' if index % 2 == 1 else u'even'
        result.append(u'    <tr class="{}">'.format(css_class))
        for field in fields:
            value = table.fields[field].serialize(getattr(row, field),
                                                  encoding=encoding)
            result.append(u'      <td>')
            result.append(value)
            result.append(u'</td>')
        result.extend([u'    </tr>', u''])
    result.extend([u'  </tbody>', u'</table>', u''])
    new_result = []
    for x in result:
        if isinstance(x, unicode):
            x = x.encode(encoding)
        new_result.append(x)
    html = u'\n'.encode(encoding).join(new_result)

    if filename is not None:
        with open(filename, 'w') as fobj:
            fobj.write(html)
    else:
        return html
