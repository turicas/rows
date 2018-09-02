# Command-Line Interface

`rows` exposes a command-line interface with common operations such as
converting and querying data.


> Note: we still need to improve this documentation. Please run `rows --help`
> to see all the available commands and take a look at [rows/cli.py][rows-cli].

## Global parameters

The table below lists the available arguments.

<table>
	<thead>
	<tr>
		<th>Description</th>
		<th>Argument</span></th>
	</tr>
	</thead>
     <tbody>
          <tr>
               <td>
                    Input Encoding.
                    <br />
                    Default value: <code>'utf-8'</code>
               </td>
               <td>
                    <code class="flag">--input-encoding=&lt;encoding&gt;</code>
               </td>
          </tr>
          <tr>
               <td>
                    Output Encoding.
                    <br />
                    Default value: <code>'utf-8'</code>
               </td>
               <td>
                    <code class="flag">--output-encoding=&lt;encoding&gt;</code>
               </td>
          </tr>
          <tr>
               <td>
                    Locale of the input data. For more information, refer to Locales document.
                    <br />
                    Default value: <code>C</code>
               </td>
               <td>
                    <code class="flag">--input-locale=&lt;locale&gt;</code>
               </td>
          </tr>
          <tr>
               <td>
                    Locale of the output data. For more information, refer to Locales document.
                    <br />
                    Default value: <code>C</code>
               </td>
               <td>
                    <code class="flag">--output-locale=&lt;locale&gt;</code>
               </td>
          </tr>
          <tr>
               <td>
                    SSL verification.
                    <br />
                    Default value: <code>True</code>
               </td>
               <td>
                    <code class="flag">--verify-ssl=&lt;bool&gt;</code>
               </td>
          </tr>
          <tr>
               <td>
		    The field(s) sorting key.
                    <br />
                    Default value: <code>None</code>
               </td>
               <td>
                    <code class="flag">--order-by=&lt;field&gt;</code>
               </td>
          </tr>
          <tr>
               <td>
                    A comma-separated list of fields to import
                    <br />
                    Default value: <code>None</code>
               </td>
               <td>
                    <code class="flag">--fields=&lt;fields&gt;</code>
               </td>
          </tr>
          <tr>
               <td>
                    A comma-separated list of fields to exclude
                    <br />
                    Default value: <code>None</code>
               </td>
               <td>
                    <code class="flag">--fields-exclude=&lt;fields&gt;</code>
               </td>
          </tr>
      </tbody>
</table>

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

## `rows join`

Join tables from `source` URIs using `key(s)` to group rows and save into `destination`

For example, to join `a.csv` and `b.csv` to a new file called `c.csv` using the field `id` as a key, we can use:

```bash
rows join id a.csv b.csv c.csv
```

## `rows print`

Print the selected `source` table

```bash
rows print brazilian-cities.csv
```

If you're using an HTML file with more than one table, you can use the `--table-index` to say which table you want to print (the default value is `0`):

```bash
rows print a.html --table-index=1
```

## `rows schema`

Identifies the table schema.

The input

```bash
rows schema brazilian-cities.csv
```

returns

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

## `rows sum`

Sum tables from `source` URIs and save into `destination`.
Note: You need to have the same fields on the source files.

```bash
rows sum source1.csv source2.csv destination.csv
```

The `c.csv` will have the same headers that `a` and `b` have, with the contents of `a` and `b` files.

[rows-cli]: https://github.com/turicas/rows/blob/develop/rows/cli.py
