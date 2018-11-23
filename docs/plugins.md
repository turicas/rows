# Plugins

The idea behing plugins is very simple: you write a little piece of code which
extracts data from/to some specific format and the library will do the other
tasks for you, such as detecting and converting data types. So writing a plugin
is as easy as reading from/writing to the file format you want. If you don't
find the plugin for the format you need, feel free [to
contribute][doc-contributing]. :-)

Each `import_from_*` function receive specific parameters (depending on the
format you're working) but also general parameters such as `skip_header` and
`fields` (they are passed to the [rows.plugins.utils.create_table
function][create-table-function]).

Some plugins also provide helper functions to work with the specific format,
which can help a lot extracting non-tabular data (like
`rows.plugins.html.extract_links` and `rows.plugins.pdf.pdf_to_text`).

This documentation is still in progress - please look into [the plugins' source
code][plugins-source] to see all available parameters. Contributions on the
documentation are very welcome. Look into the [examples folder][examples] to
see the plugins in action. :)

Current implemented plugins:


## CSV

Use `rows.import_from_csv` and `rows.export_to_csv` (dependencies are installed
by default). The CSV dialect is **detected automatically** but you can specify
it by passing the `dialect` parameter.

Helper functions:

- `rows.plugins.pdf.discover_dialect`: tries to figure out the CSV dialect
  based on a sample (in bytes).
- `rows.utils.csv2sqlite`: lazily convert a CSV into a SQLite table (the
  command-line version of this function is pretty useful -- see more by running
  `rows csv2sqlite --help`). The CSV can be optionally compressed (`.csv`,
  `.csv.gz` and `.csv.xz`).

Learn by example:

- [`examples/library/usa_legislators.py`][example-legislators]


## TXT

Use `rows.import_from_txt` and `rows.export_to_txt` (no dependencies). You can
customize the border style.


## List of dicts

Use `rows.import_from_dicts` and `rows.export_to_dicts` (no dependencies).
Useful when you have the data in memory and would like to detect/convert data
types and/or export to a supported format.

Learn by example:

- [`examples/library/organizaciones.py`][example-organizaciones]


## JSON

Use `rows.import_from_json` and `rows.export_to_json` (no dependencies). Each
table is converted to an array of objects (where each row is represented by an
object).


## HTML

Use `rows.import_from_html` and `rows.export_to_html` (dependencies must be
installed with `pip install rows[html]`). You can pass the table index (in case
there's more than one `<table>` inside the HTML) and decide to kee the HTML
inside the `<td>` tags (useful to extract links and data inside HTML
properties).

Learn by example:

- [`examples/library/airports.py`][example-airports]
- [`examples/library/extract_links.py`][example-extract-links]
- [`examples/library/slip_opinions.py`][example-slip-opinions]


Helper functions:

- `rows.plugins.html.count_tables`: return the number of tables for a given
  HTML;
- `rows.plugins.html.tag_to_dict`: extract tag's attributes into a `dict`;
- `rows.plugins.html.extract_text`: extract the text content from a given HTML;
- `rows.plugins.html.extract_links`: extract the `href` attributes from a given
  HTML (returns a list of strings).


## XPath

Dependencies must be installed with `pip install rows[xpath]`). Use
`rows.import_from_xpath` passing the following arguments:

- `filename_or_fobj`: source XML/HTML;
- `rows_xpath`: each result must represent a row in the new returned `Table`;
- `fields_xpath`: must be an `collections.OrderedDict`, where the key is the
  field name and the value the XPath to extract the desired value for this
  field (you'll probrably want to use `./` so it'll search inside the row found
  by `rows_xpath`).

Learn by example:

- [`examples/library/ecuador_radiodifusoras.py`][example-radiodifusoras]
- [`examples/library/brazilian_cities_wikipedia.py`][example-br-cities]


## Parquet

Use `rows.import_from_parquet` passing the filename (dependencies must be
installed with `pip install rows[parquet]` and if the data is compressed using
snappy you'll also need to `pip install rows[parquet-snappy]` and the
`libsnappy-dev` system library) -- read [this blog post][blog-rows-parquet] for
more details and one example.


## PDF

Use `rows.import_from_pdf` (dependencies must be installed with `pip install
rows[pdf]`).


### PDF Parser Backend

There are two available backends (under-the-hood libraries to parse the PDF),
which you can select by passing the `backend` parameter (results may differ
depending on the backend):

- `'pymupdf'`: use if possible, is much faster than the other option;
- `'pdfminer'`: 100% Python implementation, very slow.

Get this list programatically with `rows.plugins.pdf.backends()`. You can also
subclass `rows.plugins.pdf.PDFBackend` and implement your own PDF parser (not
recommended).


### Specify Table Boundaries

You can specify some parameters to delimit where the table is located in the
PDF, like:

- `starts_after` and `ends_before`: delimits the objects before/after the
  table. Can be:
  - Regular strings (exact match);
  - Regular expressions;
  - Functions (receives the object and must return `True` for the object which
    define if the table starts/ends there).
- `page_numbers`: sequence with desired page numbers (starts from `1`);


### Specify Detection Algorithms

