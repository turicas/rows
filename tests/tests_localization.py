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

from __future__ import unicode_literals

import locale
import platform

import rows
import rows.fields
from rows.localization import locale_context
from rows.compat import TEXT_TYPE


def test_locale_context_present_in_main_namespace():
    assert "locale_context" in dir(rows)
    assert locale_context is rows.locale_context


def test_locale_context():
    assert rows.fields.SHOULD_NOT_USE_LOCALE
    if platform.system() == "Windows":
        name = TEXT_TYPE("ptb_bra")
    else:
        name = "pt_BR.UTF-8"
    with locale_context(name):
        assert not rows.fields.SHOULD_NOT_USE_LOCALE
    assert rows.fields.SHOULD_NOT_USE_LOCALE


def test_locale_context_restores_on_exception():
    initial_locale = locale.getlocale()
    locale.setlocale(locale.LC_ALL, ("en_US", "UTF-8"))
    assert locale.getlocale() == ("en_US", "UTF-8")
    try:
        with locale_context("pt_BR.UTF-8"):
            assert locale.getlocale(locale.LC_ALL) == ("pt_BR", "UTF-8")
            raise RuntimeError("Test Exception")
    except RuntimeError:
        pass
    locale_after = locale.getlocale()
    locale.setlocale(locale.LC_ALL, initial_locale)
    assert locale_after == ("en_US", "UTF-8")
