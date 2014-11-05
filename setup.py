# coding: utf-8

from setuptools import setup


setup(name='rows',
    description='Import and export tabular data easily with Python',
    long_description='',
    version='0.1.0.dev0',
    author=u'Álvaro Justen',
    author_email='alvarojusten@gmail.com',
    url='https://github.com/turicas/rows/',
    packages=['rows'],
    install_requires=[],
    extras_require = {
        'html': ['lxml'], # apt: libxslt-dev libxml2-dev
        'mysql': ['MySQL-Python'], # apt: libmariadbclient-dev libssl-dev
        'all': ['lxml', 'MySQL-Python'],
    },
    keywords=['tabular', 'csv', 'rows'],
    entry_points = {
        'console_scripts': [
            'rows = rows.cli:main',
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
