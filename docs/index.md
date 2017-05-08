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

> Note: if you're using [rows][rows] in some project please [tell
> us][rows-issue-103]! :-)


## Core Values

- Simple, easy and flexible API
- Code quality
- Don't Repeat Yourself


## Contents

- [Installation][doc-installing]
- [Quick-start guide][doc-quick-start]
- [Command-line interface][doc-cli]
- [Supported plugins][doc-plugins]
- [Using locale when importing data][doc-locale]
- [Table operations][doc-operations]
- [Contributing][doc-contributing]
- [Useful links][doc-links]
- [Log of changes][doc-changelog]


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

cities = rows.import_from_csv('data/brazilian-cities.csv')
rio_biggest_cities = [city for city in cities
                      if city.state == 'RJ' and
                         city.inhabitants > 500000]
for city in rio_biggest_cities:
    print('{} ({:5.2f} ppl/km²)'.format(city.city,
                                        city.inhabitants / city.area))
```

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


## Semantic Versioning

`rows` uses [semantic versioning][semver]. Note that it means we do not
guarantee API backwards compatibility on `0.x.y` versions.


## License

This library is released under the [GNU General Public License version
3][gpl3].


[doc-cli]: command-line-interface.md
[doc-contributing]: contributing.md
[doc-installing]: installing.md
[doc-links]: links.md
[doc-locale]: locale.md
[doc-operations]: operations.md
[doc-plugins]: plugins.md
[doc-changelog]: changelog.md
[doc-quick-start]: quick-start.md
[gpl3]: http://www.gnu.org/licenses/gpl-3.0.html
[rows-issue-103]: https://github.com/turicas/rows/issues/103
[rows]: https://github.com/turicas/rows/
[semver]: http://semver.org/
