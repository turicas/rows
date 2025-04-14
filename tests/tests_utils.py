# coding: utf-8

# Copyright 2014-2019 Álvaro Justen <https://github.com/turicas/rows/>

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

import bz2
import gzip
try:
    import lzma  # Requires Python >= 3.3
except ImportError:
    lzma = None
import pathlib
import tempfile
import unittest
from collections import OrderedDict
from textwrap import dedent

import rows.fields as fields
import rows.utils
import tests.utils as utils


class UtilsTestCase(utils.RowsTestMixIn, unittest.TestCase):
    def assert_encoding(self, first, second):
        """Assert encoding equality

        `iso-8859-1` should be detected as the same as `iso-8859-8`
        as described in <https://github.com/turicas/rows/issues/194>
        (affects Debian and Fedora packaging)
        """

        encoding_1 = first.lower().split("-")[:-1]
        encoding_2 = second.lower().split("-")[:-1]
        if encoding_1 == ["windows"]:
            encoding_1 = ["iso", "8859"]
        if encoding_2 == ["windows"]:
            encoding_2 = ["iso", "8859"]
        assert encoding_1 == encoding_2

    def test_local_file_sample_size(self):

        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)

        header = b"field1,field2,field3\r\n"
        row_data = b"non-ascii-field-1,non-ascii-field-2,non-ascii-field-3\r\n"
        encoding = "iso-8859-1"
        temp.file.write(header)
        counter = len(header)
        increment = len(row_data)
        while counter <= 8192:
            temp.file.write(row_data)
            counter += increment
        temp.file.write("Álvaro,àáááããçc,ádfáffad\r\n".encode(encoding))
        temp.file.close()

        result = rows.utils.local_file(temp.name)
        assert result.uri == temp.name
        self.assert_encoding(result.encoding, encoding)
        assert result.should_delete == False


