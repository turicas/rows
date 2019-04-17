# coding: utf-8

# Copyright 2014-2018 Álvaro Justen <https://github.com/turicas/rows/>

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

from __future__ import unicode_literals

import os
import unittest

import mock
import six

import rows
import rows.plugins.postgresql
import rows.plugins.utils
import tests.utils as utils
from rows import fields
from rows.plugins.postgresql import pgconnect


class PluginPostgreSQLTestCase(utils.RowsTestMixIn, unittest.TestCase):

    plugin_name = "postgresql"
    override_fields = {
        "bool_column": fields.BoolField,
        "percent_column": fields.FloatField,
    }

    @classmethod
    def setUpClass(cls):
        cls.uri = os.environ["POSTGRESQL_URI"]
        cls.meta = {"imported_from": "postgresql", "filename": cls.uri}

    def get_table_names(self):
        connection = pgconnect(self.uri)
        cursor = connection.cursor()
        cursor.execute(rows.plugins.postgresql.SQL_TABLE_NAMES)
        header = [item[0] for item in cursor.description]
        result = [dict(zip(header, row))["tablename"] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        return result

    def tearDown(self):
        connection = pgconnect(self.uri)
        for table in self.get_table_names():
            if table.startswith("rows_"):
                cursor = connection.cursor()
                cursor.execute("DROP TABLE " + table)
                cursor.close()
        connection.commit()
        connection.close()

    def test_imports(self):
        self.assertIs(
            rows.import_from_postgresql, rows.plugins.postgresql.import_from_postgresql
        )
        self.assertIs(
            rows.export_to_postgresql, rows.plugins.postgresql.export_to_postgresql
        )

    @mock.patch("rows.plugins.postgresql.create_table")
    def test_import_from_postgresql_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {"encoding": "test", "some_key": 123, "other": 456}
        rows.export_to_postgresql(utils.table, self.uri, table_name="rows_1")
        result = rows.import_from_postgresql(self.uri, table_name="rows_1", **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        meta = call[1].pop("meta")
        source = meta.pop("source")

        self.assertEqual(call[1], kwargs)
        self.assertEqual(meta, self.meta)
        self.assertEqual(self.uri, source.uri)

    @unittest.skipIf(six.PY2, "psycopg2 on Python2 returns binary, skippging test")
    @mock.patch("rows.plugins.postgresql.create_table")
    def test_import_from_postgresql_retrieve_desired_data(self, mocked_create_table):
        mocked_create_table.return_value = 42
        connection, table_name = rows.export_to_postgresql(
            utils.table, self.uri, table_name="rows_2"
        )
        self.assertTrue(connection.closed)

        # import using uri
        table_1 = rows.import_from_postgresql(
            self.uri, close_connection=True, table_name="rows_2"
        )
        call_args = mocked_create_table.call_args_list[0]
        self.assert_create_table_data(call_args, expected_meta=self.meta)

        # import using connection
        connection = pgconnect(self.uri)
        table_2 = rows.import_from_postgresql(
            connection, close_connection=False, table_name="rows_2"
        )
        self.assertFalse(connection.closed)
        call_args = mocked_create_table.call_args_list[1]
        meta = self.meta.copy()
        meta["filename"] = None  # None is set to `source.uri` when a connection is provided
        self.assert_create_table_data(call_args, expected_meta=meta)
        connection.close()

    def test_postgresql_injection(self):
        with self.assertRaises(ValueError):
            rows.import_from_postgresql(
                self.uri, table_name=('table1","postgresql_master')
            )

        with self.assertRaises(ValueError):
            rows.export_to_postgresql(
                utils.table, self.uri, table_name='table1", "postgresql_master'
            )

    @unittest.skipIf(six.PY2, "psycopg2 on Python2 returns binary, skippging test")
    def test_export_to_postgresql_uri(self):
        rows.export_to_postgresql(utils.table, self.uri, table_name="rows_3")

        table = rows.import_from_postgresql(self.uri, table_name="rows_3")
        self.assert_table_equal(table, utils.table)

    @unittest.skipIf(six.PY2, "psycopg2 on Python2 returns binary, skippging test")
    def test_export_to_postgresql_connection(self):
        connection = pgconnect(self.uri)
        rows.export_to_postgresql(
            utils.table, connection, close_connection=True, table_name="rows_4"
        )

        table = rows.import_from_postgresql(self.uri, table_name="rows_4")
        self.assert_table_equal(table, utils.table)

    @unittest.skipIf(six.PY2, "psycopg2 on Python2 returns binary, skippging test")
    def test_export_to_postgresql_create_unique_table_name(self):
        first_table = utils.table
        second_table = utils.table + utils.table

        table_names_before = self.get_table_names()
        rows.export_to_postgresql(
            first_table, self.uri, table_name_format="rows_{index}"
        )
        table_names_after = self.get_table_names()
        rows.export_to_postgresql(
            second_table, self.uri, table_name_format="rows_{index}"
        )
        table_names_final = self.get_table_names()

        diff_1 = list(set(table_names_after) - set(table_names_before))
        diff_2 = list(set(table_names_final) - set(table_names_after))
        self.assertEqual(len(diff_1), 1)
        self.assertEqual(len(diff_2), 1)
        new_table_1 = diff_1[0]
        new_table_2 = diff_2[0]

        result_first_table = rows.import_from_postgresql(
            self.uri, table_name=new_table_1
        )
        result_second_table = rows.import_from_postgresql(
            self.uri, table_name=new_table_2
        )
        self.assert_table_equal(result_first_table, first_table)
        self.assert_table_equal(result_second_table, second_table)

    @unittest.skipIf(six.PY2, "psycopg2 on Python2 returns binary, skippging test")
    def test_export_to_postgresql_forcing_table_name_appends_rows(self):
        repeat = 3
        for _ in range(repeat):
            rows.export_to_postgresql(utils.table, self.uri, table_name="rows_7")
        expected_table = utils.table
        for _ in range(repeat - 1):
            expected_table += utils.table

        result_table = rows.import_from_postgresql(self.uri, table_name="rows_7")

        self.assertEqual(len(result_table), repeat * len(utils.table))
        self.assert_table_equal(result_table, expected_table)

    @mock.patch("rows.plugins.postgresql.prepare_to_export")
    def test_export_to_postgresql_prepare_to_export(self, mocked_prepare_to_export):
        encoding = "iso-8859-15"
        kwargs = {"test": 123, "parameter": 3.14}
        mocked_prepare_to_export.return_value = iter(
            rows.plugins.utils.prepare_to_export(utils.table)
        )

        rows.export_to_postgresql(
            utils.table, self.uri, encoding=encoding, table_name="rows_8", **kwargs
        )
        self.assertTrue(mocked_prepare_to_export.called)
        self.assertEqual(mocked_prepare_to_export.call_count, 1)

        call = mocked_prepare_to_export.call_args
        self.assertEqual(call[0], (utils.table,))
        kwargs["encoding"] = encoding
        self.assertEqual(call[1], kwargs)

    def test_import_from_postgresql_query_args(self):
        connection, table_name = rows.export_to_postgresql(
            utils.table, self.uri, close_connection=False, table_name="rows_9"
        )
        table = rows.import_from_postgresql(
            connection,
            query="SELECT * FROM rows_9 WHERE float_column > %s",
            query_args=(3,),
        )
        for row in table:
            self.assertTrue(row.float_column > 3)
