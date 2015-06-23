# rows

This library is intended to be the easiest way to access tabular data using
Python, regardless of the format it's stored or will be extracted to; some
examples include CSV, HTML, XLS and ODS.

The API is pretty straighforward: it's composed of plugins that can import
and/or export tabular data to/from one of the supported classes (`Table` and
`LazyTable` currently); each plugin implements a format, like CSV and HTML. It
makes the library perfect for converting data between these formats and focus
on **the data** itself (not on format-specific things).


## Installation

`rows` is not available on PyPI yet (we need more tests), so you need to
install using `setup.py`:

    git clone https://github.com/turicas/rows.git
    cd rows
    python setup.py install


## Using

Create a file called `data.csv` with this content:

    id,username,birthday
    1,turicas,1987-04-29
    2,kid,2000-01-01


### Importing and Exporing data

Try this out:

    import rows

    my_table = rows.import_from_csv('data.csv')
    my_table.export_to_html('data.html')

Then a file `data.html` will be created with the following content:

    <table>

      <thead>
        <tr>
          <th>id</th>
          <th>username</th>
          <th>birthday</th>
        </tr>
      </thead>

      <tbody>

        <tr class="odd">
          <td>1</td>
          <td>turicas</td>
          <td>1987-04-29</td>
        </tr>

        <tr class="even">
          <td>2</td>
          <td>kid</td>
          <td>2000-01-01</td>
        </tr>

      </tbody>
    </table>


You can also use `rows.import_from_html` and `my_table.export_to_csv` methods.


### Iterating over `Table`/`LazyTable` objects

The `Table`/`LazyTable` objects are iterable and return a dictionary in each
iteration:

    import rows

    my_table = rows.import_from_csv('data.csv')
    for row in my_table:
        print(row)

Then you'll see:

    {u'username': u'turicas', u'birthday': datetime.date(1987, 4, 29), u'id': 1}
    {u'username': u'kid', u'birthday': datetime.date(2000, 1, 1), u'id': 2}


> Note that **native Python objects** are returned! The library recognizes
> each field type and convert data *automagically*.


### Supported Plugins

A plugin is just a Python module with one or two functions:

- `import_from_PLUGINNAME`: receives parameters as input data (filename, for
  example) and return a `Table`/`LazyTable` object; and
- `export_to_PLUGINNAME`: receives a `Table`/`LazyTable` object (and possibly
  some options) and export to the format.

Currently we have the following plugins:

- Text (export only)
- CSV (import and export)
- HTML (import and export)
- MySQL/MariaDB (import and export)


The idea is to develop more plugins, such as:

- SQLite
- PostgreSQL
- JSON
- BSON
- Protocol Buffers
- Message Pack
- ODS (Open Document Spreadsheet)
- XLS and XLSX (Excel Spreadsheet)

If you feel confortable on writting one of these, please create a pull request!
Don't forget to add your name to `AUTHORS` file. :-)


### Custom Types and Converters

When importing data from formats that do not specify any kind of metadata about
the field types, like CSV and HTML, `rows` tries to figure out which type
belongs to each field. For this to work, **type converters** were implemented:
they are simple functions that receive raw data (example: `'2014-05-06'`) and
return Python objects (example: `datetime.date(2014, 5, 6)`).

You can specify custom type converters so the library will use your
functions to convert raw data, instead of the standard ones. It's pretty useful
if your data is stored using a non-standard format, since the library
automatically deals with the standard ones (booleans, integers, floating
points, dates, datetimes and strings).

Example usage: I receive many CSVs with the `date` field in the `dd/mm/yy`
format (vastly used in Brazil), so I can provide a new function to deal with it
and return `datetime.date` objects (or actually any object type I want). I just
need to create a new type converter and specify it when importing data:

    import datetime

    from re import compile as regexp_compile

    import rows

    from rows.converters import NULL


    BR_DATE_REGEXP = regexp_compile('^[0-9]{2}/[0-9]{2}/[0-9]{2}$')

    def convert_br_date(value, input_encoding):
        value = unicode(value).lower().strip()
        if not value or value in NULL:
            return None

        if BR_DATE_REGEXP.match(value) is None:
            raise ValueError("Can't be date")
        else:
            day, month, year = [int(x) for x in unicode(value).split('/')]
            if year < 20: # guessing it's 2000's
                year += 2000
            else:
                year += 1900
            return datetime.date(year, month, day)


