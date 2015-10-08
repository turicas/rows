# rows' Log of Changes

## Version `0.2.0` (under development)

**Released on: (under development)**

- Add `FlexibleTable` class
- Export to XLS also support an already opened file
- Enhance README
- Refactor `export_to_txt`
- Support lazy objects on `create_table`
- Add `samples` parameter to `create_table`
- Add plugin JSON (thanks [@sxslex](https://github.com/sxslex))
- Add `Table.__repr__`


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
