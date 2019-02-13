# Welcome to rows documentation!

No matter in which format your tabular data is: `rows` will import it,
automatically detect types and give you high-level Python objects so you can
start **working with the data** instead of **trying to parse it**. It is also
locale-and-unicode aware. :)

Have you ever lost your precious time reading a CSV that had a different
dialect? Or trying to learn a whole new library API to read a new tabular data
format your customer just sent? You've got gray hair when trying to access
some data and the only answer was `UnicodeDecodeError`? So,
[rows][rows] was custom made for you - run `pip install rows` and be happy! :-)

The library is officialy supported on Python versions 2.7, 3.5 and 3.6 (but may
work on other versions too).

> Note: if you're using [rows][rows] in some project please [tell
> us][rows-issue-103]! :-)


## Contents

- [Installation][doc-installation]
- [Quick-start guide][doc-quick-start]
- [Command-line interface][doc-cli]
- [Supported plugins][doc-plugins]
- [Using locale when importing data][doc-locale]
- [Table operations][doc-operations]
- [Contributing][doc-contributing]
- [Useful links][doc-links]
- [Log of changes][doc-changelog]
- [Code reference][reference]


## Basic Usage

`rows` will import tabular data in any of the supported formats, automatically
detect/convert encoding and column types for you, so you can focus on work on
the data.

Given a CSV file like this:

```
state,city,inhabitants,area
AC,Acrelândia,12538,1807.92
AC,Assis Brasil,6072,4974.18
AC,Brasiléia,21398,3916.5
AC,Bujari,8471,3034.87
AC,Capixaba,8798,1702.58
[...]
RJ,Angra dos Reis,169511,825.09
RJ,Aperibé,10213,94.64
RJ,Araruama,112008,638.02
RJ,Areal,11423,110.92
RJ,Armação dos Búzios,27560,70.28
[...]
```

You can use `rows` to do some math with it without the need to convert
anything:

```python
import rows

cities = rows.import_from_csv("data/brazilian-cities.csv")
rio_biggest_cities = [
    city for city in cities
    if city.state == "RJ" and city.inhabitants > 500000
]
for city in rio_biggest_cities:
    density = city.inhabitants / city.area
    print(f"{city.city} ({density:5.2f} ppl/km²)")
```

> Note: download [brazilian-cities.csv][br-cities].

The result:

```text
Duque de Caxias (1828.51 ppl/km²)
Nova Iguaçu (1527.59 ppl/km²)
Rio de Janeiro (5265.81 ppl/km²)
São Gonçalo (4035.88 ppl/km²)
```

The library can also export data in any of the available plugins and have a
command-line interface for more common tasks.

For more examples, please refer to our [quick-start guide][doc-quick-start].

> Note: `rows` is still not lazy by default, except for some operations like
> `csv2sqlite`, `sqlite2csv`, `pgimport` and `pgexport` (so using
> `rows.import_from_X` will put everything in memory), [we're working on
> this][rows-lazyness].


## Architecture

The library is composed by:

- A common interface to tabular data (the `Table` class)
- A set of plugins to populate `Table` objects from formats like CSV, XLS,
  XLSX, HTML and XPath, Parquet, PDF, TXT, JSON, SQLite;
- A set of common fields (such as `BoolField`, `IntegerField`) which know
  exactly how to serialize and deserialize data for each object type you'll get
- A set of utilities (such as field type recognition) to help working with
  tabular data
- A command-line interface so you can have easy access to the most used
  features: convert between formats, sum, join and sort tables.


## Semantic Versioning

`rows` uses [semantic versioning][semver]. Note that it means we do not
guarantee API backwards compatibility on `0.x.y` versions (but we try the best
to).


## License

This library is released under the [GNU Lesser General Public License version
3][lgpl3].


[br-cities]: https://gist.github.com/turicas/ec0abcfe0d7abf7a97ef7a0c1d72c7f7
[doc-changelog]: changelog.md
[doc-cli]: cli.md
[doc-contributing]: contributing.md
[doc-installation]: installation.md
[doc-links]: links.md
[doc-locale]: locale.md
[doc-operations]: operations.md
[doc-plugins]: plugins.md
[doc-quick-start]: quick-start.md
[lgpl3]: http://www.gnu.org/licenses/lgpl-3.0.html
[reference]: reference/
[rows-issue-103]: https://github.com/turicas/rows/issues/103
[rows-lazyness]: https://github.com/turicas/rows/issues/45
[rows]: https://github.com/turicas/rows/
[semver]: http://semver.org/
