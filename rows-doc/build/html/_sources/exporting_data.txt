Exporting Data
==============

If you have a `Table` object you can export it to all available plugins which
have the "export" feature. Let's use the HTML plugin:

::

    rows.export_to_html(legislators, 'legislators.html')

And you'll get:

::

    $ head legislators.html
    <table>

      <thead>
        <tr>
          <th> title </th>
          <th> firstname </th>
          <th> middlename </th>
          <th> lastname </th>
          <th> name_suffix </th>
          <th> nickname </th>

See the `examples folder <https://github.com/turicas/rows/tree/develop/examples>`_ guide. for more examples.