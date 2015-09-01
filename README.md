# rows

[![Join the chat at https://gitter.im/turicas/rows](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/turicas/rows?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![License: GPLv3](https://img.shields.io/pypi/l/rows.svg)](https://github.com/turicas/rows/blob/develop/LICENSE)
[![Current version at PyPI](https://img.shields.io/pypi/v/rows.svg)](https://pypi.python.org/pypi/rows)
[![Downloads per month on PyPI](https://img.shields.io/pypi/dm/rows.svg)](https://pypi.python.org/pypi/rows)
![Supported Python Versions](https://img.shields.io/pypi/pyversions/rows.svg)
![Software status](https://img.shields.io/pypi/status/rows.svg)
[![Donate](https://img.shields.io/gratipay/turicas.svg?style=social&label=Donate)](https://www.gratipay.com/turicas)

No matter in which format your tabular data is: `rows` will import it,
automatically detect types and give you high-level Python objects so you can
start **working with the data** instead of **trying to parse it**. It is also
locale-and-unicode aware. :)


## Architecture

The library is composed by:

- A common interface to tabular data (the `Table` class)
- A set of plugins to populate `Table` objects (CSV, XLS, HTML, TXT, JSON
  -- more coming soon!)
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


The plugins `csv`, `txt` and `json` are built-in by default but if you want to
use another one you need to explicitly install its dependencies, for example:

    pip install rows[html]
    pip install rows[xls]


## Basic Usage

You can create a `Table` object and populate it with some data
programmatically:

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
the correct types. Actually you can insert strings and the library will
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

Then you'll see effects of our sexist society:

```
Women vs Men: 108 vs 432
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

> Note that **native Python objects** are returned for each row inside a
> `namedtuple`! The library recognizes each field type and converts it
> *automagically* no matter which plugin you're using to import the data.


### Exporting Data

If you have a `Table` object you can export it to all available plugins which
have the "export" feature. Let's use the HTML plugin:

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

The idea behing plugins is very simple: you write a little piece of code which
extracts data from/to some specific format and the library will do the other
tasks for you. So writing a plugin is as easy as reading from/writing to the
file format you want. Currently we have the following plugins:

- CSV: use `rows.import_from_csv` and `rows.export_to_csv` (dependencies are
  installed by default)
- TXT: use `rows.export_to_txt` (no dependencies)
- JSON: use `rows.export_to_json` (no dependencies)
- HTML: use `rows.import_from_html` and `rows.export_to_html` (denpendencies
  must be installed with `pip install rows[html]`)
- XLS: use `rows.import_from_xls` and `rows.export_to_xls` (dependencies must
  be installed with `pip install rows[xls]`)

More plugins are coming (like ODS, PDF, SQLite, JSON etc.) and we're going to
re-design the plugin interface so you can create your own easily. Feel free to
contribute. :-)


## Command-Line Interface

`rows` exposes a command-line interface with the common operations such as
convert data between plugins, sum, sort and join `Table`s.

Run `rows --help` to see the available commands and take a look at
`rows/cli.py`. TODO.


## Locale

Many fields inside `rows.fields` are locale-aware. If you have some data using
Brazilian Portuguese number formatting, for example (`,` as decimal separators
and `.` as thousands separator) you can configure this into the library and
`rows` will automatically understand these numbers!

Let's see it working by extracting the population of cities in Rio de Janeiro
state:

```python
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
print 'Rio de Janeiro has {} inhabitants'.format(total_population)
```

The column `pessoas` will be imported as an `IntegerField` and the result is:

```
Rio de Janeiro has 15989929 inhabitants
```

## Operations

Available operations: `join`, `transform` and `serialize`.

TODO. See `rows/operations.py`.


## License

This library is released under the [GNU General Public License version
3](http://www.gnu.org/licenses/gpl-3.0.html).


## Semantic Versioning

`rows` uses [semantic versioning](http://semver.org). Note that it means we do
not guarantee API backwards compatibility on `0.x.y` versions.


## Known Issues

- Support Python 3
- Create a better plugin interface
- Create a `TableList` (?) interface
- See [issue #31](https://github.com/turicas/rows/issues/31)


## Core Values

- Simple and easy API
- Code quality
- Don't Repeat Yourself
- Flexibility


## Related/Similar projects

- <https://github.com/scraperwiki/scrumble/>
- <https://nytlabs.github.io/streamtools/>
- <https://github.com/Kozea/Multicorn>
- [OKFN's messytables](https://github.com/okfn/messytables)
- [OKFN's goodtables](https://github.com/okfn/goodtables)
- [tablib](https://tablib.readthedocs.org/en/latest/)
- pandas' DataFrame