class SchemaTestCase(utils.RowsTestMixIn, unittest.TestCase):

    def _create_table(self, export_fields=None):
        """Prepare a consistent table so we can test all formats using it"""
        table_fields = utils.table.fields.copy()
        table_fields["json_column"] = fields.JSONField
        table_fields["decimal_column"] = fields.DecimalField
        table_fields["percent_column"] = fields.DecimalField
        if export_fields is None:
            export_fields = list(table_fields.keys())
        table = rows.Table(fields=table_fields)

        for row in utils.table:
            data = row._asdict()
            data["json_column"] = {}
            table.append(data)
        table.meta["name"] = "this is my table"  # TODO: may set source
        return table

    def assert_generate_schema(self, fmt, expected, export_fields=None, max_choices=0):
        table = self._create_table(export_fields=export_fields)
        if export_fields is None:
            export_fields = list(table.fields.keys())
        result = rows.utils.generate_schema(
            table=table, export_fields=export_fields, output_format=fmt, max_choices=max_choices
        )
        assert expected.strip() == result.strip()

    def test_generate_schema_txt(self):
        expected = dedent(
            """
            +-----------------+------------+-------+-------+--------+----------+----------------+------------+------------+---------+
            |    field_name   | field_type |  null |  min  |  max   | subtype  | decimal_places | max_digits | max_length | choices |
            +-----------------+------------+-------+-------+--------+----------+----------------+------------+------------+---------+
            |     bool_column |       bool |  true |       |        |          |                |            |            |         |
            |  integer_column |    integer |  true |   1.0 |    6.0 | SMALLINT |                |            |            |         |
            |    float_column |      float |  true | 1.234 |   9.87 |          |                |            |            |         |
            |  decimal_column |    decimal |  true | 1.234 |   9.87 |          |              6 |         10 |            |         |
            |  percent_column |    decimal |  true |  0.01 | 0.1364 |          |              4 |          8 |            |         |
            |     date_column |       date |  true |       |        |          |                |            |            |         |
            | datetime_column |   datetime |  true |       |        |          |                |            |            |         |
            |  unicode_column |       text |  true |       |        |  VARCHAR |                |            |          8 |         |
            |     json_column |       json | false |       |        |          |                |            |            |         |
            +-----------------+------------+-------+-------+--------+----------+----------------+------------+------------+---------+
        """
        )
        self.assert_generate_schema("txt", expected)

    def test_generate_schema_txt_choices(self):
        table = self._create_table()
        export_fields = list(table.fields.keys())
        result = rows.utils.generate_schema(table=table, export_fields=export_fields, output_format="txt", max_choices=10)
        lines = result.strip().splitlines()
        assert 'choices' in lines[1]
        selected_line = None
        for line in lines:
            if ' unicode_column |' in line:
                selected_line = line
                break
        assert selected_line is not None
        assert '["test", "~~~~", ' in selected_line

    def test_generate_schema_sql(self):
        expected = dedent(
            """
        CREATE TABLE IF NOT EXISTS "this_is_my_table" (
            "bool_column" BOOL,
            "integer_column" SMALLINT,
            "float_column" FLOAT,
            "decimal_column" DECIMAL(10, 6),
            "percent_column" DECIMAL(8, 4),
            "date_column" DATE,
            "datetime_column" TIMESTAMP,
            "unicode_column" VARCHAR(8),
            "json_column" TEXT NOT NULL
        );
        """
        )
        self.assert_generate_schema("sql", expected, max_choices=0)

    def test_generate_schema_sql_choices(self):
        expected = dedent(
            """
        CREATE TYPE "enum_unicode_column" AS ENUM (
          'test',
          '~~~~',
          'Álvaro',
          'àáãâä¹²³',
          'álvaro',
          'éèẽêë'
        );

        CREATE TABLE IF NOT EXISTS "this_is_my_table" (
            "bool_column" BOOL,
            "integer_column" SMALLINT,
            "float_column" FLOAT,
            "decimal_column" DECIMAL(10, 6),
            "percent_column" DECIMAL(8, 4),
            "date_column" DATE,
            "datetime_column" TIMESTAMP,
            "unicode_column" enum_unicode_column,
            "json_column" TEXT NOT NULL
        );
        """
        )
        self.assert_generate_schema("sql", expected, max_choices=10)

    def test_generate_schema_django(self):
        expected = dedent(
            """
        from django.db import models


        class ThisIsMyTable(models.Model):
            bool_column = models.BooleanField(null=True, blank=True)
            integer_column = models.PositiveSmallIntegerField(null=True, blank=True)  # max value=6, min value=1
            float_column = models.FloatField(null=True, blank=True)  # max value=9.87, min value=1.234
            decimal_column = models.DecimalField(null=True, blank=True, decimal_places=6, max_digits=10)  # max value=9.87, min value=1.234
            percent_column = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=8)  # max value=0.1364, min value=0.01
            date_column = models.DateField(null=True, blank=True)
            datetime_column = models.DateTimeField(null=True, blank=True)
            unicode_column = models.CharField(null=True, blank=True, max_length=8)
            json_column = models.JSONField(null=False, blank=False)
        """
        )
        self.assert_generate_schema("django", expected)

    def test_generate_schema_django_choices(self):
        expected = dedent(
            """
        from django.db import models


        class ThisIsMyTable(models.Model):
            UNICODE_COLUMN_CHOICES = (
                (0, 'test'),
                (1, '~~~~'),
                (2, 'Álvaro'),
                (3, 'àáãâä¹²³'),
                (4, 'álvaro'),
                (5, 'éèẽêë'),
            )

            bool_column = models.BooleanField(null=True, blank=True)
            integer_column = models.PositiveSmallIntegerField(null=True, blank=True)  # max value=6, min value=1
            float_column = models.FloatField(null=True, blank=True)  # max value=9.87, min value=1.234
            decimal_column = models.DecimalField(null=True, blank=True, decimal_places=6, max_digits=10)  # max value=9.87, min value=1.234
            percent_column = models.DecimalField(null=True, blank=True, decimal_places=4, max_digits=8)  # max value=0.1364, min value=0.01
            date_column = models.DateField(null=True, blank=True)
            datetime_column = models.DateTimeField(null=True, blank=True)
            unicode_column = models.SmallIntegerField(null=True, blank=True, choices=UNICODE_COLUMN_CHOICES)
            json_column = models.JSONField(null=False, blank=False)
        """
        )
        self.assert_generate_schema("django", expected, max_choices=10)

    def test_generate_schema_restricted_fields(self):
        expected = dedent(
            """
            +-------------+------------+-------+-----+-----+---------+----------------+------------+------------+---------+
            |  field_name | field_type |  null | min | max | subtype | decimal_places | max_digits | max_length | choices |
            +-------------+------------+-------+-----+-----+---------+----------------+------------+------------+---------+
            | bool_column |       bool |  true |     |     |         |                |            |            |         |
            | json_column |       json | false |     |     |         |                |            |            |         |
            +-------------+------------+-------+-----+-----+---------+----------------+------------+------------+---------+
        """
        )
        self.assert_generate_schema(
            "txt", expected, export_fields=["bool_column", "json_column"]
        )

        expected = dedent(
            """
        CREATE TABLE IF NOT EXISTS "this_is_my_table" (
            "bool_column" BOOL,
            "json_column" TEXT NOT NULL
        );
        """
        )
        self.assert_generate_schema(
            "sql", expected, export_fields=["bool_column", "json_column"]
        )

        expected = dedent(
            """
        from django.db import models


        class ThisIsMyTable(models.Model):
            bool_column = models.BooleanField(null=True, blank=True)
            json_column = models.JSONField(null=False, blank=False)
        """
        )
        self.assert_generate_schema(
            "django", expected, export_fields=["bool_column", "json_column"]
        )

    def test_load_schema(self):
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        self.files_to_delete.append(temp.name)
        temp.file.write(
            dedent(
                """
        field_name,field_type
        f1,text
        f2,decimal
        f3,float
        f4,integer
        """
            )
            .strip()
            .encode("utf-8")
        )
        temp.file.close()
        schema = rows.utils.load_schema(temp.name)
        expected = OrderedDict(
            [
                ("f1", fields.TextField),
                ("f2", fields.DecimalField),
                ("f3", fields.FloatField),
                ("f4", fields.IntegerField),
            ]
        )
        assert schema == expected

    def test_load_schema_with_context(self):
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        self.files_to_delete.append(temp.name)
        temp.file.write(
            dedent(
                """
        field_name,field_type
        f1,text
        f2,decimal
        f3,custom1
        f4,custom2
        """
            )
            .strip()
            .encode("utf-8")
        )
        temp.file.close()

        class Custom1Field(fields.TextField):
            pass

        class Custom2Field(fields.TextField):
            pass

        context = {
            "text": fields.IntegerField,
            "decimal": fields.TextField,
            "custom1": Custom1Field,
            "custom2": Custom2Field,
        }
        schema = rows.utils.load_schema(temp.name, context=context)
        expected = OrderedDict(
            [
                ("f1", fields.IntegerField),
                ("f2", fields.TextField),
                ("f3", Custom1Field),
                ("f4", Custom2Field),
            ]
        )
        assert schema == expected

    def test_source_from_path(self):
        path = pathlib.Path("/tmp/test.csv")
        source = rows.utils.Source.from_file(path, mode="w")
        assert source.uri == path
        source.fobj.close()


