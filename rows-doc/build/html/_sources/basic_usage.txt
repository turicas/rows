Basic Usage
===========

You can create a `Table` object and populate it with some data
programmatically:

::

    from collections import OrderedDict
    from rows import fields, Table

    my_fields = OrderedDict([('name', fields.UnicodeField),
                             ('age', fields.IntegerField),
                             ('can', fields.BoolField)])
    table = Table(fields=my_fields)
    table.append({'name': u'Álvaro Justen', 'age': 28, 'can': False})
    table.append({'name': u'Another Guy', 'age': 42, 'can': True})


Then you can iterate over it:

::

    def print_person(person):
        can = 'can' if person.can else "just can't"
        print u'{} is {} years old and {}'.format(person.name, person.age, can)

    for person in table:
        print_person(person)  # namedtuples are returned


You'll see:

::

    Álvaro Justen is 28 years old and just can't.
    Another Guy is 42 years old and can.



As you specified field types (`my_fields`) you don't need to insert data using
the correct types. Actually you can insert strings and the library will
automatically convert it for you:

::

    table.append({'name': '...', 'age': '', 'can': 'false'})
    print_person(table[-1])  # yes, you can index it!


And the output:

::

    is None years old and just can't

