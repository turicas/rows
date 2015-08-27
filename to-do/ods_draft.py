# coding: utf-8

import HTMLParser
import zipfile

from re import compile as regexp_compile, DOTALL
from unicodedata import normalize


html_parser = HTMLParser.HTMLParser()
regexp_tags = regexp_compile(r'<[ \t]*[a-zA-Z0-9!"./_-]*[^>]*>', flags=DOTALL)
regexp_comment = regexp_compile(r'<!--.*?-->', flags=DOTALL)

regexp_ods_table = regexp_compile(r'(<table:table [^>]*>)(.*?)'
                                  r'(</table:table>)',
                                  flags=DOTALL)
regexp_ods_table_row = regexp_compile(r'(<table:table-row[^>]*>)(.*?)'
                                      r'(</table:table-row>)', flags=DOTALL)
regexp_ods_table_cell = regexp_compile(r'(<table:table-cell[^>]*>)(.*?)'
                                       r'(</table:table-cell>)', flags=DOTALL)

# TODO: encoding?
# TODO: replace &...;
# TODO: name/id of tables
# TODO: re.MULTILINE
# TODO: identify types
# TODO: clear empty rows?
# TODO: clear non-table rows?


def tables_ods(filename, headers=False, strip_xml=True):
    zip_fobj = zipfile.ZipFile(filename)
    content = zip_fobj.open('content.xml').read()
    zip_fobj.close()
    return _tables_ods(content, headers, strip_xml)

def _tables_ods(xml, headers, strip_xml):
    result = []
    ods_tables = regexp_ods_table.split(xml)[2::4]
    for table_ods in ods_tables:
        table_data = []
        rows = regexp_ods_table_row.split(table_ods)[2::4]
        if strip_xml:
            for row_data in rows:
                cells = regexp_ods_table_cell.split(row_data)[2::4]
                table_data.append([remove_html(field) for field in cells])
        else:
            for row_data in rows:
                cells = regexp_ods_table_cell.split(row_data)[2::4]
                table_data.append([field.strip() for field in cells])
        if headers:
            header, rows = table_data[0], table_data[1:]
            result.append([dict(zip(header, row)) for row in rows])
        else:
            result.append(table_data)
    return result
