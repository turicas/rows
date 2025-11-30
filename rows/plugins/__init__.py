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

from __future__ import unicode_literals

from rows.compat import library_installed as _library_installed


class _LazyModule(object):

    def __init__(self, name, module_dot_notation, root_function_names=None):
        self.name = name
        self.module_dot_notation = module_dot_notation
        self.root_function_names = root_function_names

    def _load_module(self):
        import sys
        from importlib import import_module

        module = import_module(self.module_dot_notation)
        setattr(sys.modules[__name__], self.name, module)
        rows_module = sys.modules.get("rows")
        if rows_module and self.root_function_names is not None:
            for func_name in self.root_function_names:
                setattr(rows_module, func_name, getattr(module, func_name))
        return module

    def __dir__(self):
        module = self._load_module()
        return dir(module)

    def __getattr__(self, name):
        module = self._load_module()
        return getattr(module, name)


def _define_lazy_module(name, module_dot_notation, root_function_names=None):
    import sys

    this_module = sys.modules[__name__]
    if hasattr(this_module, name):
        return
    setattr(this_module, name, _LazyModule(name, module_dot_notation, root_function_names))


_define_lazy_module("csv", "rows.plugins.plugin_csv", ("import_from_csv", "export_to_csv"))
_define_lazy_module("dicts", "rows.plugins.plugin_dicts", ("import_from_dicts", "export_to_dicts"))
_define_lazy_module("json", "rows.plugins.plugin_json", ("import_from_json", "export_to_json"))
_define_lazy_module("txt", "rows.plugins.plugin_txt", ("import_from_txt", "export_to_txt"))

if _library_installed("lxml"):
    _define_lazy_module("ods", "rows.plugins.plugin_ods", ("import_from_ods",))
    _define_lazy_module("xpath", "rows.plugins.plugin_xpath", ("import_from_xpath",))
    _define_lazy_module("html", "rows.plugins.plugin_html", ("import_from_html", "export_to_html"))
else:
    _define_lazy_module("html", "rows.plugins.plugin_html", ("export_to_html"))
    ods = None
    xpath = None

if _library_installed("parquet"):
    _define_lazy_module("parquet", "rows.plugins.plugin_parquet", ("import_from_parquet",))
else:
    parquet = None

if _library_installed("cached_property") and (_library_installed("pdfminer") or _library_installed("fitz")):
    _define_lazy_module("pdf", "rows.plugins.plugin_pdf", ("import_from_pdf",))
else:
    pdf = None

if _library_installed("psycopg2"):
    _define_lazy_module(
        "postgresql", "rows.plugins.plugin_postgresql", ("import_from_postgresql", "export_to_postgresql")
    )
else:
    postgresql = None

if _library_installed("sqlite3"):
    _define_lazy_module("sqlite", "rows.plugins.plugin_sqlite", ("import_from_sqlite", "export_to_sqlite"))
else:
    sqlite = None

_has_xlrd = _library_installed("xlrd")
_has_xlwt = _library_installed("xlwt")
if _has_xlrd and _has_xlwt:
    _xls_functions = ("import_from_xls", "export_to_xls")
elif _has_xlrd:
    _xls_functions = ("import_from_xls",)
elif _has_xlwt:
    _xls_functions = ("export_to_xls",)
if _has_xlrd or _has_xlwt:
    _define_lazy_module("xls", "rows.plugins.plugin_xls", _xls_functions)
else:
    xls = None

if _library_installed("openpyxl"):
    _define_lazy_module("xlsx", "rows.plugins.plugin_xlsx", ("import_from_xlsx", "export_to_xlsx"))
else:
    xlsx = None
