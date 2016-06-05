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

> Note: if you're using [rows][rows] in some project please [tell
> us][rows-issue-103]! :-)


## Architecture

The library is composed by:

- A common interface to tabular data (the `Table` class)
- A set of plugins to populate `Table` objects (CSV, XLS, XLSX, HTML and XPath,
  Parquet, TXT, JSON, SQLite -- more coming soon!)
- A set of common fields (such as `BoolField`, `IntegerField`) which know
  exactly how to serialize and deserialize data for each object type you'll get
- A set of utilities (such as field type recognition) to help working with
  tabular data
- A command-line interface so you can have easy access to the most used
  features: convert between formats, sum, join and sort tables.

Just `import rows` and relax.


## Core Values

- Simple, easy and flexible API
- Code quality
- Don't Repeat Yourself


## Installation

Directly from [PyPI][pypi-rows]:

    pip install rows

You can also install directly from the GitHub repository to have the newest
features (not pretty stable) by running:

    pip install git+https://github.com/turicas/rows.git@develop

or:

    git clone https://github.com/turicas/rows.git
    cd rows
    python setup.py install


The plugins `csv`, `txt`, `json` and `sqlite` are built-in by default but if
you want to use another one you need to explicitly install its dependencies,
for example:

    pip install rows[html]
    pip install rows[xls]

You also need to install some dependencies to use the [command-line
interface][rows-cli]. You can do it installing the `cli` extra requirement:

    pip install rows[cli]

And - easily - you can install all the dependencies by using the `all` extra
requirement:

    pip install rows[all]

If you use Debian [sid][debian-sid] or [testing][debian-testing] you can
install it directly from the main repository by running:

    aptitude install python-rows  # Python library only
    aptitude install rows  # Python library + CLI

And in Fedora:

    dnf install python-row  # Python library + CLI


## Basic Usage

You can create a `Table` object and populate it with some data
programmatically:

```python
from collections import OrderedDict
from rows import fields, Table

my_fields = OrderedDict([('name', fields.UnicodeField),
                         ('age', fields.IntegerField),
                         ('can', fields.BoolField)])
table = Table(fields=my_fields)
table.append({'name': u'Álvaro Justen', 'age': 28, 'can': False})
table.append({'name': u'Another Guy', 'age': 42, 'can': True})
```

Then you can iterate over it:

```python
def print_person(person):
    can = 'can' if person.can else "just can't"
    print u'{} is {} years old and {}'.format(person.name, person.age, can)

for person in table:
    print_person(person)  # namedtuples are returned
```

You'll see:

```
Álvaro Justen is 28 years old and just can't.
Another Guy is 42 years old and can.
```

As you specified field types (`my_fields`) you don't need to insert data using
the correct types. Actually you can insert strings and the library will
automatically convert it for you:

```python
table.append({'name': '...', 'age': '', 'can': 'false'})
print_person(table[-1])  # yes, you can index it!
```

And the output:

