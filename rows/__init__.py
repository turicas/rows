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

# General imports

from rows.operations import join, transform, transpose
from rows.table import Table
from rows.localization import locale_context


# Don't have dependencies or dependencies installed on `install_requires`

from rows.plugins._json import import_from_json, export_to_json
from rows.plugins.csv import import_from_csv, export_to_csv
from rows.plugins.txt import export_to_txt


# Have dependencies

try:
    from rows.plugins.xls import import_from_xls, export_to_xls
except ImportError:
    pass

try:
    from rows.plugins.html import import_from_html, export_to_html
except ImportError:
    pass


__version__ = '0.2.0-dev'
