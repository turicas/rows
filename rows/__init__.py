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

from rows import plugins
from rows.fileio import cfopen  # noqa
from rows.localization import locale_context  # noqa
from rows.operations import join, transform, transpose  # noqa
from rows.table import EagerTable, FlexibleTable, IncrementalTable, StreamTable, Table  # noqa
from rows.version import as_string as __version__  # noqa


def _set_lazy_function(plugin_name, function_name):
    """
    Set `import_from_*`/`export_to_*` attribute to rows module with an alias lazy function (only if it doesn't exist)

    The function will call the plugin-related function, but the plugin will be imported only when the function is
    called, on-demand (lazily).
    """
    import sys

    if hasattr(sys.modules[__name__], function_name):
        return

    docstring = (
        "Function to be called from a lazy loaded module. See `rows.plugins.{}.{}`".format(plugin_name, function_name)
    )

    def func(*args, **kwargs):
        plugin = getattr(plugins, plugin_name)
        func = getattr(plugin, function_name)
        return func(*args, **kwargs)
    func.__doc__ = docstring

    setattr(sys.modules[__name__], function_name, func)


# General imports
# Don't have dependencies or dependencies installed on `install_requires`

_set_lazy_function("csv", "export_to_csv")
_set_lazy_function("csv", "import_from_csv")
_set_lazy_function("dicts", "export_to_dicts")
_set_lazy_function("dicts", "import_from_dicts")
_set_lazy_function("html", "export_to_html")
_set_lazy_function("json", "export_to_json")
_set_lazy_function("json", "import_from_json")
_set_lazy_function("txt", "export_to_txt")
_set_lazy_function("txt", "import_from_txt")

# Have dependencies

if plugins.xpath is not None:
    _set_lazy_function("html", "import_from_html")
    _set_lazy_function("xpath", "import_from_xpath")

if plugins.ods is not None:
    _set_lazy_function("ods", "import_from_ods")

if plugins.sqlite is not None:
    _set_lazy_function("sqlite", "import_from_sqlite")
    _set_lazy_function("sqlite", "export_to_sqlite")

if plugins.xls is not None:
    _set_lazy_function("xls", "import_from_xls")
    _set_lazy_function("xls", "export_to_xls")

if plugins.xlsx is not None:
    _set_lazy_function("xlsx", "import_from_xlsx")
    _set_lazy_function("xlsx", "export_to_xlsx")

if plugins.parquet is not None:
    _set_lazy_function("parquet", "import_from_parquet")

if plugins.postgresql is not None:
    _set_lazy_function("postgresql", "import_from_postgresql")
    _set_lazy_function("postgresql", "export_to_postgresql")

if plugins.pdf is not None:
    _set_lazy_function("pdf", "import_from_pdf")
