# coding: utf-8

# Copyright 2014-2019 Álvaro Justen <https://github.com/turicas/rows/>

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

import contextlib
import locale

import rows.fields
from rows.compat import TEXT_TYPE

try:
    # Force to use all categories in C locale by default
    locale.setlocale(locale.LC_ALL, "C")
except locale.Error:
    pass


@contextlib.contextmanager
def locale_context(name, category=locale.LC_ALL):
    """
    Enables rows locale-aware features

    `name` can be:
    - A string with only the language, like in `"pt_BR"`
    - A string with the language and the encoding, like in `"pt_BR.UTF-8"`
    - A tuple with the language and the encoding, like in `("pt_BR", "UTF-8")`
    """
    old_setting = old_lang, old_encoding = locale.getlocale()
    if isinstance(name, TEXT_TYPE):
        name = TEXT_TYPE(name)
        if "." in name:
            lang, encoding = name.split(".")
        else:
            lang = name
            encoding = old_encoding
    if isinstance(name, tuple):
        lang, encoding = name
    new_setting = lang, encoding

    try:
        if old_setting != new_setting:
            locale.setlocale(category, new_setting)
        rows.fields.SHOULD_NOT_USE_LOCALE = False
        yield
    finally:
        if old_setting != new_setting:
            locale.setlocale(category, old_setting)
        rows.fields.SHOULD_NOT_USE_LOCALE = True
