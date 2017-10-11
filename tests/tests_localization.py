# coding: utf-8

"""Copyright 2014-2017 Álvaro Justen <https://github.com/turicas/rows/>

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU Lesser General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU Lesser General Public License for more details.

   You should have received a copy of the GNU Lesser General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>."""

from __future__ import unicode_literals

import platform
import unittest

import rows
import rows.fields
from rows.localization import locale_context


class LocalizationTestCase(unittest.TestCase):

    def test_locale_context_present_in_main_namespace(self):
        self.assertIn('locale_context', dir(rows))
        self.assertIs(locale_context, rows.locale_context)

    def test_locale_context(self):
        self.assertTrue(rows.fields.SHOULD_NOT_USE_LOCALE)
        if platform.system() == 'Windows':
            name = str('ptb_bra')
        else:
            name = 'pt_BR.UTF-8'
        with locale_context(name):
            self.assertFalse(rows.fields.SHOULD_NOT_USE_LOCALE)
        self.assertTrue(rows.fields.SHOULD_NOT_USE_LOCALE)
