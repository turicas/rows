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

import unittest

from types import ModuleType
import mock

try:
    reload
except NameError:
    from imp import reload


class DisabledPluginsTestCase(unittest.TestCase):
    """Test mechanism for graceful disabling of missing plug-ins.

    Just verifies that the friendly system
    made to leave proper messages around when plug-ins are not
    available due to missing packages is in place
    """
    def setUp(self):
        pass

    def test_stub_factory_returns_stub_module(self):
        from rows.plugins import stub_factory
        result = stub_factory("xml", "lxml")
        assert isinstance (result, ModuleType)
        assert "lxml" in result.__doc__

    def test_stub_module_is_available_on_import_failure(self):
        """Test if on import failure of a plug-in, it is shown in 'rows.plugins.disabled'."""

        import builtins
        import sys
        _imp = builtins.__import__

        # function to wrap internal importing system
        # and force import error on testes plugin-name:

        def import_blow(*args):
            if args[3] and args[3][0] == "plugin_html":
                raise ImportError
            return _imp(*args)


        # "Uninmport" plugins if they by chance have already been imported;
        sys.modules.pop("rows.plugins", None)
        sys.modules.pop("rows.plugins.html", None)
        sys.modules.pop("rows.plugins.plugin_html", None)

        with mock.patch("builtins.__import__", new=import_blow):
            import rows.plugins

        self.assertIn("html", rows.plugins.disabled)


