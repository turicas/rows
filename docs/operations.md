# `Table` operations

The module `rows.operations` contains some operations you can do on your
`Table` objects:

- `rows.operations.join`: return a new `Table` based on the joining of a list
  of `Table`s and a field to act as `key` between them. Note: for performance
  reasons you may not use this function, since the join operation is done in
  Python - you can also convert everything to SQLite, query data there and then
  have your results in a `Table`, like the [`rows query`][rows-cli-query]
  command.
- `rows.operations.transform`: return a new `Table` based on other tables and a
  transformation function.
- `rows.operations.transpose`: transpose the `Table` based on a specific field.


[rows-cli-query]: https://github.com/turicas/rows/blob/develop/rows/cli.py#L291
