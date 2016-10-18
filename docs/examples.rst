.. _examples:

Examples
========

A common use case is to have a **list** of **dict**'s -- you can also import it, and
**rows** will automatically fill in the blanks (your **dict**'s don't need to have
the same keys) and convert data

.. code-block:: python

    import rows

    data = [{'name': u'Álvaro Justen', 'age': 28, 'can': False},
            {'name': u'Another Guy', 'age': 42, 'can': True},]
    table = rows.import_from_dicts(data)

In this case, **table.fields** will be created automatically (**rows** will
identify the field type for each **dict** key).

Then you can iterate over it:

.. code-block:: python

    def print_person(person):
        can = 'can' if person.can else "just can't"
        print(u'{} is {} years old and {}'.format(person.name, person.age, can))

    for person in table:
        print_person(person)  # namedtuples are returned

You'll see::

    Álvaro Justen is 28 years old and just can't.
    Another Guy is 42 years old and can.

As you specified field types (**my_fields**) you don't need to insert data using
the correct types. Actually you can insert strings and the library will
automatically convert it for you:

.. code-block:: python

    table.append({'name': '...', 'age': '', 'can': 'false'})
    print_person(table[-1])  # yes, you can index it!

And the output::

... is None years old and just can't


Importing Data
--------------

**rows** will help you importing data: its plugins will do the hard job of
parsing each supported file format so you don't need to. They can help you
exporting data also. For example, let's download a CSV from the Web and import
it:

.. code-block:: python

    import requests
    import rows
    from io import BytesIO

    url = 'http://unitedstates.sunlightfoundation.com/legislators/legislators.csv'
    csv = requests.get(url).content  # Download CSV data
    legislators = rows.import_from_csv(BytesIO(csv))  # already imported!

    print('Hey, rows automatically identified the types:')
    for field_name, field_type in legislators.fields.items():
        print('{} is {}'.format(field_name, field_type))

And you'll see something like this::

    [...]
    in_office is <class 'rows.fields.IntegerField'>
    gender is <class 'rows.fields.TextField'>
    [...]
    birthdate is <class 'rows.fields.DateField'>

We can then work on this data:

.. code-block:: python

    women = sum(1 for row in legislators if row.in_office and row.gender == 'F')
    men = sum(1 for row in legislators if row.in_office and row.gender == 'M')
    print('Women vs Men (in office): {} vs {}'.format(women, men))

Then you'll see effects of our sexist society::

    Women vs Men: 108 vs 432

Now, let's compare ages:

.. code-block:: python

    legislators.order_by('birthdate')
    older, younger = legislators[-1], legislators[0]
    print('{}, {} is older than {}, {}'.format(
            older.lastname, older.firstname, younger.lastname, younger.firstname))

The output::

    Stefanik, Elise is older than Byrd, Robert

You can also get a whole column, like this:

.. code-block:: python

    >>> legislators[u'gender']
    [u'M',
     u'M',
     u'M',
     u'M',
     u'M',
     u'M',
     u'M',
     u'M',
     u'M',
     u'M',
     u'M',
     u'M',
     u'M',
     u'M',
     u'F',
     u'M',
     ...]

And change the whole column (or add a new one):

.. code-block:: python

    >>> legislators[u'gender'] = [u'male' if gender == u'M' else u'female'
                                  for gender in legislators[u'gender']]
    >>> legislators[u'gender']
    [u'male',
     u'male',
     u'male',
     u'male',
     u'male',
     u'male',
     u'male',
     u'male',
     u'male',
     u'male',
     u'male',
     u'male',
     u'female',
     u'male',
     ...]

Or delete it:

.. code-block:: python

    >>> u'gender' in legislators.field_names
    True
    >>> del legislators[u'gender']
    >>> u'gender' in legislators.field_names
    False
    >>> legislators[0].gender
    [...]
    AttributeError: 'Row' object has no attribute 'gender'

| Note that **native Python objects** are returned for each row inside a
| **namedtuple**! The library recognizes each field type and converts it
| **automagically** no matter which plugin you're using to import the data.


Common Parameters
-----------------

Each plugin has its own parameters (like **index** in **import_from_html** and
**sheet_name** in **import_from_xls**) but all plugins create a **rows.Table** object
so they also have some common parameters you can pass to **import_from_X**. They
are:

- **fields**: an **OrderedDict** with field names and types (disable automatic
  detection of types).
- **skip_header**: Ignore header row. Only used if **fields** is not **None**.
  Default: **True**.
- **import_fields**: a **list** with field names to import (other fields will be
  ignored) -- fields will be imported in this order.
- **samples**: number of sample rows to use on field type autodetect algorithm.
  Default: **None** (use all rows).


Exporting Data
--------------

If you have a **Table** object you can export it to all available plugins which
have the "export" feature. Let's use the HTML plugin::

    rows.export_to_html(legislators, 'legislators.html')

And you'll get:

.. code-block:: bash

    $ head legislators.html
    <table>

      <thead>
        <tr>
          <th> title </th>
          <th> firstname </th>
          <th> middlename </th>
          <th> lastname </th>
          <th> name_suffix </th>
          <th> nickname </th>

Now you have finished the quickstart guide. See the `examples <https://github.com/turicas/rows/tree/develop/examples>`_ folder for more examples.
