# coding: utf-8

# Copyright 2014-2025 Álvaro Justen <https://github.com/turicas/rows/>
#    This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
#    Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
#    any later version.
#    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
#    warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
#    more details.
#    You should have received a copy of the GNU Lesser General Public License along with this program.  If not, see
#    <http://www.gnu.org/licenses/>.

"""Helper objects to make compatibility with older versions or external tools easier"""

from __future__ import unicode_literals

import sys
from collections import OrderedDict


DEFAULT_SAMPLE_ROWS = 20480  # Number of rows to sample from files when no schema is provided

PYTHON_VERSION = (sys.version_info.major, sys.version_info.minor, sys.version_info.micro)

if PYTHON_VERSION < (3, 0, 0):
    TEXT_TYPE = unicode
    BINARY_TYPE = str

    def lru_cache(user_func):
        # Actually NOT LRU, just a dummy cache for Python 2. This is only used in this module.

        internal_cache = {}
        def func(*args, **kwargs):
            cache_key = hash(tuple(list(args) + sorted(kwargs.items())))
            if cache_key not in internal_cache:
                result = user_func(*args, **kwargs)
                internal_cache[cache_key] = result
            else:
                result = internal_cache[cache_key]
            return result

        return func

else:
    from functools import lru_cache

    TEXT_TYPE = str
    BINARY_TYPE = bytes

if PYTHON_VERSION >= (3, 7, 0) or (PYTHON_VERSION >= (3, 6, 0) and PYTHON_IMPLEMENTATION == "CPython"):
    ORDERED_DICT = dict
    ORDERED_DICTS = (dict, OrderedDict)
else:
    ORDERED_DICT = OrderedDict
    ORDERED_DICTS = (OrderedDict,)

PYTHON_KEYWORDS_LOWER = {
    "false", "none", "true", "and", "as", "assert", "async", "await", "break", "class", "continue", "def", "del",
    "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
    "not", "or", "pass", "raise", "return", "try", "while", "with", "yield"
}
# Take from: `import keyword; set(key.lower() for key in keyword.kwlist)`

@lru_cache
def library_installed(module_name):
    if PYTHON_VERSION >= (3, 0, 0):
        from importlib.util import find_spec

        return bool(find_spec(module_name))

    else:
        from imp import find_module

        try:
            _ = find_module(module_name)
        except ImportError:
            return False
        else:
            return True
