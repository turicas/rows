# Log of Changes

## Version `0.4.2dev0`

**Released on: (in development)**

### General Changes and Enhancements

- `export_to_html` is now available even if `lxml` is not installed
- Add Jupyter Notebook integration (implements `_repr_html_`, `.head` and
  `.tail`)
- Fix code to remove some warnings
- Add support to read compressed files directly (like in
  `rows.import_from_csv("filename.csv.gz")`)
- `rows.Table` now returns a new table when sliced

### Plugins

- Add param `max_rows` to `create_table` (import only part of a table, all
  plugins are supported)
- Add `start_row`, `end_row`, `start_column` and `end_column` to ODS plugin
- Prevent `xlrd` (XLS plugin) from printing wrong sector size warning
  ("`WARNING *** file size (551546) not 512 + multiple of sector size (512)`")
- Set `rows.Table` name (`table.meta["name"]`) for ODS, XLS and XLSX plugins
- Add option to set `<caption>` tag in `export_to_html`

### Command-Line Interface

- `rows schema` (CLI) is now "lazy" (before it imported the whole file, even if
  samples were defined)
- Add support for compressed files output on `rows pdf-to-text` and `rows schema`

### Utils

- Add support for CSV format on schema export
- Use dataclasses to describe Source
- `import_from_source` now supports compressed files (and so all CLI commands)
- Add support for passing a `context` to `load_schema`

### Bug Fixes

