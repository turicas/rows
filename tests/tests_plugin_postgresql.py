# coding: utf-8

# Copyright 2014-2025 Álvaro Justen <https://github.com/turicas/rows/>
#    This program is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
#    Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
#    any later version.
#    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
#    warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for
#    more details.
#    You should have received a copy of the GNU Lesser General Public License along with this program.  If not, see
#    <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import os
import tempfile
import unittest
from textwrap import dedent

import mock
from psycopg2 import connect as pgconnect

import rows
import rows.plugins.utils
import tests.utils as utils
from rows import fields
from rows.utils import Source
from rows.compat import PYTHON_VERSION
from tests.utils import PSQL_FOUND

if PYTHON_VERSION < (3, 0, 0):
    from urlparse import urlparse, urlunparse
else:
    from urllib.parse import urlparse, urlunparse

ALIAS_IMPORT, ALIAS_EXPORT = rows.import_from_postgresql, rows.export_to_postgresql  # Lazy functions (just aliases)
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL is not None:
    parsed = urlparse(DATABASE_URL)
    TEST_DATABASE_NAME = "test_py" + "_".join(str(item) for item in PYTHON_VERSION)
    TEST_DATABASE_URL = urlunparse(
        (parsed.scheme, parsed.netloc, "/{}".format(TEST_DATABASE_NAME), parsed.params, parsed.query, parsed.fragment)
    )
else:
    TEST_DATABASE_URL = None
exported_utils_table = list(rows.plugins.utils.prepare_to_export(utils.table))

