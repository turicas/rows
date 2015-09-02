# coding: utf-8

from __future__ import unicode_literals

import contextlib
import locale
import types

import rows.fields


@contextlib.contextmanager
def locale_context(name, category=locale.LC_ALL):

    old_name = locale.getlocale(category)
    if isinstance(name, types.UnicodeType):
        name = str(name)
    locale.setlocale(category, name)
    rows.fields.SHOULD_NOT_USE_LOCALE = False
    try:
        yield
    finally:
        locale.setlocale(category, old_name)
    rows.fields.SHOULD_NOT_USE_LOCALE = True
