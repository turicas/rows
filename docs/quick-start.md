# Quick Start Guide

## Programatically creating a `Table` object

`rows` can import data from any of the supported formats and will return a
`Table` object for you, but you can also create a `Table` object by hand.

### Using `Table.append`

```python
from collections import OrderedDict
from rows import fields, Table

my_fields = OrderedDict([('name', fields.TextField),
                         ('age', fields.IntegerField),])
table = Table(fields=my_fields)
table.append({'name': 'Álvaro Justen', 'age': 30})
table.append({'name': 'Another Guy', 'age': 42})
```

Check also all the available field types inside `rows.fields`.


### From a `list` of `dict`s

A common use case is to have a `list` of `dict`s -- you can also import it, and
`rows` will automatically fill in the blanks (your `dict`s don't need to have
the same keys) and convert data:

```python
import rows

data = [{'name': 'Álvaro Justen', 'age': 30},
        {'name': 'Another Guy', 'age': 42},]
table = rows.import_from_dicts(data)
```

In this case, `table.fields` will be created automatically (`rows` will
identify the field type for each `dict` key).


## Iterating over a `Table`

You can iterate over a `Table` object and each returned object will be a
`namedtuple` where you can access row's data, like this:

```python
def print_person(person):
    print('{} is {} years old.'.format(person.name, person.age))


for person in table:
    # namedtuples are returned for each row
    print_person(person)
```

The result:

```text
Álvaro Justen is 30 years old.
Another Guy is 42 years old.
```


## Automatic type detection/convertion

`rows` will automatically identify data type for each column and converts it
for you. For example:

```python
table.append({'name': '...', 'age': ''})
print_person(table[-1])  # yes, you can index it!
```

And the output:

```text
... is None years old.
```


## Importing Data

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

print('Hey, rows automatically identified the types:')
for field_name, field_type in legislators.fields.items():
    print('{} is {}'.format(field_name, field_type))
```

And you'll see something like this:

```text
[...]
in_office is <class 'rows.fields.IntegerField'>
gender is <class 'rows.fields.TextField'>
[...]
birthdate is <class 'rows.fields.DateField'>
```

We can then work on this data:

```python
women = sum(1 for row in legislators if row.in_office and row.gender == 'F')
men = sum(1 for row in legislators if row.in_office and row.gender == 'M')
print('Women vs Men (in office): {} vs {}.'.format(women, men))
```

Then you'll see effects of our sexist society:

```text
Women vs Men: 108 vs 432.
```

Now, let's compare ages:

```python
legislators.order_by('birthdate')
older, younger = legislators[-1], legislators[0]
print('{}, {} is older than {}, {}.'.format(
      older.lastname, older.firstname, younger.lastname, younger.firstname))
```

The output:

```text
Stefanik, Elise is older than Byrd, Robert.
```

You can also get a whole column, like this:

```python
>>> legislators['gender']
['M',
 'M',
 'M',
 'M',
 'M',
 'M',
 'M',
 'M',
 'M',
 'M',
 'M',
 'M',
 'M',
 'M',
 'F',
 'M',
 ...]
```

And change the whole column (or add a new one):

```python
>>> legislators['gender'] = ['male' if gender == 'M' else 'female'
                             for gender in legislators['gender']]
>>> legislators['gender']
['male',
 'male',
 'male',
 'male',
 'male',
 'male',
 'male',
 'male',
 'male',
 'male',
 'male',
 'male',
 'female',
 'male',
 ...]
```

Or delete it:

```python
>>> 'gender' in legislators.field_names
True
>>> del legislators['gender']
>>> 'gender' in legislators.field_names
False
>>> legislators[0].gender
[...]
AttributeError: 'Row' object has no attribute 'gender'
```

> Note that **native Python objects** are returned for each row inside a
> `namedtuple`! The library recognizes each field type and converts it
> *automagically* no matter which plugin you're using to import the data.


### Common Parameters

Each plugin has its own parameters (like `index` in `import_from_html` and
`sheet_name` in `import_from_xls`) but all plugins create a `rows.Table` object
so they also have some common parameters you can pass to `import_from_X`. They
are:

- `fields`: an `OrderedDict` with field names and types (disable automatic
  detection of types).
- `force_types`: a `dict` mapping field names to field types you'd like to
  force, so `rows` won't try to detect it. Example:
  `{'name': rows.fields.TextField, 'age': rows.fields.IntegerField}`.
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
rows.export_to_html(legislators, 'legislators.html')
```

And you'll get:

```bash
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


### Exporting to memory

For some plugins you don't need to specify a filename, so the result will be
returned for you as a `str`. Example:

```python
fields_to_export = ('title', 'firstname', 'lastname', 'party')
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

The plugins `csv`, `json` and `html` will have the same behaviour.


#### Using file-objects

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

On `sqlite` plugin the returned object is a `sqlite3.Connection`:

```python
connection = rows.export_to_sqlite(legislators, ':memory:')
query = 'SELECT firstname, lastname FROM table1 WHERE birthdate > 1980-01-01'
connection = rows.export_to_sqlite(legislators, ':memory:')
print(list(connection.execute(query).fetchall()))
```

You'll get the following output:

```text
[('Darren', 'Soto'), ('Adam', 'Kinzinger'), ('Ron', 'DeSantis'), (...)]
```

And you can use `sqlite3.Connection` when importing, too:

```python
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


[rows-examples]: https://github.com/turicas/rows/tree/develop/examples
