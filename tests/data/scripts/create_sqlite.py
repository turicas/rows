# coding: utf-8

import os
import sqlite3
from collections import OrderedDict

input_filename = "../all-field-types.csv"
output_filename = "../all-field-types.sqlite"


field_types = OrderedDict(
    [
        ("bool_column", "INTEGER"),
        ("integer_column", "INTEGER"),
        ("float_column", "FLOAT"),
        ("decimal_column", "FLOAT"),
        ("percent_column", "TEXT"),
        ("date_column", "TEXT"),
        ("datetime_column", "TEXT"),
        ("unicode_column", "TEXT"),
    ]
)
column_types = ", ".join(
    ["{} {}".format(key, value) for key, value in field_types.items()]
)
create_sql = "CREATE TABLE table1 ({})".format(column_types)
field_names = ", ".join(field_types.keys())
placeholders = ", ".join(["?" for _ in field_types])
insert_sql = "INSERT INTO table1 ({}) VALUES ({})".format(field_names, placeholders)

if os.path.exists(output_filename):
    os.unlink(output_filename)

connection = sqlite3.connect(output_filename)
connection.execute(create_sql)
with open(input_filename) as fobj:
    data = fobj.read().decode("utf-8").splitlines()
for row in data[1:]:
    connection.execute(insert_sql, row.split(","))
connection.commit()
