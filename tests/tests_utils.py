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
import io
import lzma
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

        self.assertEqual(first.lower().split("-")[:-1], second.lower().split("-")[:-1])

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
        self.assertEqual(result.uri, temp.name)
        self.assert_encoding(result.encoding, encoding)
        self.assertEqual(result.should_delete, False)


class SchemaTestCase(utils.RowsTestMixIn, unittest.TestCase):

    def assert_generate_schema(self, fmt, expected, export_fields=None):
        # prepare a consistent table so we can test all formats using it
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

        result = rows.utils.generate_schema(table, export_fields, fmt)
        self.assertEqual(expected.strip(), result.strip())

    def test_generate_schema_txt(self):
        expected = dedent(
            """
            +-----------------+------------+
            |    field_name   | field_type |
            +-----------------+------------+
            |     bool_column |       bool |
            |  integer_column |    integer |
            |    float_column |      float |
            |  decimal_column |    decimal |
            |  percent_column |    decimal |
            |     date_column |       date |
            | datetime_column |   datetime |
            |  unicode_column |       text |
            |     json_column |       json |
            +-----------------+------------+
        """
        )
        self.assert_generate_schema("txt", expected)

    def test_generate_schema_sql(self):
        expected = dedent(
            """
        CREATE TABLE IF NOT EXISTS this_is_my_table (
            bool_column BOOL,
            integer_column INT,
            float_column FLOAT,
            decimal_column FLOAT,
            percent_column FLOAT,
            date_column DATE,
            datetime_column DATETIME,
            unicode_column TEXT,
            json_column TEXT
        );
        """
        )
        self.assert_generate_schema("sql", expected)

    def test_generate_schema_django(self):
        expected = dedent(
            """
        from django.db import models
        from django.contrib.postgres.fields import JSONField

        class ThisIsMyTable(models.Model):
            bool_column = models.BooleanField()
            integer_column = models.IntegerField()
            float_column = models.FloatField()
            decimal_column = models.DecimalField()
            percent_column = models.DecimalField()
            date_column = models.DateField()
            datetime_column = models.DateTimeField()
            unicode_column = models.TextField()
            json_column = JSONField()
        """
        )
        self.assert_generate_schema("django", expected)

    def test_generate_schema_restricted_fields(self):
        expected = dedent(
            """
            +-------------+------------+
            |  field_name | field_type |
            +-------------+------------+
            | bool_column |       bool |
            | json_column |       json |
            +-------------+------------+
        """
        )
        self.assert_generate_schema(
            "txt", expected, export_fields=["bool_column", "json_column"]
        )

        expected = dedent(
            """
        CREATE TABLE IF NOT EXISTS this_is_my_table (
            bool_column BOOL,
            json_column TEXT
        );
        """
        )
        self.assert_generate_schema(
            "sql", expected, export_fields=["bool_column", "json_column"]
        )

        expected = dedent(
            """
        from django.db import models
        from django.contrib.postgres.fields import JSONField

        class ThisIsMyTable(models.Model):
            bool_column = models.BooleanField()
            json_column = JSONField()
        """
        )
        self.assert_generate_schema(
            "django", expected, export_fields=["bool_column", "json_column"]
        )

    def test_load_schema(self):
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        self.files_to_delete.append(temp.name)
        temp.file.write(dedent(
        """
        field_name,field_type
        f1,text
        f2,decimal
        f3,float
        f4,integer
        """).strip().encode("utf-8"))
        temp.file.close()
        schema = rows.utils.load_schema(temp.name)
        expected = OrderedDict([
            ("f1", fields.TextField),
            ("f2", fields.DecimalField),
            ("f3", fields.FloatField),
            ("f4", fields.IntegerField),
        ])
        assert schema == expected

    def test_load_schema_with_context(self):
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        self.files_to_delete.append(temp.name)
        temp.file.write(dedent(
        """
        field_name,field_type
        f1,text,
        f2,decimal
        f3,custom1
        f4,custom2
        """).strip().encode("utf-8"))
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
        expected = OrderedDict([
            ("f1", fields.IntegerField),
            ("f2", fields.TextField),
            ("f3", Custom1Field),
            ("f4", Custom2Field),
        ])
        assert schema == expected

    def test_source_from_path(self):
        path = pathlib.Path("/tmp/test.csv")
        source = rows.utils.Source.from_file(path, mode="w")
        self.assertEqual(source.uri, path)
        source.fobj.close()

    def assert_open_compressed_binary(self, suffix, decompress):
        content = "Álvaro"
        encoding = "iso-8859-1"
        content_encoded = content.encode(encoding)

        temp = tempfile.NamedTemporaryFile(delete=False)
        filename = temp.name + (suffix or "")
        self.files_to_delete.append(filename)
        fobj = rows.utils.open_compressed(filename, mode="wb")
        fobj.write(content_encoded)
        fobj.close()
        assert decompress(open(filename, mode="rb").read()) == content_encoded

    def assert_open_compressed_text(self, suffix, decompress):
        content = "Álvaro"
        encoding = "iso-8859-1"
        content_encoded = content.encode(encoding)

        temp = tempfile.NamedTemporaryFile(delete=False)
        filename = temp.name + (suffix or "")
        self.files_to_delete.append(filename)
        fobj = rows.utils.open_compressed(filename, mode="w", encoding=encoding)
        fobj.write(content)
        fobj.close()
        assert decompress(open(filename, mode="rb").read()).decode(encoding) == content

    def test_open_compressed(self):
        # No compression
        same_content = lambda data: data
        self.assert_open_compressed_binary(suffix="", decompress=same_content)
        self.assert_open_compressed_text(suffix="", decompress=same_content)

        # Gzip
        self.assert_open_compressed_binary(suffix=".gz", decompress=gzip.decompress)
        self.assert_open_compressed_text(suffix=".gz", decompress=gzip.decompress)

        # Lzma
        self.assert_open_compressed_binary(suffix=".xz", decompress=lzma.decompress)
        self.assert_open_compressed_text(suffix=".xz", decompress=lzma.decompress)

        # Bz2
        self.assert_open_compressed_binary(suffix=".bz2", decompress=bz2.decompress)
        self.assert_open_compressed_text(suffix=".bz2", decompress=bz2.decompress)


class PgUtilsTestCase(unittest.TestCase):

    def test_pg_create_table_sql(self):
        schema = OrderedDict([("id", rows.fields.IntegerField), ("name", rows.fields.TextField)])
        sql = rows.utils.pg_create_table_sql(schema, "testtable")
        assert sql == """CREATE TABLE IF NOT EXISTS "testtable" (id BIGINT, name TEXT)"""


def test_scale_number():
    scale_number = rows.utils.scale_number

    assert scale_number(100) == "100"
    assert scale_number(1_000) == "1.00K"
    assert scale_number(1_500) == "1.50K"
    assert scale_number(10_000) == "10.00K"
    assert scale_number(1_000_000) == "1.00M"
    assert scale_number(1_234_000_000) == "1.23G"
    assert scale_number(1_234_567_890_000) == "1.23T"

    assert scale_number(1_000, divider=1_024) == "1000"
    assert scale_number(1_024, divider=1_024) == "1.00K"
    assert scale_number(1_024, divider=1_024, suffix="iB") == "1.00KiB"

    assert scale_number(1_234_567_890_000, decimal_places=3) == "1.235T"
    assert scale_number(1_234_567_890_000, multipliers="KMGtP") == "1.23t"


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
