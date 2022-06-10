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

import zipfile
from decimal import Decimal

from lxml.etree import fromstring as xml_from_string
from lxml.etree import tostring as xml_to_string

from rows.plugins.utils import create_table
from rows.utils import Source


def xpath(element, xpath, namespaces):
    return xml_from_string(xml_to_string(element)).xpath(xpath, namespaces=namespaces)


def attrib(cell, namespace, name):
    return cell.attrib["{{{}}}{}".format(namespace, name)]


def complete_with_None(lists, size):
    for element in lists:
        element.extend([None] * (size - len(element)))
        yield element


def sheet_names(filename_or_fobj):
    # TODO: setup/teardown must be methods of a class so we can reuse them
    source = Source.from_file(filename_or_fobj, plugin_name="ods")
    ods_file = zipfile.ZipFile(source.fobj)
    content_fobj = ods_file.open("content.xml")
    xml = content_fobj.read()  # will return bytes
    # TODO: read XML lazily?
    content_fobj.close()
    ods_file.close()
    source.fobj.close()

    document = xml_from_string(xml)
    namespaces = document.nsmap
    spreadsheet = document.xpath("//office:spreadsheet", namespaces=namespaces)[0]
    tables = xpath(spreadsheet, "//table:table", namespaces)
    name_attribute = f"{{{namespaces['table']}}}name"
    # TODO: unescape values
    return [table.attrib[name_attribute] for table in tables]


def import_from_ods(
    filename_or_fobj,
    index=0,
    start_row=None,
    start_column=None,
    end_row=None,
    end_column=None,
    *args,
    **kwargs,
):
    # TODO: unescape values

    source = Source.from_file(filename_or_fobj, plugin_name="ods")

    start_row = start_row if start_row is not None else 0
    end_row = end_row + 1 if end_row is not None else None
    start_column = start_column if start_column is not None else 0
    end_column = end_column + 1 if end_column is not None else None

    ods_file = zipfile.ZipFile(source.fobj)
    content_fobj = ods_file.open("content.xml")
    xml = content_fobj.read()  # will return bytes
    # TODO: read XML lazily?
    content_fobj.close()
    ods_file.close()

    document = xml_from_string(xml)
    namespaces = document.nsmap
    spreadsheet = document.xpath("//office:spreadsheet", namespaces=namespaces)[0]
    tables = xpath(spreadsheet, "//table:table", namespaces)
    table = tables[index]  # TODO: import spreadsheet by name
    try:
        table_name = attrib(table, namespaces["table"], "name")
    except KeyError:
        table_name = None

    table_rows_obj = xpath(table, "//table:table-row", namespaces)
    table_rows = []
    for row_obj in table_rows_obj:
        cells = list(reversed(xpath(row_obj, "//table:table-cell", namespaces)))
        if len(cells) == 1 and not cells[0].getchildren():
            continue  # Empty line(s), ignore
        row = []
        row_started = False
        for cell in cells:
            children = cell.getchildren()
            if not children:
                cell_value = None
                # TODO: check repeat
            else:
                # TODO: evalute 'boolean' and 'time' types
                value_type = attrib(cell, namespaces["office"], "value-type")
                if value_type == "date":
                    cell_value = attrib(cell, namespaces["office"], "date-value")
                elif value_type == "float":
                    cell_value = attrib(cell, namespaces["office"], "value")
                elif value_type == "percentage":
                    cell_value = attrib(cell, namespaces["office"], "value")
                    cell_value = Decimal(cell_value)
                    cell_value = "{:%}".format(cell_value)
                elif value_type == "string":
                    try:
                        # get computed string (from formula, for example)
                        cell_value = attrib(cell, namespaces["office"], "string-value")
                    except KeyError:
                        # computed string not present => get from <p>...</p>
                        cell_value = children[0].text
                else:  # value_type == some type we don't know
                    cell_value = children[0].text

            try:
                repeat = attrib(cell, namespaces["table"], "number-columns-repeated")
            except KeyError:
                row.append(cell_value)
                row_started = True
            else:
                cell_data = [cell_value for _ in range(int(repeat))]
                if set(cell_data) != set([None]) or row_started:
                    # This check will remove empty cells from the end
                    row.extend(cell_data)
                    row_started = True

        row = list(reversed(row))[start_column:end_column]
        if row and set(row) != set([None]):
            table_rows.append(row)

    table_rows = table_rows[start_row:end_row]
    max_length = max(len(row) for row in table_rows)
    full_rows = complete_with_None(table_rows, max_length)
    meta = {"imported_from": "ods", "source": source, "name": table_name}
    return create_table(full_rows, meta=meta, *args, **kwargs)
