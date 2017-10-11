# coding: utf-8

# Copyright 2014-2017 Álvaro Justen <https://github.com/turicas/rows/>

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

from . import plugin_json as json  # NOQA
from . import dicts as dicts  # NOQA
from . import plugin_csv as csv  # NOQA
from . import txt as txt  # NOQA

try:
    from . import plugin_html as html
except ImportError:
    html = None

try:
    from . import xpath as xpath
except ImportError:
    xpath = None

try:
    from . import ods as ods
except ImportError:
    ods = None

try:
    from . import sqlite as sqlite
except ImportError:
    sqlite = None

try:
    from . import xls as xls
except ImportError:
    xls = None

try:
    from . import xlsx as xlsx
except ImportError:
    xlsx = None

try:
    from . import plugin_parquet as parquet
except ImportError:
    parquet = None

try:
    from . import postgresql as postgresql
except ImportError:
    postgresql = None