There are 3 available algorithms to identify text objects and define where the
table is located inside each page - you can subclass them and overwrite some
methods to have custom behaviour (like the `get_lines`, where you can access
objects' positions, for example). The algorithms available are (get the list
programatically with `rows.plugins.pdf.algorithms()`):

- `rows.plugins.pdf.YGroupsAlgorithm`: default, group text objects by y
  position and identify table lines based on these groups.
- `rows.plugins.pdf.HeaderPositionAlgorithm`:
- `rows.plugins.pdf.RectsBoundariesAlgorithm`: detect the table boundaries by
  the rectangles on the page (currently only available using the `'pdfminer'`
  backend, which is very slow).


### Helper Functions

- `rows.plugins.pdf.number_of_pages`: returns an integer representing the
  number of pages of a specific PDF file/stream;
- `rows.plugins.pdf.pdf_to_text`: generator: each iteration will return the
  text for a specific page (can specify `page_numbers` to delimit which pages
  will be returned);
- `rows.plugins.pdf.pdf_table_lines`: almost the same as
  `rows.import_from_pdf`, but returns a list of strings instead of a
  `rows.Table` object. Useful if the PDF is not well structured and needs some
  tweaking before importing as a `rows.Table` (so youcan extract to another
  format).

### Examples

- [`balneabilidade-bahia`][example-balneabilidade]: scraping project (downloads
  1400+ PDFs from a Brazilian organization which monitors water quality, then
  extract the tables in each PDF and put all rows together in one CSV).
- [`examples/cli/extract-pdf.sh`][example-pdf-cli]: PDF extraction using the
  command-line interface (the parameters cannot be customized using this method
  by now).


## XLS

Use `rows.import_from_xls` and `rows.export_to_xls` (dependencies must be
installed with `pip install rows[xls]`). You can customize things like
`sheet_name`, `sheet_index`, `start_row`, `end_row`, `start_column` and
`end_column` (the last 5 options are indexes and starts from 0).

On `rows.export_to_xls` you can define the `sheet_name`.


## XLSX

use `rows.import_from_xlsx` and `rows.export_to_xlsx` (dependencies must be
installed with `pip install rows[xlsx]`). You can customize things like
`sheet_name`, `sheet_index`, `start_row`, `end_row`, `start_column` and
`end_column` (the last 5 options are indexes and starts from 0).

On `rows.export_to_xlsx` you can define the `sheet_name`.


## SQLite

Use `rows.import_from_sqlite` and `rows.export_to_sqlite` (no dependencies).

Helper functions:

- `rows.utils.sqlite2csv`: lazily SQLite tables into CSV files (the
  command-line version of this function is pretty useful -- see more by running
  `rows sqlite2csv --help`). The CSV can be optionally compressed (`.csv`,
  `.csv.gz` and `.csv.xz`).


## PostgreSQL

Use `rows.import_from_postgresql` and `rows.export_to_postgresql` (dependencies
must be installed with `pip install rows[postgresql]`).

### Parameters

On both `rows.import_from_postgresql` and `rows.export_to_postgresql` you can pass
either a connection string or a `psycopg2` connection object.

On `rows.import_from_postgresql` you can pass a `query` parameter instead of a
`table_name`.

### Helper Functions

- `rows.utils.pgimport`: import data from CSV into PostgreSQL using the fastest
  possible method - requires the `psql` command available on your system (the
  command-line version of this function is pretty useful -- see more by running
  `rows pgimport --help`). The CSV can be optionally compressed (`.csv`,
  `.csv.gz` and `.csv.xz`);
- `rows.utils.pgexport`: export data from PostgreSQL into a CSV file using the
  fastest possible method - requires the `psql` command available on your
  system (the command-line version of this function is pretty useful -- see
  more by running `rows pgexport --help`). The CSV can be optionally compressed
  (`.csv`, `.csv.gz` and `.csv.xz`).


## ODS

Use `rows.import_from_ods` (dependencies must be installed with `pip install
rows[ods]`).


[blog-rows-parquet]: http://blog.justen.eng.br/2016/03/reading-parquet-files-in-python-with-rows.html
[create-table-function]: https://github.com/turicas/rows/blob/develop/rows/utils.py
[plugins-source]: https://github.com/turicas/rows/tree/develop/rows/plugins
[examples]: https://github.com/turicas/rows/tree/develop/examples/library
[example-airports]: https://github.com/turicas/rows/blob/develop/examples/library/airports.py
[example-radiodifusoras]: https://github.com/turicas/rows/blob/develop/examples/library/ecuador_radiodifusoras.py
[example-br-cities]: https://github.com/turicas/rows/blob/develop/examples/library/brazilian_cities_wikipedia.py
[example-extract-links]: https://github.com/turicas/rows/blob/develop/examples/library/extract_links.py
[example-organizaciones]:[https://github.com/turicas/rows/blob/develop/examples/library/organizaciones.py]
[example-slip-opinions]: https://github.com/turicas/rows/blob/develop/examples/library/slip_opinions.py
[example-legislators]: https://github.com/turicas/rows/blob/develop/examples/library/usa_legislators.py
[example-balneabilidade]: https://github.com/Correio24horas/balneabilidade-bahia
[example-pdf-cli]: https://github.com/turicas/rows/blob/develop/examples/cli/extract-pdf.sh
