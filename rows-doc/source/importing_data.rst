Importing Data
==============

``rows`` will help you importing data: its plugins will do the hard job of
parsing each supported file format so you don't need to. They can help you
exporting data also. For example, let's download a CSV from the Web and import
it:
::

    import requests
    import rows
    from io import BytesIO

    url = 'http://unitedstates.sunlightfoundation.com/legislators/legislators.csv'
    csv = requests.get(url).content  # Download CSV data
    legislators = rows.import_from_csv(BytesIO(csv))  # already imported!

    print 'Hey, rows automatically identified the types:'
    for field_name, field_type in legislators.fields.items():
        print '{} is {}'.format(field_name, field_type)

And you'll see something like this:

::

    [...]
    in_office is <class 'rows.fields.BoolField'>
    gender is <class 'rows.fields.UnicodeField'>
    [...]
    birthdate is <class 'rows.fields.DateField'>

We can then work on this data:

::

    women_in_office = filter(lambda row: row.in_office and row.gender == 'F',
                             legislators)
    men_in_office = filter(lambda row: row.in_office and row.gender == 'M',
                           legislators)
    print 'Women vs Men: {} vs {}'.format(len(women_in_office), len(men_in_office))


Then you'll see effects of our sexist society:

::

    Women vs Men: 108 vs 432


Now, let's compare ages:

::

    legislators.order_by('birthdate')
    older, younger = legislators[-1], legislators[0]
    print '{}, {} is older than {}, {}'.format(older.lastname, older.firstname,
                                               younger.lastname, younger.firstname)

The output:

::

    Stefanik, Elise is older than Byrd, Robert

..

    Note that **native Python objects** are returned for each row inside a
    `namedtuple`! The library recognizes each field type and converts it
    *automagically* no matter which plugin you're using to import the data.

Common Parameters
------------------

Each plugin has its own parameters (like index in import_from_html and sheet_name in import_from_xls) but all plugins create a rows.Table object so they also have some common parameters you can pass to import_from_X. They are:

* ``fields``: an ``OrderedDict`` with field names and types (disable automatic detection of types).
* ``skip_header``: Ignore header row. Only used if ``fields`` is not ``None``. Default: ``True``.
* ``import_fields``: a ``list`` with field names to import (other fields will be ignored) -- fields will be imported in this order.
* ``samples``: number of sample rows to use on field type autodetect algorithm. Default: ``None`` (use all rows).
