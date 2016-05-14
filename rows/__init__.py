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
"""
About
-----

No matter in which format your tabular data is: rows will import it,
automatically detect types and give you high-level Python objects so you can
start working with the data instead of trying to parse it. It is also
locale-and-unicode aware. :)

Architecture
-------------

The library is composed by:

* A common interface to tabular data (the Table class)
* A set of plugins to populate Table objects (CSV, XLS, HTML, TXT, JSON, SQLite
  -- more coming soon!)
* A set of common fields (such as BoolField, IntegerField) which know exactly
  how to serialize and deserialize data for each object type you'll get
* A set of utilities (such as field type recognition) to help working with
  tabular data
* A command-line interface so you can have easy access to the most used
  features: convert between formats, sum, join and sort tables.
"""
from __future__ import unicode_literals

# General imports

from rows.operations import join, transform, transpose
from rows.table import Table, FlexibleTable
from rows.localization import locale_context


# Don't have dependencies or dependencies installed on `install_requires`

from rows.plugins._json import import_from_json, export_to_json
from rows.plugins.csv import import_from_csv, export_to_csv
from rows.plugins.txt import import_from_txt, export_to_txt


# Have dependencies

try:
    from rows.plugins.html import import_from_html, export_to_html
    from rows.plugins.xpath import import_from_xpath
except ImportError:
    pass

try:
    from rows.plugins.ods import import_from_ods
except ImportError:
    pass

try:
    from rows.plugins.sqlite import import_from_sqlite, export_to_sqlite
except ImportError:
    pass

try:
    from rows.plugins.xls import import_from_xls, export_to_xls
except ImportError:
    pass

try:
    from rows.plugins.xlsx import import_from_xlsx, export_to_xlsx
except ImportError:
    pass

try:
    from rows.plugins._parquet import import_from_parquet
except ImportError:
    pass


__version__ = '0.2.0dev'
