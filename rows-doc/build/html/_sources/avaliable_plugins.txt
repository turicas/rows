Available Plugins
=================

The idea behing plugins is very simple: you write a little piece of code which
extracts data from/to some specific format and the library will do the other
tasks for you. So writing a plugin is as easy as reading from/writing to the
file format you want. Currently we have the following plugins:

* CSV: use ``rows.import_from_csv`` and ``rows.export_to_csv`` (dependencies are
  installed by default)
* TXT: use ``rows.export_to_txt`` (no dependencies)
* JSON: use ``rows.import_from_json`` and ``rows.export_to_json`` (no dependencies)
* HTML: use ``rows.import_from_html`` and ``rows.export_to_html`` (denpendencies
  must be installed with ``pip install rows[html]``)
* XLS: use ``rows.import_from_xls`` and ``rows.export_to_xls`` (dependencies must
  be installed with ``pip install rows[xls]``)
* SQLite: use ``rows.import_from_sqlite`` and ``rows.export_to_sqlite`` (no
  dependencies)
* ODS: use ``rows.import_from_ods`` (dependencies must be installed with ``pip
  install rows[ods]``)

More plugins are coming (like PDF, DBF etc.) and we're going to re-design the
plugin interface so you can create your own easily. Feel free to contribute.
:-)

Common Parameters
-----------------

Each plugin has its own parameters (like ``encoding`` in ``import_from_html`` and
``sheet_name`` in ``import_from_xls``) but all plugins use the same mechanism to
prepare a ``rows.Table`` before exporting, so they also have some common
parameters you can pass to ``export_to_X``. They are:

- ``export_fields``: a ``list`` with field names to export (other fields will be
  ignored) -- fields will be exported in this order.