Now I can create a file with the dates using the Brazilian date format named
`data-br.csv`:

    id,username,birthday
    1,turicas,29/04/87
    2,kid,01/01/90

...and specify our custom converter function when importing:


    import rows

    my_table = rows.import_from_csv('data-br.csv',
            converters={datetime.date: convert_br_date})
    for row in my_table:
        print(row)

Then you'll see:

    {u'username': u'turicas', u'birthday': datetime.date(1987, 4, 29), u'id': 1}
    {u'username': u'another-user', u'birthday': datetime.date(2000, 1, 1), u'id': 2}

Enjoy the data!

> Note 1: technically each plugin have its own way to deal with `converters`,
> but a standard way of doing this in all plugins is being researched.

> Note 2: the converters work only for converting input data (raw) to native
> Python types; we still need to add support for custom converters to
> export native types (for example: currently `datetime.date` objects will
> *always* be exported using the `%Y-%m-%d` format).

#### Locale-aware converters

The standard converters are locale-aware, it means that decimal and thousand
separators can be correctly identified just setting the correct locale. Let's
go to an example -- create a file named `brazilian-cities.csv` with this
content:

    state,city_name,inhabitants
    RJ,Rio de Janeiro,6.320.446
    RJ,Niterói,487.562
    RJ,Três Rios,77.432

...and execute this code:


    import locale

    import rows


    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    my_table = rows.import_from_csv('brazilian-cities.csv')
    for row in my_table:
        print(row)

Then you'll see:

    {u'city_name': u'Rio de Janeiro', u'inhabitants': 6320446, u'state': u'RJ'}
    {u'city_name': u'Niter\xf3i', u'inhabitants': 487562, u'state': u'RJ'}
    {u'city_name': u'Tr\xeas Rios', u'inhabitants': 77432, u'state': u'RJ'}

As `.`  is the thousands separator for `pt_BR` locale, the `inhabitants` field
is identified to be `int`.


> Note: currently, the standard `datetime.date` and `datetime.datetime` do not
> support locale-aware data (we still need to fix this).


### Table Operations


#### Sum

If you have more than one `Table`/`LazyTable` object with the same fields
(`table.fields`) and fields types (`table.types`), you can put all the rows
together in one table just summing the objects, like this:

    result = some_rows + other_rows

You can also use the built-in `sum` method:

    result = sum([table_1, table_2, table_3, ...])


#### Join

There is a simple way to merge tables which share a foreign key but different
other fields into one table. For example, create the file `city-area.csv` with
the content:

    state,city_name,area_km2
    RJ,Rio de Janeiro,1200
    RJ,Niterói,133
    RJ,Três Rios,326

Now, import and join the tables:

    import locale

    import rows


    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    table_1 = rows.import_from_csv('brazilian-cities.csv')
    table_2 = rows.import_from_csv('city-area.csv')

    # Pass the keys to group rows and the tables to `join`:
    result = rows.join(('state', 'city_name'), table_1, table_2)
    for row in result:
        print(row)

The result:

    {u'city_name': u'Niter\xf3i', u'inhabitants': 487562, u'state': u'RJ', u'area_km2': 133}
    {u'city_name': u'Tr\xeas Rios', u'inhabitants': 77432, u'state': u'RJ', u'area_km2': 326}
    {u'city_name': u'Rio de Janeiro', u'inhabitants': 6320446, u'state': u'RJ', u'area_km2': 1200}


### Command-Line Interface

You can use simple import-from/export-to functions for all available plugins
through a CLI:

    rows --from examples/data.csv --to examples/data.txt

Will create the file `examples/data.txt` with the content as:

    +----+--------------+------------+
    | id |   username   |  birthday  |
    +----+--------------+------------+
    |  1 |      turicas | 1987-04-29 |
    |  2 | another-user | 2000-01-01 |
    +----+--------------+------------+


## License

This library is released under the [GNU General Public License version
3](http://www.gnu.org/licenses/gpl-3.0.html).


## Related projects

- <https://github.com/scraperwiki/scrumble/>
- <https://nytlabs.github.io/streamtools/>
- <https://github.com/Kozea/Multicorn>
- Kettle/Pentaho?
- Talend?

## Possible new formats (to support)

- .sif
- sql
- excel
- json
- msgpack
- hdf
- gbq
- stata
- protocol buffers
