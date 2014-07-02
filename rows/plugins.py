# coding: utf-8

# Copyright 2014 Álvaro Justen <https://github.com/turicas/rows/>
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

try:
    from .plugin_text import *
except ImportError:
    pass

try:
    from .plugin_csv import *
except ImportError:
    pass

try:
    from .plugin_html import *
except ImportError:
    pass

try:
    from .plugin_mysql import *
except ImportError:
    pass

try:
    from .plugin_JSON import *
except ImportError:
    pass