- [#314](https://github.com/turicas/rows/issues/314) rows pgimport fails if
  using --schema
- [#309](https://github.com/turicas/rows/issues/309) Fix file-magic detection
- [#320](https://github.com/turicas/rows/issues/320) Get correct data if ODS
  spreadsheet has empty cells
- Fix slug function (so `"a/b"` will turn into `"a_b"`)

## Version `0.4.1` (bugfix release)

**Released on: 2019-02-14**

### General Changes and Enhancements

- Add new way to make docs (remove sphinx and uses mkdocs + click-man + pycco)
- Update Dockerfile


### Bug Fixes

- [#305](https://github.com/turicas/rows/issues/305) "0" was not being
  deserialized by `IntegerField`


## Version `0.4.0`

**Released on: 2019-02-09**


### General Changes and Enhancements

- [#243](https://github.com/turicas/rows/issues/243) Change license to LGPL3.0.
- Added official Python 3.6 support.
- `Table.__add__` does not depend on table sizes anymore.
- Implemented `Table.__iadd__` (`table += other` will work).
- [#234](https://github.com/turicas/rows/issues/234) Remove `BinaryField` from
  the default list of detection types.

### Plugins

- [#224](https://github.com/turicas/rows/issues/224) Add `|` as possible
  delimiter (CSV dialect detection).
- Export CSV in batches.
- Change CSV dialect detection sample size to 256KiB.
- [#225](https://github.com/turicas/rows/issues/225) Create export callbacks
  (CSV and SQLite plugins).
- [#270](https://github.com/turicas/rows/pull/270) Added options to export
  pretty text table frames (TXT plugin).
- [#274](https://github.com/turicas/rows/issues/274) `start_row` and
  `start_column` now behave the same way in XLS and XLSX (starting from 0).
- [#261](https://github.com/turicas/rows/issues/261) Add support to `end_row`
  and `end_column` on XLS and XLSX (thanks
  [@Lrcezimbra](https://github.com/Lrcezimbra) for the suggestion).
- [#4](https://github.com/turicas/rows/issues/4) Add PostgreSQL plugin (thanks
  to [@juliano777](https://github.com/juliano777)).
- [#290](https://github.com/turicas/rows/pull/290) Fix percent formatting
  reading on XLSX and ODS file formats (thanks to
  [@jsbueno](https://github.com/jsbueno)).
- [#220](https://github.com/turicas/rows/issues/220) Do not use
  non-import_fields and force_types columns on type detection algorithm.
- [#50](https://github.com/turicas/rows/issues/50) Create PDF extraction plugin
  with two backend libraries (`pymupdf` and `pdfminer.six`) and 3 table
  extraction algorithms.
- [#294](https://github.com/isses/294) Decrease XLSX reading time (thanks to
  [@israelst](https://github.com/israelst)).
- Change to pure Python version of Apache Thrift library (parquet plugin)
- [@299](https://github.com/turicas/rows/issues/299) Change CSV field limit

### Command-Line Interface

- [#242](https://github.com/turicas/rows/issues/242) Add
  `--fields`/`--fields-exclude` to `convert`, `join` and `sum` (and rename
  `--fields-exclude` on `print`), also remove `--fields` from `query` (is not
  needed).
- [#235](https://github.com/turicas/rows/issues/235) Implement `--http-cache`
  and `--http-cache-path`.
- [#237](https://github.com/turicas/rows/issues/237) Implement `rows schema`
  (generates schema in text, SQL and Django models).
- Enable progress bar when downloading files.
- Create `pgimport` and `pgexport` commands.
- Create `csv-to-sqlite` and `sqlite-to-csv` commands.
- Create `pdf-to-text` command.
- Add shortcut for all command names: `2` can be used instead of `-to-` (so
  `rows pdf2text` is a shortcut to `rows pdf-to-text`).

### Utils

- Create `utils.open_compressed` helper function: can read/write files,
  automatically dealing with on-the-fly compression.
- Add progress bar support to `utils.download_file` (thanks to `tqdm` library).
- Add helper class `utils.CsvLazyDictWriter` (write as `dict`s without needing
  to pass the keys in advance).
- Add `utils.pgimport` and `utils.pgexport` functions.
- Add `utils.csv2sqlite` and `utils.sqlite2csv` functions.

### Bug Fixes

- [#223](https://github.com/turicas/rows/issues/223) `UnicodeDecodeError` on
  dialect detection.
- [#214](https://github.com/turicas/rows/issues/214) Problem detecting dialect.
- [#181](https://github.com/turicas/rows/issues/181) Create slugs inside
  `Table.__init__`.
- [#221](https://github.com/turicas/rows/issues/221) Error on `pip install rows`.
- [#238](https://github.com/turicas/rows/issues/238) `import_from_dicts`
  supports generator as input
- [#239](https://github.com/turicas/rows/issues/239) Use correct field ordering
- [#299](https://github.com/turicas/rows/issues/302) Integer field detected for
  numbers started with zero

## Version `0.3.1`

**Released on: 2017-05-08**

### Enhancements

- Move information on README to a site, organize and add more examples.
  Documentation is available at [turicas.info/rows](http://turicas.info/rows).
  Thanks to [@ellisonleao](https://github.com/ellisonleao) for Sphinx
  implementation and [@ramiroluz](https://github.com/ramiroluz) for new
  examples.
- Little code refactorings.

### Bug Fixes

- [#200](https://github.com/turicas/rows/pull/200) Escape output when exporting
  to HTML (thanks to [@arloc](https://github.com/arloc))
- Fix some tests
- [#215](https://github.com/turicas/rows/issues/215) DecimalField does not
  handle negative values correctly if using locale (thanks to
  [@draug3n](https://github.com/draug3n) for reporting)


## Version `0.3.0`

**Released on: 2016-09-02**

### Backwards Incompatible Changes

### Bug Fixes

- Return `None` on XLS blank cells;
- [#188](https://github.com/turicas/rows/issues/188) Change `sample_size` on
  encoding detection.


### Enhancements and Refactorings

- `rows.fields.detect_fields` will consider `BinaryField` if all the values are
  `str` (Python 2)/`bytes` (Python 3) and all other fields will work only with
  `unicode` (Python 2)/`str` (Python 3);
- Plugins HTML and XPath now uses a better way to return inner HTML (when
  `preserve_html=True`);
- [#189](https://github.com/turicas/rows/issues/189) Optimize `Table.__add__`.


### New Features

- Support for Python 3 (finally!);
- `rows.fields.BinaryField` now automatically uses base64 to encode/decode;
- Added `encoding` information to `rows.Table` metadata in text plugins;
- Added `sheet_name` information to `rows.Table` metadata in XLS and XLSX
  plugins;
- [#190](https://github.com/turicas/rows/issues/190) Add `query_args` to
  `import_from_sqlite`;
- [#177](https://github.com/turicas/rows/issues/177) Add `dialect` to
  `export_to_csv`.


## Version `0.2.1`

**Released on: 2016-08-10**

### Backwards Incompatible Changes

- `rows.utils.export_to_uri` signature is now like `rows.export_to_*` (first
  the `rows.Table` object, then the URI)
- Changed default table name in `import_from_sqlite` and `export_to_sqlite`
  (from `rows` and `rows_{number}` to `table{number}`)


### Bug Fixes

- [#170](https://github.com/turicas/rows/issues/170) (SQLite plugin) Error
  converting `int` and `float` when value is `None`.
- [#168](https://github.com/turicas/rows/issues/168) Use `Field.serialize`
  if does not know the field type (affecting: XLS, XLSX and SQLite plugins).
- [#167](https://github.com/turicas/rows/issues/167) Use more data to detect
  dialect, delimit the possible delimiters and fallback to excel if can't
  detect.
- [#176](https://github.com/turicas/rows/issues/176) Problem using quotes on
  CSV plugin.
- [#179](https://github.com/turicas/rows/issues/179) Fix double underscore
  problem on `rows.utils.slug`
- [#175](https://github.com/turicas/rows/issues/175) Fix `None`
  serialization/deserialization in all plugins (and also field types)
- [#172](https://github.com/turicas/rows/issues/172) Expose all tables in `rows
  query` for SQLite databases
- Fix `examples/cli/convert.sh` (missing `-`)
- Avoids SQL injection in table name


### Enhancements and Refactorings

- Refactor `rows.utils.import_from_uri`
- Encoding and file type are better detected on `rows.utils.import_from_uri`
- Added helper functions to `rows.utils` regarding encoding and file
  type/plugin detection
- There's a better description of plugin metadata (MIME types accepted) on
  `rows.utils` (should be refactored to be inside each plugin)
- Moved `slug` and `ipartition` functions to `rows.plugins.utils`
- Optimize `rows query` when using only one SQLite source


## Version `0.2.0`

**Released on: 2016-07-15**

### Backwards Incompatible Changes

- `rows.fields.UnicodeField` was renamed to `rows.fields.TextField`
- `rows.fields.BytesField` was renamed to `rows.fields.BinaryField`

### Bug Fixes

- Fix import errors on older versions of urllib3 and Python (thanks to
  [@jeanferri](https://github.com/jeanferri))
- [#156](https://github.com/turicas/rows/issues/156) `BoolField` should not
  accept "0" and "1" as possible values
- [#86](https://github.com/turicas/rows/issues/86) Fix `Content-Type` parsing
- Fix locale-related tests
- [#85](https://github.com/turicas/rows/issues/85) Fix `preserve_html` if
  `fields` is not provided
- Fix problem with big integers
- [#131](https://github.com/turicas/rows/issues/131) Fix problem when empty
  sample data
- Fix problem with `unicode` and `DateField`
- Fix `PercentField.serialize(None)`
- Fix bug with `Decimal` receiving `''`
- Fix bug in `PercentField.serialize(Decimal('0'))`
- Fix nested table behaviour on HTML plugin

### General Changes

- (EXPERIMENTAL) Add `rows.FlexibleTable` class (with help on tests from
  [@maurobaraildi](https://github.com/maurobaraldi))
- Lots of refactorings
- Add `rows.operations.transpose`
- Add `Table.__repr__`
- Renamte `rows.fields.UnicodeField` to `rows.fields.TextField` and
  `rows.fields.ByteField` to `rows.fields.BinaryField`
- Add a man page (thanks to [@kretcheu](https://github.com/kretcheu))
- [#40](https://github.com/turicas/rows/issues/40) The package is available on
  Debian!
- [#120](https://github.com/turicas/rows/issues/120) The package is available
  on Fedora!
- Add some examples
- [#138](https://github.com/turicas/rows/issues/138) Add
  `rows.fields.JSONField`
- [#146](https://github.com/turicas/rows/issues/146) Add
  `rows.fields.EmailField`
- Enhance encoding detection using
  [file-magic](https://pypi.python.org/pypi/file-magic) library
- [#160](https://github.com/turicas/rows/issues/160) Add
  support for column get/set/del in `rows.Table`

### Tests

- Fix "\r\n" on tests to work on Windows
- Enhance tests with `mock` to assure some functions are being called
- Improve some tests

### Plugins

- Add plugin JSON (thanks [@sxslex](https://github.com/sxslex))
- [#107](https://github.com/turicas/rows/issues/107) Add `import_from_txt`
- [#149](https://github.com/turicas/rows/issues/149) Add `import_from_xpath`
- (EXPERIMENTAL) Add `import_from_ods`
- (EXPERIMENTAL) Add `import_from_parquet`
- Add `import_from_sqlite` and `export_to_sqlite` (implemented by
  [@turicas](https://github.com/turicas) with help from
  [@infog](https://github.com/infog))
- Add `import_from_xlsx` and `export_to_xlsx` (thanks to
  [@RhenanBartels](https://github.com/turicas/RhenanBartels))
- Autodetect delimiter in CSV files
- Export to TXT, JSON and XLS also support an already opened file and CSV can
  export to memory (thanks to [@jeanferri](https://github.com/jeanferri))
- [#93](https://github.com/turicas/rows/issues/93) Add HTML helpers inside
  `rows.plugins.html`: `count_tables`, `extract_text`, `extract_links` and
  `tag_to_dict`
- [#162](https://github.com/turicas/rows/issues/162) Add `import_from_dicts`
  and `export_to_dicts`
- Refactor `export_to_txt`

### Utils

- Create `rows.plugins.utils`
- [#119](https://github.com/turicas/rows/issues/119) Rename field name if name
  is duplicated (to "field_2", "field_3", ..., "field_N") or if starts with a
  number.
- Add option to import only some fields (`import_fields` parameter inside
  `create_table`)
- Add option to export only some fields (`export_fields` parameter inside
  `prepare_to_export`)
- Add option `force_types` to force field types in some columns (instead of
  detecting) on `create_table`.
- Support lazy objects on `create_table`
- Add `samples` parameter to `create_table`

### CLI

- Add option to disable SSL verification (`--verify-ssl=no`)
- Add `print` command
- Add `--version`
- CLI is not installed by default (should be installed as
  `pip install rows[cli]`)
- Automatically detect default encoding (if not specified)
- Add `--order-by` to some commands and remove `sort` command. #111
- Do not use locale by default
- Add `query` command: converts (from many sources) internally to SQLite,
  execute the query and then export

## Version `0.1.1`

**Released on: 2015-09-03**

- Fix code to run on Windows (thanks [@sxslex](https://github.com/sxslex))
- Fix locale (name, default name etc.)
- Remove `filemagic` dependency (waiting for `python-magic` to be available on
  PyPI)
- Write log of changes for `0.1.0` and `0.1.1`


## Version `0.1.0`

**Released on: 2015-08-29**

- Implement `Table` and its basic methods
- Implement basic plugin support with many utilities and the following formats:
  - `csv` (input/output)
  - `html` (input/output)
  - `txt` (output)
  - `xls` (input/output)
- Implement the following field types - many of them with locale support:
  - `ByteField`
  - `BoolField`
  - `IntegerField`
  - `FloatField`
  - `DecimalField`
  - `PercentField`
  - `DateField`
  - `DatetimeField`
  - `UnicodeField`
- Implement basic `Table` operations:
  - `sum`
  - `join`
  - `transform`
  - `serialize`
- Implement a command-line interface with the following commands:
  - `convert`
  - `join`
  - `sort`
  - `sum`
- Add examples to the repository
