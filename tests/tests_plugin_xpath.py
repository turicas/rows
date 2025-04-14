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

import io
import tempfile
import unittest
from collections import OrderedDict
from pathlib import Path

import mock
import pytest

import rows
import tests.utils as utils

ALIAS_IMPORT = rows.import_from_xpath  # Lazy function (just aliases)


class PluginXPathTestCase(utils.RowsTestMixIn, unittest.TestCase):

    filename = "tests/data/ecuador-medios-radiodifusoras.html"
    encoding = "utf-8"
    expected_data = "tests/data/ecuador-medios-radiodifusoras.csv"

    def setUp(self):
        rows_xpath = (
            '//*[@class="entry-container"]/*[@class="row-fluid"]/*[@class="span6"]'
        )
        fields_xpath = OrderedDict(
            [
                ("url", ".//h2/a/@href"),
                ("name", ".//h2/a/text()"),
                ("address", './/div[@class="spField field_direccion"]/text()'),
                ("phone", './/div[@class="spField field_telefono"]/text()'),
                ("website", './/div[@class="spField field_sitio_web"]/text()'),
                ("email", './/div[@class="spField field_email"]/text()'),
            ]
        )
        self.kwargs = {"rows_xpath": rows_xpath, "fields_xpath": fields_xpath}

        self.expected_table = rows.import_from_csv(self.expected_data)
        self.files_to_delete = []

    def test_imports(self):
        # Force the plugin to load
        original_import = rows.plugins.xpath.import_from_xpath
        assert id(ALIAS_IMPORT) != id(original_import)
        new_alias_import = rows.import_from_xpath
        assert id(new_alias_import) == id(original_import)  # Function replaced with loaded one

    def test_import_from_xpath_filename(self):
        table = rows.import_from_xpath(self.filename, encoding=self.encoding, **self.kwargs)
        meta = table.meta.copy()
        source = meta.pop("source")
        assert source.uri == Path(self.filename)
        expected_meta = {"imported_from": "xpath"}
        assert meta == expected_meta
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        fobj = temp.file
        fobj2 = rows.export_to_csv(table, fobj)
        fobj.seek(0)
        table = rows.import_from_csv(fobj)
        self.assert_table_equal(table, self.expected_table)

    def test_import_from_xpath_fobj_binary(self):
        with open(self.filename, mode="rb") as fobj:
            table = rows.import_from_xpath(fobj, encoding=self.encoding, **self.kwargs)
        meta = table.meta.copy()
        source = meta.pop("source")
        assert source.uri == Path(self.filename)
        expected_meta = {"imported_from": "xpath"}
        assert meta == expected_meta
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        fobj = temp.file
        rows.export_to_csv(table, fobj)
        fobj.seek(0)
        table = rows.import_from_csv(fobj)
        self.assert_table_equal(table, self.expected_table)

    def test_import_from_xpath_fobj_binary_without_encoding(self):
        with open(self.filename, mode="rb") as fobj:
            with pytest.raises(ValueError, match="import_from_xpath must receive an encoding when file is in binary mode"):
                rows.import_from_xpath(fobj, encoding=None, **self.kwargs)

    def test_import_from_xpath_fobj_text(self):
        with io.TextIOWrapper(io.open(self.filename, mode="rb"), encoding="utf-8") as fobj:
            table = rows.import_from_xpath(fobj, encoding=self.encoding, **self.kwargs)
        meta = table.meta.copy()
        source = meta.pop("source")
        assert source.uri == Path(self.filename)
        expected_meta = {"imported_from": "xpath"}
        assert meta == expected_meta
        temp = tempfile.NamedTemporaryFile(delete=False)
        self.files_to_delete.append(temp.name)
        fobj = temp.file
        rows.export_to_csv(table, fobj)
        fobj.seek(0)
        table = rows.import_from_csv(fobj)
        self.assert_table_equal(table, self.expected_table)

    def test_import_from_xpath_unescape_and_extract_text(self):
        html = """
          <ul>
            <li><a href="/wiki/Abadia_de_Goi%C3%A1s" title="Abadia de Goiás">Abadia de Goi&aacute;s</a> (GO)</li>
            <li><a href="/wiki/Abadi%C3%A2nia" title="Abadiânia">Abadi&acirc;nia</a> (GO)</li>
          </ul>
        """.encode(
            "utf-8"
        )
        rows_xpath = "//ul/li"
        fields_xpath = OrderedDict([("name", ".//text()"), ("link", ".//a/@href")])
        table = rows.import_from_xpath(
            io.BytesIO(html),
            rows_xpath=rows_xpath,
            fields_xpath=fields_xpath,
            encoding="utf-8",
        )
        assert table[0].name == "Abadia de Goiás (GO)"
        assert table[1].name == "Abadiânia (GO)"

    @mock.patch("rows.plugins.xpath.create_table")
    def test_import_from_xpath_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        encoding = "iso-8859-15"
        kwargs = {"some_key": 123, "other": 456}
        self.kwargs.update(kwargs)

        result = rows.import_from_xpath(self.filename, encoding=encoding, **self.kwargs)
        assert mocked_create_table.called
        assert mocked_create_table.call_count == 1
        assert result == 42

    def test_xpath_must_be_text_type(self):
        with self.assertRaises(TypeError):
            rows.import_from_xpath(
                self.filename,
                encoding=self.encoding,
                rows_xpath=b"//div",
                fields_xpath={"f1": ".//span"},
            )

        with self.assertRaises(TypeError):
            rows.import_from_xpath(
                self.filename,
                encoding=self.encoding,
                rows_xpath="//div",
                fields_xpath={"f1": b".//span"},
            )