```
... is None years old and just can't
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


#### Common Parameters

Each plugin has its own parameters (like `index` in `import_from_html` and
`sheet_name` in `import_from_xls`) but all plugins create a `rows.Table` object
so they also have some common parameters you can pass to `import_from_X`. They
are:

- `fields`: an `OrderedDict` with field names and types (disable automatic
  detection of types).
- `skip_header`: Ignore header row. Only used if `fields` is not `None`.
  Default: `True`.
- `import_fields`: a `list` with field names to import (other fields will be
  ignored) -- fields will be imported in this order.
- `samples`: number of sample rows to use on field type autodetect algorithm.
  Default: `None` (use all rows).


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
- JSON: use `rows.import_from_json` and `rows.export_to_json` (no dependencies)
- HTML: use `rows.import_from_html` and `rows.export_to_html` (denpendencies
  must be installed with `pip install rows[html]`)
- XPath: use `rows.import_from_xpath` passing the following arguments:
  `filename_or_fobj`, `rows_xpath` and `fields_xpath` (denpendencies must be
  installed with `pip install rows[xpath]`) -- see an example in
  `examples/library/ecuador_radiodifusoras.py`.
- Parquet: use `rows.import_from_parquet` passing the filename (dependencies
  must be installed with `pip install rows[parquet]` and if the data is
  compressed using snappy you also need to install `rows[parquet-snappy]` and
  the `libsnappy-dev` system library) -- read [this blog post][blog-rows-parquet]
  for more details and one example
- XLS: use `rows.import_from_xls` and `rows.export_to_xls` (dependencies must
  be installed with `pip install rows[xls]`)
- XLSX: use `rows.import_from_xlsx` and `rows.export_to_xlsx` (dependencies
  must be installed with `pip install rows[xlsx]`)
- SQLite: use `rows.import_from_sqlite` and `rows.export_to_sqlite` (no
  dependencies)
- ODS: use `rows.import_from_ods` (dependencies must be installed with `pip
  install rows[ods]`)

More plugins are coming (like PDF, DBF etc.) and we're going to re-design the
plugin interface so you can create your own easily. Feel free to contribute.
:-)


#### Common Parameters

Each plugin has its own parameters (like `encoding` in `import_from_html` and
`sheet_name` in `import_from_xls`) but all plugins use the same mechanism to
prepare a `rows.Table` before exporting, so they also have some common
parameters you can pass to `export_to_X`. They are:

- `export_fields`: a `list` with field names to export (other fields will be
  ignored) -- fields will be exported in this order.


## Command-Line Interface

`rows` exposes a command-line interface with the common operations such as
convert data between plugins, sum, sort and join `Table`s.

Run `rows --help` to see the available commands and take a look at
`rows/cli.py`. We still need to improve the CLI docs, sorry.


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


## Developing

Create the virtualenv:

    mkvirtualenv rows

Install all plugins' dependencies:

    pip install --editable .[all]

Install development dependencies:

    pip install -r requirements-development.txt

Run tests:

    make test

or (if you don't have `make`):

    tox

you can also run tox against an especific python version:

    tox -e py27
    tox -e py35

*tox known issuses* : runing tox with py27 eviron may raise InvocationError in non Linux environments. To avoid it you may rebuild tox environment in every run with: `tox -e py27 -r`

or if you want to run nosetests directly:

    nosetests -dsv --with-yanc --with-coverage --cover-package rows tests/*.py

To create the man page you'll need to install [txt2man][txt2man]. In Debian
(and Debian-based distributions) you can install by running:

```bash
aptitude install txt2man
```

Then, you can generate the `rows.1` file by running:

```bash
make man
```


## Similar Projects

- [OKFN's goodtables](https://github.com/okfn/goodtables)
- [OKFN's messytables](https://github.com/okfn/messytables)
- [csvcat](https://pypi.python.org/pypi/csvcat)
- [csvstudio](https://github.com/mdipierro/csvstudio)
- [odo](https://github.com/blaze/odo)
- [pandashells](https://github.com/robdmc/pandashells) (and pandas DataFrame)
- [tablib](https://tablib.readthedocs.org/en/latest/)
- [textql](https://github.com/dinedal/textql)


## Related Projects

- [libextract](https://github.com/datalib/libextract)
- [scrapy](http://scrapy.org/)
- [grablib](https://github.com/lorien/grab)
- [streamtools](http://blog.nytlabs.com/streamtools/)
- [multicorn](https://github.com/Kozea/Multicorn)
- [webscraper.io](http://webscraper.io/)
- [import.io](http://import.io/)
- [Tabula](http://tabula.technology/)


## Known Issues

- [Lack of Python 3 support][rows-issue-46]
- [Create a better plugin interface so anyone can benefit of
  it][rows-issue-27]
- [Create an object to represent a set of `rows.Table`s, like
  `TableSet`][rows-issue-47]
- Performance: the automatic type detection algorithm can cost time: it
  iterates over all rows to determine the type of each column. You can disable
  it by passing `samples=0` to any `import_from_*` function or either changing
  the number of sample rows (any positive number is accepted).
- [Code design issues][rows-issue-31]


## Semantic Versioning

`rows` uses [semantic versioning][semver]. Note that it means we do not
guarantee API backwards compatibility on `0.x.y` versions.


## License

This library is released under the [GNU General Public License version
3][gpl3].


[blog-rows-parquet]: http://blog.justen.eng.br/2016/03/reading-parquet-files-in-python-with-rows.html
[debian-sid]: https://www.debian.org/releases/sid/
[debian-testing]: https://www.debian.org/releases/testing/
[gpl3]: http://www.gnu.org/licenses/gpl-3.0.html
[pypi-rows]: http://pypi.python.org/pypi/rows
[rows-cli]: #command-line-interface
[rows-issue-103]: https://github.com/turicas/rows/issues/103
[rows-issue-27]: https://github.com/turicas/rows/issues/27
[rows-issue-31]: https://github.com/turicas/rows/issues/31
[rows-issue-46]: https://github.com/turicas/rows/issues/46
[rows-issue-47]: https://github.com/turicas/rows/issues/47
[rows]: https://github.com/turicas/rows/
[semver]: http://semver.org/
[txt2man]: http://mvertes.free.fr/
