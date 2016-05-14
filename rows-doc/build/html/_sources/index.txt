.. Rows documentation master file, created by
   sphinx-quickstart on Tue Oct 13 14:40:03 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Rows
================

.. automodule:: rows
   :members: __init__

Quick Start
============

Do you want to read a **table from a HTML page**? It's simple :)

Let's say you want to know all the Academic Award-winning films

::

    from io import BytesIO

    import requests
    import rows

    # Get data
    url = 'https://en.wikipedia.org/wiki/List_of_Academy_Award-winning_films'
    response = requests.get(url)
    html = response.content

    # Parse
    table = rows.import_from_html(BytesIO(html), index=0)

    # Sort
    by_name = sorted(table)
    by_nominations = sorted(table, key=lambda x: x.nominations)
    by_year = sorted(table, key=lambda x: x.year)

How to install
===============

Simple and elegant: ``pip install rows``

If you want another forms of installation please `click here <https://github.com/turicas/rows/blob/develop/README.md#installation>`_

The plugins `csv`, `txt`, `json` and `sqlite` are built-in by default but if
you want to use another one you need to explicitly install its dependencies,
for example:
::

    pip install rows[html]
    pip install rows[xls]

You also need to install some dependencies to use the [command-line
interface](#command-line-interface). You can do it installing the `cli` extra
requirement:
::

    pip install rows[cli]

And - easily - you can install all the dependencies by using the `all` extra
requirement:
::

    pip install rows[all]

If you use Debian [sid](https://www.debian.org/releases/sid/) or
[testing](https://www.debian.org/releases/testing/) you can install it directly
from the main repository by running:
::

    aptitude install python-rows  # Python library only
    aptitude install rows  # Python library + CLI


.. include:: basic_usage.rst

.. include:: importing_data.rst

.. include:: exporting_data.rst

.. include:: avaliable_plugins.rst

.. include:: command_line.rst

.. include:: locale.rst

License
=======

This library is released under the `GNU General Public License version
3 <http://www.gnu.org/licenses/gpl-3.0.html>`_.

Bugs and Enhancements
=====================

Please fill an issue in https://github.com/turicas/rows/issues

.. toctree::
   :maxdepth: 2
