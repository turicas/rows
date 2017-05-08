# Command-Line Interface

`rows` exposes a command-line interface with common operations such as
converting and querying data.


> Note: we still need to improve this documentation. Please run `rows --help`
> to see all the available commands and take a look at [rows/cli.py][rows-cli].


## `rows convert`

You can convert from/to any of the supported formats -- just pass the correct
filenames and the CLI will automatically identify file type and encoding:

```bash
rows convert data/brazilian-cities.csv data/brazilian-cities.xlsx
```


## `rows query`

Yep, you can SQL-query any supported file format! Each of the source files will
be a table inside an in-memory SQLite database, called `table1`, ..., `tableN`.
If the `--output` is not specified, `rows` will print a table on the standard
output.


```bash
rows query 'SELECT * FROM table1 WHERE inhabitants > 1000000' \
     data/brazilian-cities.csv \
     --output=data/result.html
```


[rows-cli]: https://github.com/turicas/rows/blob/develop/rows/cli.py
