# Basic Usage

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

[br-cities]: https://gist.github.com/turicas/ec0abcfe0d7abf7a97ef7a0c1d72c7f7
[rows-lazyness]: https://github.com/turicas/rows/issues/45
[doc-quick-start]: quick-start.md
