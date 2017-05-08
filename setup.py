# coding: utf-8

# Copyright 2014-2016 Álvaro Justen <https://github.com/turicas/rows/>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from setuptools import setup


EXTRA_REQUIREMENTS = {
    'csv': ['unicodecsv'],
    'cli': ['click', 'requests'],
    'html': ['lxml'],  # apt: libxslt-dev libxml2-dev
    'ods': ['lxml'],
    'parquet': ['parquet>=1.1'],
    'xls': ['xlrd', 'xlwt'],
    'xlsx': ['openpyxl'],
    'xpath': ['lxml'],
    'detect': ['file-magic'],
}
EXTRA_REQUIREMENTS['all'] = sum(EXTRA_REQUIREMENTS.values(), [])
INSTALL_REQUIREMENTS = ['six'] + EXTRA_REQUIREMENTS['csv']
LONG_DESCRIPTION = '''
No matter in which format your tabular data is: rows will import it,
automatically detect types and give you high-level Python objects so you can
start working with the data instead of trying to parse it. It is also
locale-and-unicode aware. :)

Read the documentation and learn how simple is to use it: http://turicas.info/rows
'''.strip()


setup(name='rows',
      description=('A common, beautiful interface to tabular data, '
                   'no matter the format'),
      long_description=LONG_DESCRIPTION,
      version='0.3.2dev0',
      author='Álvaro Justen',
      author_email='alvarojusten@gmail.com',
      url='https://github.com/turicas/rows/',
      packages=['rows', 'rows.plugins'],
      install_requires=INSTALL_REQUIREMENTS,
      extras_require=EXTRA_REQUIREMENTS,
      keywords='tabular table csv xls xlsx xpath ods sqlite html rows data opendata',
      entry_points={
          'console_scripts': [
              'rows = rows.cli:cli',
          ],
      },
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: Science/Research',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Natural Language :: English',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.5',
          'Topic :: Database',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: Text Processing :: Markup :: HTML',
          'Topic :: Utilities',
      ])
