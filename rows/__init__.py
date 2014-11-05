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

import sys
import types

from .plugins import *

from .rows import Table, LazyTable, BaseTable, join


this = sys.modules[__name__]
import_methods = []

# take all available import/export methods from plugins
for attribute in dir(this):
    if attribute.startswith('import_from_'):
        import_methods.append(attribute)
    elif attribute.startswith('export_to_'):
        setattr(BaseTable, attribute,
                types.MethodType(getattr(this, attribute), None, BaseTable))
        # TODO: this line should be changed for python 3
        delattr(this, attribute)
    elif attribute.startswith('plugin_'):
        delattr(this, attribute)

# explicitly export Table, LazyTable and all import methods (for available
# plugins)
__all__ = ['Table', 'LazyTable'] + import_methods

# cleanup namespace
del BaseTable
del attribute
del import_methods
del plugins
del rows
del sys
del this
del types
