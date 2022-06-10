# coding: utf-8

# Copyright 2014-2022 Álvaro Justen <https://github.com/turicas/rows/>

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

from io import BytesIO

import six

try:
    from lxml.etree import strip_tags
    from lxml.etree import tostring as to_string
    from lxml.html import document_fromstring
except ImportError:
    has_lxml = False
else:
    has_lxml = True

from rows.plugins.utils import create_table, serialize
from rows.utils import Source

try:
    from HTMLParser import HTMLParser  # Python 2

    unescape = HTMLParser().unescape
except:
    import html  # Python 3

    unescape = html.unescape


try:
    from html import escape  # Python 3
except:
    from cgi import escape  # Python 2


def _get_content(element):
    return (element.text if element.text is not None else "") + "".join(
        to_string(child, encoding=six.text_type) for child in element.getchildren()
    )


def _get_row(row, column_tag, preserve_html, properties):
    if not preserve_html:
        data = list(map(_extract_node_text, row.xpath(column_tag)))
    else:
        data = list(map(_get_content, row.xpath(column_tag)))

    if properties:
        data.append(dict(row.attrib))

    return data


def import_from_html(
    filename_or_fobj,
    encoding="utf-8",
    index=0,
    ignore_colspan=True,
    preserve_html=False,
    properties=False,
    table_tag="table",
    row_tag="tr",
    column_tag="td|th",
    *args,
    **kwargs
):
    """Return rows.Table from HTML file."""

    source = Source.from_file(
        filename_or_fobj, plugin_name="html", mode="rb", encoding=encoding
    )

    html = source.fobj.read()
    if b"<?xml" not in html[:1024] or b"encoding" not in html[: html.find(b"?>") + 2]:
        html = html.decode(source.encoding)  # Regular HTML, not XHTML/XML

    html_tree = document_fromstring(html)
    tables = html_tree.xpath("//{}".format(table_tag))
    table = tables[index]
    # TODO: set meta's "name" from @id or @name (if available)

    strip_tags(table, "thead")
    strip_tags(table, "tbody")
    row_elements = table.xpath(row_tag)

    table_rows = [
        _get_row(
            row,
            column_tag=column_tag,
            preserve_html=preserve_html,
            properties=properties,
        )
        for row in row_elements
    ]

    if properties:
        table_rows[0][-1] = "properties"

    if preserve_html and kwargs.get("fields", None) is None:
        # The field names will be the first table row, so we need to strip HTML
        # from it even if `preserve_html` is `True` (it's `True` only for rows,
        # not for the header).
        table_rows[0] = list(map(_extract_node_text, row_elements[0]))

    if ignore_colspan:
        max_columns = max(map(len, table_rows))
        table_rows = [row for row in table_rows if len(row) == max_columns]

    meta = {"imported_from": "html", "source": source}
    return create_table(table_rows, meta=meta, *args, **kwargs)


def export_to_html(
    table, filename_or_fobj=None, encoding="utf-8", caption=False, *args, **kwargs
):
    """Export and return rows.Table data to HTML file."""

    return_data, should_close = False, None
    if filename_or_fobj is None:
        filename_or_fobj = BytesIO()
        return_data = should_close = True

    source = Source.from_file(
        filename_or_fobj,
        plugin_name="html",
        mode="wb",
        encoding=encoding,
        should_close=should_close,
    )

    serialized_table = serialize(table, *args, **kwargs)
    fields = next(serialized_table)
    result = ["<table>\n\n"]
    if caption and table.name:
        result.extend(["  <caption>", table.name, "</caption>\n\n"])
    result.extend(["  <thead>\n", "    <tr>\n"])
    # TODO: set @name/@id if self.meta["name"] is set
    header = ["      <th> {} </th>\n".format(field) for field in fields]
    result.extend(header)
    result.extend(["    </tr>\n", "  </thead>\n", "\n", "  <tbody>\n", "\n"])
    for index, row in enumerate(serialized_table, start=1):
        css_class = ("even", "odd")[index % 2]
        result.append(f'    <tr class="{css_class}">\n')
        for value in row:
            result.extend(["      <td> ", escape(value), " </td>\n"])
        result.append("    </tr>\n\n")
    result.append("  </tbody>\n\n</table>\n")
    html = "".join(result).encode(encoding)

    if return_data:
        result = html
    else:
        result = source.fobj
        source.fobj.write(html)
        source.fobj.flush()

    if source.should_close:
        source.fobj.close()

    return result


def _extract_node_text(node):
    """Extract text from a given lxml node."""

    texts = map(
        six.text_type.strip, map(six.text_type, map(unescape, node.xpath(".//text()")))
    )
    return " ".join(text for text in texts if text)


def count_tables(filename_or_fobj, encoding="utf-8", table_tag="table"):
    """Read a file passed by arg and return your table HTML tag count."""

    source = Source.from_file(
        filename_or_fobj, plugin_name="html", mode="rb", encoding=encoding
    )
    html = source.fobj.read().decode(source.encoding)
    html_tree = document_fromstring(html)
    tables = html_tree.xpath("//{}".format(table_tag))
    result = len(tables)

    if source.should_close:
        source.fobj.close()

    return result


def tag_to_dict(html):
    """Extract tag's attributes into a `dict`."""

    element = document_fromstring(html).xpath("//html/body/child::*")[0]
    attributes = dict(element.attrib)
    attributes["text"] = element.text_content()
    return attributes


def extract_text(html):
    """Extract text from a given HTML."""

    return _extract_node_text(document_fromstring(html))


def extract_links(html):
    """Extract the href values from a given HTML (returns a list of strings)."""

    return document_fromstring(html).xpath(".//@href")
