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

from IPython.core.display import display, HTML
try:
    from rows.plugins.plugin_html import export_to_html
except ImportError:
    export_to_html = lambda x: b"<em>HTML plugin not found</em>"

def head(table, rows=10):
    # TODO: How do we test this?
    table_html = export_to_html(table).decode("utf-8")
    html_rows = table_html.split("<tr class=\"")
    if len(html_rows) > rows+1:
        table_html = "<tr class=\"".join(html_rows[:rows+1])
        table_html += "<tbody>\n\n<table>"
    display(HTML(table_html))

def tail(table, rows=10):
    table_html = export_to_html(table).decode("utf-8")
    html_rows = table_html.split("<tr class=\"")
    if len(html_rows) > rows+1:
        table_html = html_rows[0]
        table_html += "<tr class=\"".join(["    "]+html_rows[-rows:])
    display(HTML(table_html))
