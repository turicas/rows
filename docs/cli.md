# Command-Line Interface

`rows` exposes a command-line interface with common operations such as
converting and querying data.

> Note: we still need to improve this documentation. Please run `rows --help`
> to see all the available commands and take a look at [rows/cli.py][rows-cli].


## Commands

All the commands accepts any of the formats supported by the library (unless
in some specific/optimized cases, like `csv2sqlite`, `sqlite2csv`, `pgimport`
and `pgexport`) and for all input data you can specify an URL instead of a
local filename (example: `rows convert https://website/file.html file.csv`).

> Note: you must install the specific dependencies for each format you want
> support (example: to extract tables from HTML the Python library `lxml` is
> required).

- [`rows convert`][cli-convert]: convert a table from one format to another.
- [`rows csv2sqlite`][cli-csv2sqlite]: convert one or more CSV files
  (compressed or not) to SQLite in an optimized way (if source is CSV and
  destination is SQLite, use this rather than `rows convert`).
- [`rows join`][cli-join]: equivalent to SQL's `JOIN` - get rows from each
  table and join them.
- [`rows pgexport`][cli-pgexport]: export a PostgreSQL table into a CSV file
  (compressed or not) in the most optimized way: using `psql`'s `COPY` command.
- [`rows pgimport`][cli-pgimport]: import a CSV file (compressed or not) into a
  PostgreSQL table in the most optimized way: using `psql`'s `COPY` command.
- [`rows print`][cli-print]: print a table in the standard output (you can
  choose between some frame styles).
- [`rows query`][cli-query]: query a table using SQL (converts the table to an
  in-memory SQLite database) and output to the standard output or a file.
- [`rows schema`][cli-schema]: inspects a table and defines its schema. Can
  output in many formats, like text, SQL or even Django models.
- [`rows sqlite2csv`][cli-sqlite2csv]: convert a SQLite table into a CSV file
  (compressed or not).
- [`rows sum`][cli-sum]: aggreate the rows of two equivalent tables (must have
  same field names and types), equivalent to SQL's `UNION`.

> Note: everytime we specify "compressed or not" means you can use the file as
> is or a compressed version of it. The supported compression formats are:
> gzip (`.gz`), lzma (`.xz`) and bzip2 (`.bz2`). The [support for archive
> formats such as zip, tar and rar will be implemented in the
> future][issue-archives].


## Global and Common Parameters

Some parameters are global to the command-line interface and the sub-commands
also have specific options. The global options are:

- `--http-cache=BOOLEAN`: Enable/disable HTTP cache (default: `true`)
- `--http-cache-path=TEXT`: Set HTTP cache path (default:
  `USER_HOME_PATH/.cache/rows/http`


## `rows convert`

Convert a table from a `source` URI to `destination`. Useful to convert files
between formats, like extracting data from a HTML table and converting to CSV.

Usage: `rows convert [OPTIONS] SOURCE DESTINATION`

Options:
- `--input-encoding=TEXT`: Encoding of input tables (default: `utf-8`)
- `--output-encoding=TEXT`: Encoding of output tables (default: `utf-8`)
- `--input-locale=TEXT`: Locale of input tables. Used to parse integers, floats
  etc. (default: `C`)
- `--output-locale=TEXT`: Locale of output tables. Used to parse integers,
  floats etc. (default: `C`)
- `--verify-ssl=BOOLEAN`: Verify SSL certificate, if source is downloaded via
  HTTPS (default: `true`)
- `--order-by=TEXT`: Order result by this field (default: same order as input
  data)
- `--fields=TEXT`: A comma-separated list of fields to import (default: all
  fields)
- `--fields-exclude=TEXT`: A comma-separated list of fields to exclude when
  exporting (default: all fields)

Example:

```bash
# needs: pip install rows[html]
rows convert \
    http://www.sports-reference.com/olympics/countries/BRA/summer/2016/ \
    brazil-2016.csv
```


## `rows csv2sqlite`

Convert one or more CSV files (compressed or not) to SQLite in an optimized way
(if source is CSV and destination is SQLite, use this rather than `rows
convert`). The supported compression formats are: gzip (`.gz`), lzma (`.xz`)
and bzip2 (`.bz2`).

Usage: `rows csv2sqlite [OPTIONS] SOURCES... OUTPUT`

Options:

- `--batch-size=INTEGER`: number of rows to batch insert into SQLite (default:
  `10000`)
- `--samples=INTEGER`: number of sample rows to detect schema (default: `5000`)
- `--input-encoding=TEXT`: input encoding (default: `utf-8`)
- `--dialect=TEXT`: CSV dialect to be used (default: will detect automatically)
- `--schemas=TEXT`: comma-separated list of schema files (default: will detect
  automatically) - these files must have the columns `field_name` and
  `field_type` (you can see and example by running [`rows schema`][cli-schema])

Example:

```bash
rows csv2sqlite \
     --dialect=excel \
     --input-encoding=latin1 \
     file1.csv file2.csv \
     result.sqlite
```


## `rows join`

Join tables from `source` URIs using `key(s)` to group rows and save into
`destination`.

Usage: `rows join [OPTIONS] KEYS SOURCES... DESTINATION`

Options:
- `--input-encoding=TEXT`: Encoding of input tables (default: `utf-8`)
- `--output-encoding=TEXT`: Encoding of output tables (default: `utf-8`)
- `--input-locale=TEXT`: Locale of input tables. Used to parse integers, floats
  etc. (default: `C`)
- `--output-locale=TEXT`: Locale of output tables. Used to parse integers,
  floats etc. (default: `C`)
- `--verify-ssl=BOOLEAN`: Verify SSL certificate, if source is downloaded via
  HTTPS (default: `true`)
- `--order-by=TEXT`: Order result by this field (default: same order as input
  data)
- `--fields=TEXT`: A comma-separated list of fields to import (default: all
  fields)
- `--fields-exclude=TEXT`: A comma-separated list of fields to exclude when
  exporting (default: all fields)

Example: join `a.csv` and `b.csv` into a new file called `c.csv` using the
field `id` as a key (both `a.csv` and `b.csv` must have the field `id`):

```bash
rows join id a.csv b.csv c.csv
```

## `rows pgexport`

Export a PostgreSQL table into a CSV file (compressed or not) in the most
optimized way: using `psql`'s `COPY` command. The supported compression formats
are: gzip (`.gz`), lzma (`.xz`) and bzip2 (`.bz2`).

Usage: `rows pgexport [OPTIONS] DATABASE_URI TABLE_NAME DESTINATION`

Options:

- `--output-encoding=TEXT`: encoding to be used on output file (default:
  `utf-8`)
- `--dialect=TEXT`: CSV dialect to be used on output file (default: `excel`)

Example:

```bash
# needs: pip install rows[postgresql]
rows pgexport \
    postgres://postgres:postgres@127.0.0.1:42001/rows \
    my_table \
    my_table.csv.gz
```


## `rows pgimport`

Import a CSV file (compressed or not) into a PostgreSQL table in the most
optimized way: using `psql`'s `COPY` command. The supported compression formats
are: gzip (`.gz`), lzma (`.xz`) and bzip2 (`.bz2`).

Usage: `rows pgimport [OPTIONS] SOURCE DATABASE_URI TABLE_NAME`

Options:
- `--input-encoding=TEXT`: Encoding of input CSV file (default: `utf-8`)
- `--no-create-table=BOOLEAN`: should rows create the table or leave it to
  PostgreSQL? (default: false, ie: create the table)
- `--dialect=TEXT`: CSV dialect to be used (default: will detect automatically)
- `--schemas=TEXT`: schema filename to be used (default: will detect schema
  automatically) - this file must have the columns `field_name` and
  `field_type` (you can see and example by running [`rows schema`][cli-schema])

Example:

```bash
# needs: pip install rows[postgresql]
rows pgimport \
    my_data.csv.xz \
    postgres://postgres:postgres@127.0.0.1:42001/rows \
    my_table
```


## `rows print`

Print the selected `source` table

Usage: `rows print [OPTIONS] SOURCE`

Options:

- `--input-encoding=TEXT`: Encoding of input tables (default: `utf-8`)
- `--output-encoding=TEXT`: Encoding of output tables (default: `utf-8`)
- `--input-locale=TEXT`: Locale of input tables. Used to parse integers, floats
  etc. (default: `C`)
- `--output-locale=TEXT`: Locale of output tables. Used to parse integers,
  floats etc. (default: `C`)
- `--verify-ssl=BOOLEAN`: Verify SSL certificate, if source is downloaded via
  HTTPS (default: `true`)
- `--order-by=TEXT`: Order result by this field (default: same order as input
  data)
- `--fields=TEXT`: A comma-separated list of fields to import (default: all
  fields)
- `--fields-exclude=TEXT`: A comma-separated list of fields to exclude when
  exporting (default: all fields)
- `--frame-style=TEXT`: frame style to "draw" the table; options: `ascii`,
  `single`, `double`, `none` (default: `ascii`)
- `--table-index=INTEGER`: if source is HTML, specify the table index to
  extract (default: `0`, ie: first `<table>` inside the HTML file)

Examples:

```bash
rows print \
    --fields=state,city \
    --order-by=city \
    data/brazilian-cities.csv
```

```bash
# needs: pip install rows[html]
rows print \
    --table-index=1 \  # extracts second table
    some-html-file.html
```

## `rows query`

Yep, you can SQL-query any supported file format! Each of the source files will
be a table inside an in-memory SQLite database, called `table1`, ..., `tableN`.
If the `--output` is not specified, `rows` will print a table on the standard
output.

Usage: `rows query [OPTIONS] QUERY SOURCES...`

Options:

- `--input-encoding=TEXT`: Encoding of input tables (default: `utf-8`)
- `--output-encoding=TEXT`: Encoding of output tables (default: `utf-8`)
- `--input-locale=TEXT`: Locale of input tables. Used to parse integers, floats
  etc. (default: `C`)
- `--output-locale=TEXT`: Locale of output tables. Used to parse integers,
  floats etc. (default: `C`)
- `--verify-ssl=BOOLEAN`: Verify SSL certificate, if source is downloaded via
  HTTPS (default: `true`)
- `--samples=INTEGER`: number of sample rows to detect schema (default: `5000`)
- `--output=TEXT`: filename to outputs - will use file extension to define
  which plugin to use (default: standard output, plugin text)
- `--frame-style=TEXT`: frame style to "draw" the table; options: `ascii`,
  `single`, `double`, `none` (default: `ascii`)

Examples:

```bash
# needs: pip install rows[html]
rows query \
    'SELECT * FROM table1 WHERE inhabitants > 1000000' \
    data/brazilian-cities.csv \
    --output=data/result.html
```

```bash
# needs: pip install rows[pdf]
rows query \
    'SELECT * FROM table1 WHERE categoria = "Imprópria"' \
    http://balneabilidade.inema.ba.gov.br/index.php/relatoriodebalneabilidade/geraBoletim?idcampanha=36381 \
    --output=bathing-conditions.xls
```

In the last example `rows` will:

- Download a file using HTTP
- Identify its format (PDF)
- Automatically extract a table based on objects' positions
- Create an in-memory database with extracted data
- Run the SQL query
- Export the result to XLS

In just one command, automatically. How crazy is that?


## `rows schema`

Identifies the table schema by inspecting data. The files generated by this
command (`txt` format) can be used in `--schema` and `--schemas` options (a CSV
version of these files can also be used).

Usage: `rows schema [OPTIONS] SOURCE [OUTPUT]`


Options:
- `--input-encoding=TEXT`: Encoding of input tables (default: `utf-8`)
- `--input-locale=TEXT`: Locale of input tables. Used to parse integers, floats
  etc. (default: `C`)
- `--verify-ssl=BOOLEAN`: Verify SSL certificate, if source is downloaded via
  HTTPS (default: `true`)
- `-f TEXT`, `--format=TEXT`: output format; options: `txt`, `sql`, `django`
  (default: `txt`)
- `--fields=TEXT`: A comma-separated list of fields to import (default: all
  fields)
- `--fields-exclude=TEXT`: A comma-separated list of fields to exclude when
  exporting (default: all fields)
- `--samples=INTEGER`: number of sample rows to detect schema (default: `5000`)


Example:

```bash
rows schema \
    --samples=100 \
    data/brazilian-cities.csv
```

Output:

```
+-------------+------------+
|  field_name | field_type |
+-------------+------------+
|       state |       text |
|        city |       text |
| inhabitants |    integer |
|        area |      float |
+-------------+------------+
```


## `rows sqlite2csv`

Convert a SQLite table into a CSV file (compressed or not). The supported
compression formats are: gzip (`.gz`), lzma (`.xz`) and bzip2 (`.bz2`).

Usage: `rows sqlite2csv [OPTIONS] SOURCE TABLE_NAME OUTPUT`

Options:
- `--batch-size=INTEGER`: number of rows to batch insert into SQLite (default:
  `10000`)
- `--dialect=TEXT`: CSV dialect to be used on output file (default: `excel`)

Example:

```bash
rows sqlite2csv \
    my_db.sqlite \
    my_table \
    my_table.csv.bz2
```


## `rows sum`

Sum tables from `source` URIs and save into `destination`. The tables must have
the same fields.

Usage: `rows sum [OPTIONS] SOURCES... DESTINATION`

Options:

- `--input-encoding=TEXT`: Encoding of input tables (default: `utf-8`)
- `--output-encoding=TEXT`: Encoding of output tables (default: `utf-8`)
- `--input-locale=TEXT`: Locale of input tables. Used to parse integers, floats
  etc. (default: `C`)
- `--output-locale=TEXT`: Locale of output tables. Used to parse integers,
  floats etc. (default: `C`)
- `--verify-ssl=BOOLEAN`: Verify SSL certificate, if source is downloaded via
  HTTPS (default: `true`)
- `--order-by=TEXT`: Order result by this field (default: same order as input
  data)
- `--fields=TEXT`: A comma-separated list of fields to import (default: all
  fields)
- `--fields-exclude=TEXT`: A comma-separated list of fields to exclude when
  exporting (default: all fields)

Example:

```bash
rows sum \
    --fields=id,name,phone \
    people.csv \  # This file has `id`, `name` and other fields
    phones.csv \  # This file has `id`, `phone` and other fields
    contacts.csv  # Will have `id`, `name` and `phone` fields
```


[cli-convert]: #rows-convert
[cli-csv2sqlite]: #rows-csv2sqlite
[cli-join]: #rows-join
[cli-pgexport]: #rows-pgexport
[cli-pgimport]: #rows-pgimport
[cli-print]: #rows-print
[cli-query]: #rows-query
[cli-schema]: #rows-schema
[cli-sqlite2csv]: #rows-sqlite2csv
[cli-sum]: #rows-sum
[issue-archives]: https://github.com/turicas/rows/issues/236
[rows-cli]: https://github.com/turicas/rows/blob/develop/rows/cli.py
