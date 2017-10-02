# coding: utf-8

# Copyright 2014-2016 Álvaro Justen <https://github.com/turicas/rows/>
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

import six
from lxml.html import fromstring as tree_from_string

from rows.plugins.utils import create_table, get_filename_and_fobj

try:
    from HTMLParser import HTMLParser  # Python 2
except ImportError:
    from html.parser import HTMLParser  # Python 3






unescape = HTMLParser().unescape


def _get_row_data(fields_xpath):

    fields = list(fields_xpath.items())

    def get_data(row):
        data = []
        for field_name, field_xpath in fields:
            result = row.xpath(field_xpath)
            if result:
                result = ' '.join(text for text in
                                    map(six.text_type.strip,
                                        map(six.text_type,
                                            map(unescape, result)))
                                if text)
            else:
                result = None
            data.append(result)

        return data

    return get_data


def import_from_xpath(filename_or_fobj, rows_xpath, fields_xpath,
                      encoding='utf-8', *args, **kwargs):

    types = set([type(rows_xpath)] + \
                [type(xpath) for xpath in fields_xpath.values()])
    if types != set([six.text_type]):
        raise TypeError('XPath must be {}'.format(six.text_type.__name__))

    filename, fobj = get_filename_and_fobj(filename_or_fobj, mode='rb')
    xml = fobj.read().decode(encoding)
    # TODO: make it lazy (is it possible with lxml?)
    tree = tree_from_string(xml)
    row_elements = tree.xpath(rows_xpath)

    header = list(fields_xpath.keys())
    row_data = _get_row_data(fields_xpath)
    result_rows = list(map(row_data, row_elements))

    meta = {'imported_from': 'xpath',
            'filename': filename,
            'encoding': encoding,}
    return create_table([header] + result_rows, meta=meta, *args, **kwargs)


import_from_xpath.is_lazy = False
