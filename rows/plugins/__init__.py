# coding: utf-8

# Copyright 2014-2018 Álvaro Justen <https://github.com/turicas/rows/>

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
from types import ModuleType

import six

from . import plugin_json as json  # NOQA
from . import dicts as dicts  # NOQA
from . import plugin_csv as csv  # NOQA
from . import txt as txt  # NOQA

disabled = {}

def stub_factory(name, modules):
    if isinstance(modules, six.text_type):
        modules = [modules]

    message_template = "Plugin '{0}' disabled: requires install of package{1} {2}."
    message = message_template.format(
        name,
        '' if len(modules) == 1 else 's',
        ', '.join("'{}'".format(module) for module in modules),
    )

    class ModuleStub(ModuleType):
        def __repr__(self):
            return 'Plugin stub: "{}"'.format(self.__doc__)

    if six.PY2:
        name = name.encode('utf-8')
        message = message.encode('utf-8')
    return ModuleStub(name, message)

try:
    from . import plugin_html as html
except ImportError:
    html = stub_factory('html', 'lxml')
    disabled['html'] = html.__doc__

try:
    from . import xpath as xpath
except ImportError:
    xpath = stub_factory('xpath', 'lxml')
    disabled['xpath'] = xpath.__doc__

try:
    from . import ods as ods
except ImportError:
    ods = stub_factory('ods', 'lxml')
    disabled['ods'] = ods.__doc__

try:
    from . import sqlite as sqlite
except ImportError:
    sqlite = stub_factory('sqlite', 'sqlite3')
    disabled['sqlite'] = sqlite.__doc__

try:
    from . import xls as xls
except ImportError:
    xls = stub_factory('xls', ['xlrd', 'xlwt'])
    disabled['xls'] = xls.__doc__

try:
    from . import xlsx as xlsx
except ImportError:
    xlsx = stub_factory('xlsx', 'openpyxml')
    disabled['xlsx'] = xlsx.__doc__

try:
    from . import plugin_parquet as parquet
except ImportError:
    parquet = stub_factory('parquet', 'parquet>=1.1')
    disabled['parquet'] = parquet.__doc__
