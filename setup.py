# coding: utf-8

from setuptools import setup


setup(name='rows',
    description='Import and export tabular data easily with Python',
    long_description='',
    version='0.1.1-dev',
    author=u'Álvaro Justen',
    author_email='alvarojusten@gmail.com',
    url='https://github.com/turicas/rows/',
    packages=['rows', 'rows.plugins'],
    install_requires=['unicodecsv', 'click', 'filemagic', 'requests'],
    extras_require = {
        'csv': ['unicodecsv'],
        'html': ['lxml'], # apt: libxslt-dev libxml2-dev
        'cli': ['click', 'filemagic', 'requests'],
        'xls': ['xlrd', 'xlwt'],
        'all': ['unicodecsv',
                'lxml',
                'click', 'filemagic', 'requests',
                'xlrd', 'xlwt'],
    },
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
