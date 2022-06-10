# coding: utf-8

# Copyright 2014-2022 Álvaro Justen <https://github.com/turicas/rows/>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import datetime

import MySQLdb

from .rows import Table
from .utils import ipartition, slug

__all__ = ["import_from_mysql", "export_to_mysql"]

# TODO: replace 'None' with '' on export_to_*
# TODO: need converters in and out
# TODO: lazy=True|False
# TODO: datetime.time on MYSQL_TYPE
# TODO: import from mysql
# TODO: logging?
# TODO: _mysql_exceptions.OperationalError: (2006, 'MySQL server has gone #
# away')

MYSQL_TYPE = {
    str: "TEXT",
    int: "INT",
    float: "FLOAT",
    datetime.date: "DATE",
    datetime.datetime: "DATETIME",
    bool: "BOOL",
}
# 'BOOL' on MySQL is a shortcut to TINYINT(1)
MYSQLDB_TYPE = {
    getattr(MySQLdb.FIELD_TYPE, x): x
    for x in dir(MySQLdb.FIELD_TYPE)
    if not x.startswith("_")
}
MYSQLDB_TO_PYTHON = {
    "ENUM": str,
    "STRING": str,
    "VAR_STRING": str,
    "BLOB": bytes,
    "LONG_BLOB": bytes,
    "MEDIUM_BLOB": bytes,
    "TINY_BLOB": bytes,
    "DECIMAL": float,
    "DOUBLE": float,
    "FLOAT": float,
    "INT24": int,
    "LONG": int,
    "LONGLONG": int,
    "TINY": int,
    "YEAR": int,
    "DATE": datetime.date,
    "NEWDATE": datetime.date,
    "TIME": int,
    "TIMESTAMP": int,
    "DATETIME": datetime.datetime,
}


def _get_mysql_config(connection_str):
    colon_index = connection_str.index(":")
    at_index = connection_str.index("@")
    slash_index = connection_str.index("/")
    config = {}
    config["user"] = connection_str[:colon_index]
    config["passwd"] = connection_str[colon_index + 1 : at_index]
    config["host"] = connection_str[at_index + 1 : slash_index]
    config["port"] = 3306
    if ":" in config["host"]:
        data = config["host"].split(":")
        config["host"] = data[0]
        config["port"] = int(data[1])
    if connection_str.count("/") == 1:
        table_name = None
        config["db"] = connection_str[slash_index + 1 :]
    else:
        second_slash_index = connection_str.index("/", slash_index + 1)
        config["db"] = connection_str[slash_index + 1 : second_slash_index]
        table_name = connection_str[second_slash_index + 1 :]
    return config, table_name


def _connect_to_mysql(config):
    return MySQLdb.connect(**config)


def import_from_mysql(connection_string, limit=None, order_by=None, query=""):
    # TODO: add 'lazy' option
    config, table_name = _get_mysql_config(connection_string)
    connection = _connect_to_mysql(config)
    cursor = connection.cursor()
    if query:
        sql = query
    else:
        sql = "SELECT * FROM " + table_name
        if limit is not None:
            sql += " LIMIT {0[0]}, {0[1]}".format(limit)
        if order_by is not None:
            sql += " ORDER BY " + order_by
    cursor.execute(sql)
    column_info = [(x[0], x[1]) for x in cursor.description]
    table = Table(fields=[x[0] for x in cursor.description])
    table.types = {
        name: MYSQLDB_TO_PYTHON[MYSQLDB_TYPE[type_]] for name, type_ in column_info
    }
    table_rows = [list(row) for row in cursor.fetchall()]

    encoding = connection.character_set_name()
    for row in table_rows:
        for column_index, value in enumerate(row):
            if type(value) is str:
                row[column_index] = value.decode(encoding)
    table._rows = table_rows
    cursor.close()
    connection.close()
    return table


def export_to_mysql(
    table,
    connection_string,
    encoding=None,
    batch_size=1000,
    commit_every=10000,
    callback=None,
    callback_every=10000,
):
    config, table_name = _get_mysql_config(connection_string)
    connection = _connect_to_mysql(config)
    cursor = connection.cursor()

    # Create table
    fields, types = table.fields, table.types
    field_slugs = [slug(field) for field in fields]
    field_types = [MYSQL_TYPE[types[field]] for field in fields]
    columns_definition = [
        "{} {}".format(field, type_) for field, type_ in zip(field_slugs, field_types)
    ]
    sql = "CREATE TABLE IF NOT EXISTS {} ({})".format(
        table_name, ", ".join(columns_definition)
    )
    cursor.execute(sql)

    # Insert items
    columns = ", ".join(field_slugs)
    # placeholders = ['%s' if types[field] in (int, float, bool) else '"%s"'
    #                for field in fields]
    # TODO: fix this string/formatting problem
    placeholders = ["%s" for field in fields]
    sql = "INSERT INTO {} ({}) VALUES ({})".format(
        table_name, columns, ", ".join(placeholders)
    )

    total = last_commit = last_callback = 0
    for rows in ipartition(iter(table), batch_size):
        values = [[row[field] for field in fields] for row in rows]

        added = len(values)
        total += added
        last_commit += added
        last_callback += added

        cursor.executemany(sql, values)

        if last_commit >= commit_every:
            connection.commit()
            last_commit = 0
        if callback is not None and last_callback >= callback_every:
            callback(total)
            last_callback = 0

    if callback is not None and last_callback > 0:
        callback(total)
    if last_commit > 0:
        connection.commit()
    connection.close()
