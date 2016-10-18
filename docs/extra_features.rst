.. _extra_features:

Extra features
==============


Plugins
-------

The idea behing plugins is very simple: you write a little piece of code which
extracts data from/to some specific format and the library will do the other
tasks for you. So writing a plugin is as easy as reading from/writing to the
file format you want. Currently we have the following plugins:

- CSV: use **rows.import_from_csv** and **rows.export_to_csv** (dependencies are
  installed by default)
- TXT: use **rows.export_to_txt** (no dependencies)
- JSON: use **rows.import_from_json** and **rows.export_to_json** (no dependencies)
- HTML: use **rows.import_from_html** and **rows.export_to_html** (dependencies
  must be installed with **pip install rows[html]**)
- XPath: use **rows.import_from_xpath** passing the following arguments:
  **filename_or_fobj**, **rows_xpath** and **fields_xpath** (dependencies must be
  installed with **pip install rows[xpath]**) -- see an example in
  **examples/library/ecuador_radiodifusoras.py**.
- Parquet: use **rows.import_from_parquet** passing the filename (dependencies
  must be installed with **pip install rows[parquet]** and if the data is
  compressed using snappy you also need to install **rows[parquet-snappy]** and
  the **libsnappy-dev** system library) -- read [this blog post][blog-rows-parquet]
  for more details and one example
- XLS: use **rows.import_from_xls** and **rows.export_to_xls** (dependencies must
  be installed with **pip install rows[xls]**)
- XLSX: use **rows.import_from_xlsx** and **rows.export_to_xlsx** (dependencies
  must be installed with **pip install rows[xlsx]**)
- SQLite: use **rows.import_from_sqlite** and **rows.export_to_sqlite** (no
  dependencies)
- ODS: use **rows.import_from_ods** (dependencies must be installed with **pip
  install rows[ods]**)

More plugins are coming (like PDF, DBF etc.) and we're going to re-design the
plugin interface so you can create your own easily. Feel free to contribute.
:-)


Common Parameters
^^^^^^^^^^^^^^^^^

Each plugin has its own parameters (like **encoding** in **import_from_html** and
**sheet_name** in **import_from_xls**) but all plugins use the same mechanism to
prepare a **rows.Table** before exporting, so they also have some common
parameters you can pass to **export_to_X**. They are:

- **export_fields**: a **list** with field names to export (other fields will be
  ignored) -- fields will be exported in this order.


Command-Line Interface
----------------------

**rows** exposes a command-line interface with the common operations such as
convert data between plugins, sum, sort and join **Table**'s.

Run **rows --help** to see the available commands and take a look at
**rows/cli.py**. We still need to improve the CLI docs, sorry.


Locale
------

Many fields inside **rows.fields** are locale-aware. If you have some data using
Brazilian Portuguese number formatting, for example (**,** as decimal separators
and **.** as thousands separator) you can configure this into the library and
**rows** will automatically understand these numbers!

Let's see it working by extracting the population of cities in Rio de Janeiro
state:

.. code-block:: python

    import locale
    import requests
    import rows
    from io import BytesIO

    url = 'http://cidades.ibge.gov.br/comparamun/compara.php?idtema=1&codv=v01&coduf=33'
    html = requests.get(url).content
    with rows.locale_context(name='pt_BR.UTF-8', category=locale.LC_NUMERIC):
        rio = rows.import_from_html(BytesIO(html))

    total_population = sum(city.pessoas for city in rio)
    # 'pessoas' is the fieldname related to the number of people in each city
    print('Rio de Janeiro has {} inhabitants'.format(total_population))

The column **pessoas** will be imported as an **IntegerField** and the result is::

    Rio de Janeiro has 15989929 inhabitants

Operations
----------

Available operations: **join**, **transform** and **serialize**.

TODO. See **rows/operations.py**.
