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

from lxml.html import fromstring as tree_from_string
from lxml.etree import strip_tags
from lxml.etree import tostring as to_string

from rows.plugins.utils import create_table, get_filename_and_fobj


unescape = HTMLParser.HTMLParser().unescape

def _get_row_data(row, fields_xpath):
    row = tree_from_string(to_string(row))
    data = []
    for field_name, field_xpath in fields_xpath.items():
        result = row.xpath(field_xpath)
        if result:
            texts = map(string.strip, map(unescape, result))
            result = ' '.join(text for text in texts if text)
        else:
            result = None
        data.append(result)
    return data


def import_from_xpath(filename_or_fobj, rows_xpath, fields_xpath,
                      encoding='utf-8', *args, **kwargs):

    filename, fobj = get_filename_and_fobj(filename_or_fobj)
    kwargs['encoding'] = encoding
    xml = fobj.read().decode(encoding)
    tree = tree_from_string(xml)
    row_elements = tree.xpath(rows_xpath)

    header = fields_xpath.keys()
    result_rows = [_get_row_data(row, fields_xpath) for row in row_elements]

    meta = {'imported_from': 'xpath', 'filename': filename,}
    return create_table([header] + result_rows, meta=meta, *args, **kwargs)
