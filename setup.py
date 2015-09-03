# coding: utf-8

from setuptools import setup


EXTRA_REQUIREMENTS = {
        'csv': ['unicodecsv'],
        'cli': ['click', 'requests'],
        'html': ['lxml'], # apt: libxslt-dev libxml2-dev
        'xls': ['xlrd', 'xlwt'], }
EXTRA_REQUIREMENTS['all'] = sum(EXTRA_REQUIREMENTS.values(), [])
INSTALL_REQUIREMENTS = EXTRA_REQUIREMENTS['csv'] + EXTRA_REQUIREMENTS['cli']
LONG_DESCRIPTION = '''
No matter in which format your tabular data is: rows will import it,
automatically detect types and give you high-level Python objects so you can
start working with the data instead of trying to parse it. It is also
locale-and-unicode aware. :)

See a quick start tutorial at:
    https://github.com/turicas/rows/blob/develop/README.md
'''.strip()


setup(name='rows',
      description=('A common, beautiful interface to tabular data, '
                   'no matter the format'),
      long_description=LONG_DESCRIPTION,
      version='0.2.0-dev',
      author=u'Álvaro Justen',
      author_email='alvarojusten@gmail.com',
      url='https://github.com/turicas/rows/',
      packages=['rows', 'rows.plugins'],
      install_requires=INSTALL_REQUIREMENTS,
      extras_require=EXTRA_REQUIREMENTS,
      keywords=['tabular', 'table', 'csv', 'xls', 'html', 'rows'],
      entry_points = {
          'console_scripts': [
              'rows = rows.cli:cli',
              ],
      },
      classifiers = [
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: GNU General Public License (GPL)',
          'Natural Language :: English',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2.7',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ]
)
