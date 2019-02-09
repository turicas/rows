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

import six

import rows.fields


@contextlib.contextmanager
def locale_context(name, category=locale.LC_ALL):

    old_name = locale.getlocale()
    if None not in old_name:
        old_name = ".".join(old_name)
    if isinstance(name, six.text_type):
        name = str(name)

    if old_name != name:
        locale.setlocale(category, name)

    rows.fields.SHOULD_NOT_USE_LOCALE = False
    try:
        yield
    finally:
        if old_name != name:
            locale.setlocale(category, old_name)

    rows.fields.SHOULD_NOT_USE_LOCALE = True
