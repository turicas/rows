Welcome to rows documentation!
==============================

.. toctree::
   :caption: Table of Contents
   :maxdepth: 3

   installing
   examples
   extra_features
   developing
   links


Have you ever lost your precious time reading a CSV that had a different
dialect? Or trying to learn a whole new library API to read a new tabular data
format your customer just sent? You've got gray hair when trying to access
some data and the only answer was **UnicodeDecodeError**? So,
`rows <https://github.com/turicas/rows>`_ was custom made for you! :-)

No matter in which format your tabular data is: **rows** will import it,
automatically detect types and give you high-level Python objects so you can
start **working with the data** instead of **trying to parse it**. It is also
locale-and-unicode aware. :)

| Note: if you're using **rows** in some project please `tell us <https://github.com/turicas/rows/issues/103>`_! :-)



Installing
----------

Please refer to the :ref:`installing` section


Basic Usage
-----------

You can create a **Table** object and populate it with some data programmatically:

.. code-block:: python

	from collections import OrderedDict
	from rows import fields, Table

	my_fields = OrderedDict([('name', fields.TextField),
							 ('age', fields.IntegerField),
							 ('can', fields.BoolField)])
	table = Table(fields=my_fields)
	table.append({'name': u'Álvaro Justen', 'age': 28, 'can': False})
	table.append({'name': u'Another Guy', 'age': 42, 'can': True})


For more examples, please refer to the `examples` page


Architecture
------------

The library is composed by:

- A common interface to tabular data (the **Table** class)
- A set of plugins to populate **Table** objects (CSV, XLS, XLSX, HTML and XPath,
  Parquet, TXT, JSON, SQLite -- more coming soon!)
- A set of common fields (such as **BoolField**, **IntegerField**) which know
  exactly how to serialize and deserialize data for each object type you'll get
- A set of utilities (such as field type recognition) to help working with
  tabular data
- A command-line interface so you can have easy access to the most used
  features: convert between formats, sum, join and sort tables.

Just **import rows** and relax.


Core Values
-----------

- Simple, easy and flexible API
- Code quality
- Don't Repeat Yourself


Semantic Versioning
-------------------

**rows** uses `semantic versioning <http://semver.org/>`_. Note that it means we do not
guarantee API backwards compatibility on **0.x.y** versions.


License
-------

This library is released under the `GNU General Public License version
3 <http://www.gnu.org/licenses/gpl-3.0.html>`_.
