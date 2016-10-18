.. _links:

Useful links
============

Showcase
--------

- `Convert files tabular files using rows <http://rows.irdx.com.br/>`_ (`source
  code <https://github.com/leonardocsantoss/django-rows>`_ )
- (Portuguese) `Talk (videos + slides) on rows by Álvaro Justeni <http://blog.justen.eng.br/2016/05/dados-tabulares-a-maneira-pythonica.html>`_


Similar Projects
----------------

- `OKFN's goodtables <https://github.com/okfn/goodtables>`_
- `OKFN's messytables <https://github.com/okfn/messytables>`_
- `csvcat <https://pypi.python.org/pypi/csvcat>`_
- `csvstudio <https://github.com/mdipierro/csvstudio>`_
- `odo <https://github.com/blaze/odo>`_
- `pandashells <https://github.com/robdmc/pandashells>`_ (and pandas DataFrame)
- `tablib <https://tablib.readthedocs.org/en/latest/>`_
- `textql <https://github.com/dinedal/textql>`_


Related Projects
----------------

- `libextract <https://github.com/datalib/libextract>`_
- `scrapy <http://scrapy.org/>`_
- `grablib <https://github.com/lorien/grab>`_
- `streamtools <http://blog.nytlabs.com/streamtools/>`_
- `multicorn <https://github.com/Kozea/Multicorn>`_
- `webscraper.io <http://webscraper.io/>`_
- `import.io <http://import.io/>`_
- `Tabula <http://tabula.technology/>`_


Known Issues
------------

-  `Create a better plugin interface so anyone can benefit of it <https://github.com/turicas/rows/issues/27>`_
- `Create an object to represent a set of rows.Table`s, like TableSet <https://github.com/turicas/rows/issues/47>`_
- Performance: the automatic type detection algorithm can cost time: it
  iterates over all rows to determine the type of each column. You can disable
  it by passing **samples=0** to any **import_from_*** function or either changing
  the number of sample rows (any positive number is accepted).
- `Code design issues <https://github.com/turicas/rows/issues/31>`_