class PgUtilsTestCase(unittest.TestCase):
    def test_pg_create_table_sql(self):
        schema = OrderedDict(
            [("id", rows.fields.IntegerField), ("name", rows.fields.TextField)]
        )
        sql = rows.utils.pg_create_table_sql(schema, "testtable")
        assert (
            sql
            == """CREATE TABLE IF NOT EXISTS "testtable" ("id" BIGINT, "name" TEXT)"""
        )


def test_scale_number():
    scale_number = rows.utils.scale_number

    assert scale_number(100) == "100"
    assert scale_number(1000) == "1.00K"
    assert scale_number(1500) == "1.50K"
    assert scale_number(10000) == "10.00K"
    assert scale_number(1000000) == "1.00M"
    assert scale_number(1234000000) == "1.23G"
    assert scale_number(1234567890000) == "1.23T"

    assert scale_number(1000, divider=1024) == "1000"
    assert scale_number(1024, divider=1024) == "1.00K"
    assert scale_number(1024, divider=1024, suffix="iB") == "1.00KiB"

    assert scale_number(1234567890000, decimal_places=3) == "1.235T"
    assert scale_number(1234567890000, multipliers="KMGtP") == "1.23t"


# TODO: test Source.from_file
# TODO: test/implement load_schema with file object
# TODO: test detect_local_source
# TODO: test detect_source
# TODO: test download_file
# TODO: test export_to_uri
# TODO: test extension_by_plugin_name
# TODO: test import_from_source
# TODO: test import_from_uri
# TODO: test local_file
# TODO: test normalize_mime_type
# TODO: test plugin_name_by_mime_type
# TODO: test plugin_name_by_uri
