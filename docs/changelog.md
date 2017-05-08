# rows' Log of Changes

## Version `0.3.2`

**Released on: (under development)**


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
- Add `print` subcommand
- Add `--version`
- CLI is not installed by default (should be installed as
  `pip install rows[cli]`)
- Automatically detect default encoding (if not specified)
- Add `--order-by` to some subcommands and remove `sort` subcommand. #111
- Do not use locale by default
- Add `query` subcommand: converts (from many sources) internally to SQLite,
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
- Implement a command-line interface with the following subcommands:
  - `convert`
  - `join`
  - `sort`
  - `sum`
- Add examples to the repository
