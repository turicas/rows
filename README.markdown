# rows

[![Join the chat at https://gitter.im/turicas/rows](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/turicas/rows?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

No matter in which format your tabular data is: `rows` will import it,
automatically detect types and give you high-level Python objects so you can
start **working with the data** instead of **trying to parse it**. It is also
locale-and-unicode aware. :)


## Architecture

The library is composed by:

- A common interface to tabular data (the `Table` class)
- A set of plugins to populate `Table` objects (CSV, XLS, HTML, TXT -- more
  coming soon!)
- A set of common fields (such as `BoolField`, `IntegerField`) which know
  exactly how to serialize and deserialize data for each object type you'll get
- A set of utilities (such as field type recognition) to help working with
  tabular data
- A command-line interface so you can have easy access to the most used
  features: convert between formats, sum, join and sort tables.

Just `import rows` and relax.


## Installation

Directly from [PyPI](http://pypi.python.org/pypi/rows):

    pip install rows


Or from source:

    git clone https://github.com/turicas/rows.git
    cd rows
    python setup.py install


## Basic Usage

You can create a `Table` object and populate it with some data:

```python
from collections import OrderedDict
from rows import fields, Table

my_fields = OrderedDict([('name', fields.UnicodeField),
                         ('age', fields.IntegerField),
                         ('married', fields.BoolField)])
table = Table(fields=my_fields)
table.append({'name': u'Álvaro Justen', 'age': 28, 'married': False})
table.append({'name': u'Another Guy', 'age': 42, 'married': True})
```

Then you can iterate over it:

```python
def print_person(person):
    married = 'is married' if person.married else 'is not married'
    print u'{} is {} years old and {}'.format(person.name, person.age, married)

for person in table:
    print_person(person)  # namedtuples are returned
```

You'll see:

```
Álvaro Justen is 28 years old and is not married
Another Guy is 42 years old and is married
```

As you specified field types (`my_fields`) you don't need to insert data using
the correct types. Actually you can insert strings and the library you
automatically convert it for you:

```python
table.append({'name': '...', 'age': '', 'married': 'false'})
print_person(table[-1])  # yes, you can index it!
```

And the output:

```
... is None years old and is not married
```


### Importing Data

`rows` will help you importing data: its plugins will do the hard job of
parsing each supported file format so you don't need to. They can help you
exporting data also. For example, let's download a CSV from the Web and import
it:

```python
import requests
import rows
from io import BytesIO

url = 'http://unitedstates.sunlightfoundation.com/legislators/legislators.csv'
csv = requests.get(url).content  # Download CSV data
legislators = rows.import_from_csv(BytesIO(csv))  # already imported!

print 'Hey, rows automatically identified the types:'
for field_name, field_type in legislators.fields.items():
    print '{} is {}'.format(field_name, field_type)
```

And you'll see something like this:

```
[...]
in_office is <class 'rows.fields.BoolField'>
gender is <class 'rows.fields.UnicodeField'>
[...]
birthdate is <class 'rows.fields.DateField'>
```

We can then work on this data:

```python
women_in_office = filter(lambda row: row.in_office and row.gender == 'F',
                         legislators)
men_in_office = filter(lambda row: row.in_office and row.gender == 'M',
                       legislators)
print 'Women vs Men: {} vs {}'.format(len(women_in_office), len(men_in_office))
```

Now, let's compare ages:

```python
legislators.order_by('birthdate')
older, younger = legislators[-1], legislators[0]
print '{}, {} is older than {}, {}'.format(older.lastname, older.firstname,
                                           younger.lastname, younger.firstname)
```

The output:

```
Stefanik, Elise is older than Byrd, Robert
```

> Note that **native Python objects** are returned for each row! The library
> recognizes each field type and convert data *automagically*.


### Exporting Data

Now it's time to export this data using another plugin: HTML! It's pretty easy:

```python
rows.export_to_html(legislators, 'legislators.html')
```

And you'll get:

```
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
```

Now you have finished the quickstart guide. See the `examples` folder for more
examples.


### Available Plugins

- CSV: use `rows.import_from_csv` and `rows.export_to_csv`
- HTML: use `rows.import_from_html` and `rows.export_to_html`
- XLS: use `rows.import_from_xls` and `rows.export_to_xls`
- TXT: use `rows.export_to_csv`

We'll be adding support for more plugins soon (like ODS, PDF, JSON etc.) --
actually we're going to re-design the plugin interface so you can create your
own easily.


## Command-Line Interface

TODO. Run `rows --help` and see `rows/cli.py`.


## Locale

TODO. See `rows/localization.py`.


## Operations

Available operations: `join`, `transform` and `serialize`.

TODO. See `rows/operations.py`.


## License

This library is released under the [GNU General Public License version
3](http://www.gnu.org/licenses/gpl-3.0.html).


## Related projects

- <https://github.com/scraperwiki/scrumble/>
- <https://nytlabs.github.io/streamtools/>
- <https://github.com/Kozea/Multicorn>
- messytables
- tablib
- pandas' DataFrame
