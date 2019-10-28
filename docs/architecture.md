## Architecture

The library is composed by:

- A common interface to tabular data (the `Table` class)
- A set of plugins to populate `Table` objects from formats like CSV, XLS,
  XLSX, HTML and XPath, Parquet, PDF, TXT, JSON, SQLite;
- A set of common fields (such as `BoolField`, `IntegerField`) which know
  exactly how to serialize and deserialize data for each object type you'll get
- A set of utilities (such as field type recognition) to help working with
  tabular data
- A command-line interface so you can have easy access to the most used
  features: convert between formats, sum, join and sort tables.
