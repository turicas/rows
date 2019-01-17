# Plugins

The idea behing plugins is very simple: you write a little piece of code which
extracts data from/to some specific format and the library will do the other
tasks for you, such as detecting and converting data types. So writing a plugin
is as easy as reading from/writing to the file format you want. Currently we
have the following plugins:

- CSV: use `rows.import_from_csv` and `rows.export_to_csv` (dependencies are
  installed by default)
- TXT: use `rows.export_to_txt` (no dependencies)
- JSON: use `rows.import_from_json` and `rows.export_to_json` (no dependencies)
- HTML: use `rows.import_from_html` and `rows.export_to_html` (dependencies
  must be installed with `pip install rows[html]`)
- XPath: use `rows.import_from_xpath` passing the following arguments:
  `filename_or_fobj`, `rows_xpath` and `fields_xpath` (dependencies must be
  installed with `pip install rows[xpath]`) -- see an example in
  `examples/library/ecuador_radiodifusoras.py`.
- Parquet: use `rows.import_from_parquet` passing the filename (dependencies
  must be installed with `pip install rows[parquet]` and if the data is
  compressed using snappy you also need to install `rows[parquet-snappy]` and
  the `libsnappy-dev` system library) -- read [this blog post][blog-rows-parquet]
  for more details and one example
- XLS: use `rows.import_from_xls` and `rows.export_to_xls` (dependencies must
  be installed with `pip install rows[xls]`)
- XLSX: use `rows.import_from_xlsx` and `rows.export_to_xlsx` (dependencies
  must be installed with `pip install rows[xlsx]`)
- SQLite: use `rows.import_from_sqlite` and `rows.export_to_sqlite` (no
  dependencies)
- ODS: use `rows.import_from_ods` (dependencies must be installed with `pip
  install rows[ods]`)

More plugins are coming and we're going to re-design the plugin interface so
you can create and distribute your own in a better way. Feel free [to
contribute][doc-contributing]. :-)


[doc-contributing]: contributing.md