@unittest.skipIf(TEST_DATABASE_URL is None, "postgres service is not running")
@unittest.skipIf(not PSQL_FOUND, "command psql not installed")
class PluginPostgreSQLTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = "postgresql"
    override_fields = {
        "bool_column": fields.BoolField,
        "percent_column": fields.FloatField,
    }
    expected_meta = {
        "imported_from": "postgresql",
        "source": Source(uri=TEST_DATABASE_URL, plugin_name=plugin_name, encoding=None),
    }

    @classmethod
    def setUpClass(cls):
        """Create a new database for this Python version"""
        if DATABASE_URL is None:
            return
        connection = pgconnect(DATABASE_URL)
        connection.autocommit = True
        cursor = connection.cursor()
        cursor.execute("DROP DATABASE IF EXISTS {}".format(TEST_DATABASE_NAME))
        cursor.execute("CREATE DATABASE {}".format(TEST_DATABASE_NAME))
        cursor.close()

    @classmethod
    def tearDownClass(cls):
        """Delete the test database for this Python version"""

        if DATABASE_URL is None:
            return
        parsed = urlparse(DATABASE_URL)
        database_url_no_db = urlunparse(
            (parsed.scheme, parsed.netloc, "/", parsed.params, parsed.query, parsed.fragment)
        )
        connection = pgconnect(database_url_no_db)
        connection.autocommit = True
        cursor = connection.cursor()
        cursor.execute("DROP DATABASE IF EXISTS {}".format(TEST_DATABASE_NAME))
        cursor.close()

    def get_table_names(self):
        SQL_TABLE_NAMES = """
            SELECT
                tablename
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        """
        connection = pgconnect(TEST_DATABASE_URL)
        cursor = connection.cursor()
        cursor.execute(SQL_TABLE_NAMES)
        header = [item[0] for item in cursor.description]
        result = [dict(zip(header, row))["tablename"] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        return result

    def tearDown(self):
        connection = pgconnect(TEST_DATABASE_URL)
        for table in self.get_table_names():
            if table.startswith("rows_"):
                cursor = connection.cursor()
                cursor.execute("DROP TABLE " + table)
                cursor.close()
        connection.commit()
        connection.close()

    def test_imports(self):
        # Force the plugin to load
        original_import, original_export = rows.plugins.postgresql.import_from_postgresql, rows.plugins.postgresql.export_to_postgresql
        assert id(ALIAS_IMPORT) != id(original_import)
        assert id(ALIAS_EXPORT) != id(original_export)
        new_alias_import, new_alias_export = rows.import_from_postgresql, rows.export_to_postgresql
        assert id(new_alias_import) == id(original_import)  # Function replaced with loaded one
        assert id(new_alias_export) == id(original_export)  # Function replaced with loaded one

    @mock.patch("rows.plugins.utils.create_table")
    def test_import_from_postgresql_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {"encoding": "test", "some_key": 123, "other": 456}
        rows.export_to_postgresql(utils.table, TEST_DATABASE_URL, table_name="rows_1")
        result = rows.import_from_postgresql(TEST_DATABASE_URL, table_name="rows_1", **kwargs)
        assert mocked_create_table.called
        assert mocked_create_table.call_count == 1
        assert result == 42

        call = mocked_create_table.call_args
        meta = call[1].pop("meta")
        source = meta.pop("source")
        expected_meta = self.expected_meta.copy()
        expected_source = expected_meta.pop("source")

        assert call[1] == kwargs
        assert meta == expected_meta
        assert expected_source.uri == source.uri

    @unittest.skipIf(PYTHON_VERSION < (3, 0, 0), "psycopg2 on Python2 returns binary, skippging test")
    @mock.patch("rows.plugins.utils.create_table")
    def test_import_from_postgresql_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42
        connection, table_name = rows.export_to_postgresql(
            utils.table, TEST_DATABASE_URL, table_name="rows_2"
        )
        assert connection.closed

        # import using uri
        table_1 = rows.import_from_postgresql(
            TEST_DATABASE_URL, close_connection=True, table_name="rows_2"
        )
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args, expected_meta=self.expected_meta)

        # import using connection
        connection = pgconnect(TEST_DATABASE_URL)
        table_2 = rows.import_from_postgresql(
            connection, close_connection=False, table_name="rows_2"
        )
        self.assertFalse(connection.closed)
        connection_type = type(connection)
        connection.close()

        call_args = mocked_create_table.call_args_list[1]
        meta = call_args[1].pop("meta")
        call_args[1]["meta"] = {}
        self.assert_create_table_data(call_args, expected_meta={})
        assert isinstance(meta["source"].fobj, connection_type)

    def test_postgresql_injection(self):
        with self.assertRaises(ValueError):
            rows.import_from_postgresql(
                TEST_DATABASE_URL, table_name=('table1","postgresql_master')
            )

        with self.assertRaises(ValueError):
            rows.export_to_postgresql(
                utils.table, TEST_DATABASE_URL, table_name='table1", "postgresql_master'
            )

    @unittest.skipIf(PYTHON_VERSION < (3, 0, 0), "psycopg2 on Python2 returns binary, skippging test")
    def test_export_to_postgresql_uri(self):
        rows.export_to_postgresql(utils.table, TEST_DATABASE_URL, table_name="rows_3")

        table = rows.import_from_postgresql(TEST_DATABASE_URL, table_name="rows_3")
        self.assert_table_equal(table, utils.table)

    @unittest.skipIf(PYTHON_VERSION < (3, 0, 0), "psycopg2 on Python2 returns binary, skippging test")
    def test_export_to_postgresql_connection(self):
        connection = pgconnect(TEST_DATABASE_URL)
        rows.export_to_postgresql(
            utils.table, connection, close_connection=True, table_name="rows_4"
        )

        table = rows.import_from_postgresql(TEST_DATABASE_URL, table_name="rows_4")
        self.assert_table_equal(table, utils.table)
        connection.close()

    @unittest.skipIf(PYTHON_VERSION < (3, 0, 0), "psycopg2 on Python2 returns binary, skippging test")
    def test_export_to_postgresql_create_unique_table_name(self):
        first_table = utils.table
        second_table = utils.table + utils.table

        table_names_before = self.get_table_names()
        rows.export_to_postgresql(
            first_table, TEST_DATABASE_URL, table_name_format="rows_{index}"
        )
        table_names_after = self.get_table_names()
        rows.export_to_postgresql(
            second_table, TEST_DATABASE_URL, table_name_format="rows_{index}"
        )
        table_names_final = self.get_table_names()

        diff_1 = list(set(table_names_after) - set(table_names_before))
        diff_2 = list(set(table_names_final) - set(table_names_after))
        assert len(diff_1) == 1
        assert len(diff_2) == 1
        new_table_1 = diff_1[0]
        new_table_2 = diff_2[0]

        result_first_table = rows.import_from_postgresql(
            TEST_DATABASE_URL, table_name=new_table_1
        )
        result_second_table = rows.import_from_postgresql(
            TEST_DATABASE_URL, table_name=new_table_2
        )
        self.assert_table_equal(result_first_table, first_table)
        self.assert_table_equal(result_second_table, second_table)

    @unittest.skipIf(PYTHON_VERSION < (3, 0, 0), "psycopg2 on Python2 returns binary, skippging test")
    def test_export_to_postgresql_forcing_table_name_appends_rows(self):
        repeat = 3
        for _ in range(repeat):
            rows.export_to_postgresql(utils.table, TEST_DATABASE_URL, table_name="rows_7")
        expected_table = utils.table
        for _ in range(repeat - 1):
            expected_table += utils.table

        result_table = rows.import_from_postgresql(TEST_DATABASE_URL, table_name="rows_7")

        assert len(result_table) == repeat * len(utils.table)
        self.assert_table_equal(result_table, expected_table)

    @mock.patch("rows.plugins.utils.prepare_to_export")
    def test_export_to_postgresql_prepare_to_export(self, mocked_prepare_to_export):
        encoding = "iso-8859-15"
        kwargs = {"test": 123, "parameter": 3.14}
        mocked_prepare_to_export.return_value = iter(exported_utils_table)
        rows.export_to_postgresql(
            utils.table, TEST_DATABASE_URL, encoding=encoding, table_name="rows_8", **kwargs
        )
        assert mocked_prepare_to_export.called
        assert mocked_prepare_to_export.call_count == 1
        call = mocked_prepare_to_export.call_args
        assert call[0] == (utils.table,)
        kwargs["encoding"] = encoding
        assert call[1] == kwargs

    def test_import_from_postgresql_query_args(self):
        connection, table_name = rows.export_to_postgresql(
            utils.table, TEST_DATABASE_URL, close_connection=False, table_name="rows_9"
        )
        table = rows.import_from_postgresql(
            connection,
            query="SELECT * FROM rows_9 WHERE float_column > %s",
            query_args=(3,),
        )
        for row in table:
            assert row.float_column > 3
        connection.close()

    def test_pgimport_force_null(self):
        temp = tempfile.NamedTemporaryFile()
        filename = "{}.csv".format(temp.name)
        temp.close()
        self.files_to_delete.append(filename)
        with open(filename, mode="wb") as fobj:
            fobj.write(
                dedent(
                    """
                field1,field2
                "","4"
                ,2
                """
                )
                .strip()
                .encode("utf-8")
            )
        rows.utils.pgimport(
            filename=filename,
            database_uri=TEST_DATABASE_URL,
            table_name="rows_force_null",
        )
        table = rows.import_from_postgresql(TEST_DATABASE_URL, "rows_force_null")
        assert table[0].field1 is None
        assert table[0].field2 == 4
        assert table[1].field1 is None
        assert table[1].field2 == 2
