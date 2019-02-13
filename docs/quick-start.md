# Quick Start Guide

## Programatically creating a `Table` object

`rows` can import data from any of the supported formats (using
`rows.import_from_X` functions) and will return a `Table` object for you, but
you can also create a `Table` object by hand.

### Using `Table.append`

```python
from collections import OrderedDict
from rows import fields, Table

# Create a schema for the new table (check also all the available field types
# inside `rows.fields`).
country_fields = OrderedDict([
    ("name", fields.TextField),
    ("population", fields.IntegerField),
])

# Data from: <http://www.worldometers.info/world-population/population-by-country/>
countries = Table(fields=country_fields)
countries.append({"name": "Argentina", "population": "45101781"})
countries.append({"name": "Brazil", "population": "212392717"})
countries.append({"name": "Colombia", "population": "49849818"})
countries.append({"name": "Ecuador", "population": "17100444"})
countries.append({"name": "Peru", "population": "32933835"})
```

Then you can iterate over it:

```python
for country in countries:
    print(country)
# Result:
#     Row(name='Argentina', population=45101781)
#     Row(name='Brazil', population=212392717)
#     Row(name='Colombia', population=49849818)
#     Row(name='Ecuador', population=17100444)
#     Row(name='Peru', population=32933835)
# "Row" is a namedtuple created from `country_fields`

# We've added population as a string, the library automatically converted to
# integer so we can also sum:
countries_population = sum(country.population for country in countries)
print(countries_population)  # prints 357378595
```

You could also export this table to CSV or any other supported format:

```python
import rows
rows.export_to_csv(countries, "some-LA-countries.csv")
```

If you had this file before, you could:

```python
import rows

countries = rows.import_from_csv("some-LA-countries.csv")
for country in countries:
    print(country)
# And the result will be the same.

# Since the library has an automatic type detector, the "population" column
# will be detected and converted to integer. Let's see the detected types:
print(countries.fields)
# Result:
#    OrderedDict([
#        ('name', <class 'rows.fields.TextField'>),
#        ('population', <class 'rows.fields.IntegerField'>)
#    ])
```


### From a `list` of `dict`s

If you have the data in a list of dictionaries already you can simply use
`rows.import_from_dicts`:

```python
import rows

data = [
    {"name": "Argentina", "population": "45101781"},
    {"name": "Brazil", "population": "212392717"},
    {"name": "Colombia", "population": "49849818"},
    {"name": "Ecuador", "population": "17100444"},
    {"name": "Peru", "population": "32933835"},
    {"name": "Guyana", },  # Missing "population", will fill with `None`
]
table = rows.import_from_dicts(data)
print(table[-1])  # Can use indexes
# Result:
#     Row(name='Guyana', population=None)
```


## Importing from other formats

`rows`' ability to import data is amazing: its plugins will do the hard job of
parsing the file format so you don't need to. They can help you exporting data
also. For example, let's download a CSV from the Web and import it:

```python
import requests
import rows
from io import BytesIO

url = "http://unitedstates.sunlightfoundation.com/legislators/legislators.csv"
csv = requests.get(url).content  # Download CSV data
legislators = rows.import_from_csv(BytesIO(csv))  # already imported!

print("rows automatically identified the types:")
for field_name, field_type in legislators.fields.items():
    print(f"{field_name} is {field_type}")
```

And you'll see something like this:

```text
[...]
gender is <class 'rows.fields.TextField'>
[...]
govtrack_id is <class 'rows.fields.IntegerField'>
[...]
birthdate is <class 'rows.fields.DateField'>
[...]
```

> Note that **native Python objects** are returned for each row inside a
> `namedtuple`! The library recognizes each field type and converts it
> *automagically* no matter which plugin you're using to import the data.

We can then work on this data:

```python
women = sum(1 for row in legislators if row.in_office and row.gender == 'F')
men = sum(1 for row in legislators if row.in_office and row.gender == 'M')
print(f"Women vs Men (in office): {women} vs {men}.")
# Result:
#     Women vs Men: 108 vs 432.
```

Since `birthdate` is automatically detected and converted to a
`rows.fields.DateField` we can do some quick analysis:

```python
legislators.order_by("birthdate")
older, younger = legislators[-1], legislators[0]
print(f"{older.lastname}, {older.firstname} is older than {younger.lastname}, {younger.firstname}.")
# Result:
#     Stefanik, Elise is older than Byrd, Robert.
```

You can also get a whole column, like this:

```python
print(legislators["gender"])
# Result (a list of strings):
#     ['M', 'M', 'M', 'M', 'M', 'M', ..., 'M', 'M', 'F']
```

And change the whole column (or add a new one):

```python
legislators["gender"] = [
    "male" if gender == "M" else "female"
    for gender in legislators["gender"]
]
print(legislators["gender"])
# Result:
#     ['male', 'male', 'male', ..., 'male', 'female']
```

Or delete it:

```python
print("gender" in legislators.field_names)
# Result: True
del legislators["gender"]
print("gender" in legislators.field_names)
# Result: False
print(legislators[0].gender)
# Raises the exception:
#     AttributeError: 'Row' object has no attribute 'gender'
```

