# coding: utf-8
from __future__ import unicode_literals

import io

import pytest

import rows


class BinaryFileWithoutMode(object):
    """A binary file proxy without a mode attribute, like a memory upload."""

    def __init__(self, content):
        self.file = io.BytesIO(content)

    def __getattr__(self, name):
        return getattr(self.file, name)

    def __iter__(self):
        return iter(self.file)


@pytest.mark.parametrize("encoding", ["utf-8", "latin-1"])
@pytest.mark.parametrize("kind", ["proxy", "django", "bytesio", "disk"])
def test_import_csv_binary_file_without_mode(tmp_path, encoding, kind):
    content = "name;value\r\nÁlvaro;one\r\nAlice;two\r\n".encode(encoding)
    if kind == "proxy":
        source = BinaryFileWithoutMode(content)
        assert not hasattr(source, "mode")
    elif kind == "django":
        uploadedfile = pytest.importorskip("django.core.files.uploadedfile")
        source = uploadedfile.InMemoryUploadedFile(
            io.BytesIO(content), "file", "data.csv", "text/csv", len(content), encoding
        )
    elif kind == "bytesio":
        source = io.BytesIO(content)
    else:
        source = tmp_path / "data.csv"
        source.write_bytes(content)

    table = rows.import_from_csv(source, encoding=encoding)

    assert list(table.fields) == ["name", "value"]
    assert [tuple(row) for row in table] == [("Álvaro", "one"), ("Alice", "two")]


@pytest.mark.parametrize("explicit_dialect", [False, True])
def test_import_csv_binary_proxy_preserves_current_position(explicit_dialect):
    source = BinaryFileWithoutMode(b"skip this line\nname;value\nAlice;one\n")
    source.readline()
    kwargs = {"dialect": "excel-semicolon"} if explicit_dialect else {}

    table = rows.import_from_csv(source, **kwargs)

    assert list(table.fields) == ["name", "value"]
    assert [tuple(row) for row in table] == [("Alice", "one")]


def test_import_csv_text_proxy_with_explicit_dialect():
    source = io.StringIO("name;value\nAlice;one\n")

    table = rows.import_from_csv(source, dialect="excel-semicolon")

    assert [tuple(row) for row in table] == [("Alice", "one")]