Exercise: use `rows.import_from_html` to import [population data from
worldometers.com][worldometers-population-table] (tip: you must run
`pip install rows[html]` first to install the needed dependencies).


### Common Parameters

Each plugin has its own parameters (like `index` in `import_from_html` and
`sheet_name` in `import_from_xls`) but all plugins create a `rows.Table` object
so they also have some common parameters you can pass to `import_from_X`. They
are:

- `fields`: an `OrderedDict` with field names and types (disable automatic
  detection of types).
- `force_types`: a `dict` mapping field names to field types you'd like to
  force, so `rows` won't try to detect it. Example:
  `{"population": rows.fields.IntegerField}`.
- `skip_header`: Ignore header row. Only used if `fields` is not `None`.
  Default: `True`.
- `import_fields`: a `list` with field names to import (other fields will be
  ignored) -- fields will be imported in this order.
- `export_fields`: a `list` with field names to export (other fields will be
  ignored) -- fields will be exported in this order.
- `samples`: number of sample rows to use on field type autodetect algorithm.
  Default: `None` (use all rows).


## Exporting Data

If you have a `Table` object you can export it to all available plugins which
have the "export" feature. Let's use the HTML plugin:

```python
rows.export_to_html(legislators, "legislators.html")
```

And you'll get a file with the following contents:

```html
<table>

  <thead>
    <tr>
      <th> title </th>
      <th> firstname </th>
      <th> middlename </th>
      <th> lastname </th>
      <th> name_suffix </th>
      <th> nickname </th>
[...]

  </tbody>

</table>
```


### Exporting to memory

Some plugins don't require a filename to export to, so you can get the result
as a string, for example:

```python
fields_to_export = ("title", "firstname", "lastname", "party")
content = rows.export_to_txt(legislators, export_fields=fields_to_export)
print(content)
```

The result will be:

```text
+-------+-------------+--------------------+-------+
| title |  firstname  |      lastname      | party |
+-------+-------------+--------------------+-------+
|   Sen |      Robert |               Byrd |     D |
|   Rep |       Ralph |               Hall |     R |
|   Sen |         Ted |            Stevens |     R |
|   Sen |       Frank |         Lautenberg |     D |
[...]
|   Rep |       Aaron |             Schock |     R |
|   Rep |        Matt |              Gaetz |     R |
|   Rep |        Trey |      Hollingsworth |     R |
|   Rep |        Mike |          Gallagher |     R |
|   Rep |       Elise |           Stefanik |     R |
+-------+-------------+--------------------+-------+
```

The plugins `csv`, `json` and `html` have this behaviour.


It makes sense on file-oriented formats to returned the data as output, but
some plugins return different objects; on `sqlite` the returned object is
a `sqlite3.Connection`, see:

```python
connection = rows.export_to_sqlite(legislators, ":memory:")
query = "SELECT firstname, lastname FROM table1 WHERE birthdate > 1980-01-01"
connection = rows.export_to_sqlite(legislators, ":memory:")
print(list(connection.execute(query).fetchall()))
```

You'll get the following output:

```text
[('Darren', 'Soto'), ('Adam', 'Kinzinger'), ('Ron', 'DeSantis'), (...)]
```


#### Using file and connection objects

The majority of plugins also accept file-objects instead of filenames (for
importing and also for exporting), for example:

```python
from io import BytesIO

fobj = BytesIO()
rows.export_to_csv(legislators, fobj)
fobj.seek(0)  # You need to point the file cursor to the first position.
print(fobj.read())
```

The following text will be printed:

```text
b"title,firstname,lastname,party\r\nSen,Robert,Byrd,D\r\nRep,Ralph,Hall,R[...]"
```

The same happens for `sqlite3.Connection` objects when importing:

```python
# Reuses the `connection` and `query` variables from the last sections' example
table = rows.import_from_sqlite(connection, query=query)
print(rows.export_to_txt(table))
```

The following output will be printed:

```text
+-----------+-----------------+
| firstname |     lastname    |
+-----------+-----------------+
|    Darren |            Soto |
|      Adam |       Kinzinger |
|       Ron |        DeSantis |
| Stephanie |          Murphy |
|      Seth |         Moulton |
|     Jaime | Herrera Beutler |
|      Pete |         Aguilar |
|     Scott |          Taylor |
|       Jim |           Banks |
|     Ruben |         Gallego |
|       Lee |          Zeldin |
|    Carlos |         Curbelo |
|    Justin |           Amash |
|     Ruben |          Kihuen |
|     Jason |           Smith |
|     Brian |            Mast |
|    Joseph |         Kennedy |
|      Eric |        Swalwell |
|     Tulsi |         Gabbard |
|     Aaron |          Schock |
|      Matt |           Gaetz |
|      Trey |   Hollingsworth |
|      Mike |       Gallagher |
|     Elise |        Stefanik |
+-----------+-----------------+
```

## Learn more

Now you have finished the quickstart guide. See the [examples][rows-examples]
folder for more examples.


[rows-examples]: https://github.com/turicas/rows/tree/master/examples
[worldometers-population-table]: http://www.worldometers.info/world-population/population-by-country/
