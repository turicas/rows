# coding: utf-8

# Copyright 2014-2017 Álvaro Justen <https://github.com/turicas/rows/>

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

import csv
import io
import os
import psycopg2
import sqlite3
from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

from rows.cli import cli, create_complete_query
from rows.compat import PYTHON_VERSION, TEXT_TYPE


if PYTHON_VERSION < (3, 0, 0):
    from urlparse import urlparse, urlunparse
else:
    from urllib.parse import urlparse, urlunparse


sample_csv_content = dedent("""
    Name  , Age!
    Alice,30
    Bob,25
    Álvaro,37
""").strip()
tests_data_path = Path(__file__).parent / "data"

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL is not None:
    parsed = urlparse(DATABASE_URL)
    TEST_DATABASE_NAME = "test_py" + "_".join(str(item) for item in PYTHON_VERSION)
    TEST_DATABASE_URL = urlunparse(
        (parsed.scheme, parsed.netloc, "/{}".format(TEST_DATABASE_NAME), parsed.params, parsed.query, parsed.fragment)
    )
else:
    TEST_DATABASE_URL = None


def read_csv(filename):
    filename = Path(TEXT_TYPE(filename))
    with filename.open(encoding="utf-8") as fobj:  # TODO: may not work for py2
        return list(csv.DictReader(fobj))


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def sample_csv(tmp_path):
    file_path = tmp_path / "people.csv"
    file_path.write_text(sample_csv_content, encoding="utf-8")
    return file_path


@pytest.fixture()
def sample_csv_iso_885915(tmp_path):
    file_path = tmp_path / "people-iso-8859-15.csv"
    file_path.write_text(sample_csv_content, encoding="iso-8859-15")
    return file_path


def test_convert_csv_to_csv(runner, tmp_path, sample_csv):
    output_file = tmp_path / "out.csv"
    result = runner.invoke(cli, ["convert", str(sample_csv), str(output_file)])
    assert result.exit_code == 0, result.output
    assert output_file.exists()
    data = read_csv(output_file)
    expected = [
        {"name": "Alice", "age": "30"},
        {"name": "Bob", "age": "25"},
        {"name": "Álvaro", "age": "37"},
    ]
    assert data == expected


def test_convert_fields_and_order_by_desc(runner, tmp_path, sample_csv):
    out_file = tmp_path / "ordered.csv"
    result = runner.invoke(
        cli,
        ["convert", "--fields", "age,name", "--order-by", "^age", str(sample_csv), str(out_file)],
    )
    assert result.exit_code == 0, result.output
    ages = [row["age"] for row in read_csv(out_file)]
    assert ages == ["37", "30", "25"]
    assert out_file.read_text(encoding="utf-8").splitlines()[0].strip() == "age,name"


def test_convert_fields_exclude(runner, tmp_path, sample_csv):
    out_file = tmp_path / "nofield.csv"
    result = runner.invoke(
        cli,
        [
            "convert",
            "--fields-exclude", "age",
            str(sample_csv),
            str(out_file),
        ],
    )
    assert result.exit_code == 0, result.output
    rows = read_csv(out_file)
    assert list(rows[0].keys()) == ["name"]


def test_join_two_csvs(runner, tmp_path):
    csv1 = tmp_path / "left.csv"
    csv1.write_text(dedent("""
        id,name
        1,Alice
        2,Bob
        3,Álvaro
    """).strip(), encoding="utf-8")
    csv2 = tmp_path / "right.csv"
    csv2.write_text(dedent("""
        id,score
        1,9.5
        2,7.0
        3,10.0
    """).strip(), encoding="utf-8")
    output_file = tmp_path / "joined.csv"
    result = runner.invoke(
        cli,
        ["join", "id", str(csv1), str(csv2), str(output_file)],
    )
    assert result.exit_code == 0, result.output
    assert output_file.exists()
    data = read_csv(output_file)
    expected = [
        {"id": "1", "name": "Alice", "score": "9.5"},
        {"id": "2", "name": "Bob", "score": "7.0"},
        {"id": "3", "name": "Álvaro", "score": "10.0"},
    ]
    assert data == expected


def test_sum_two_csvs(runner, tmp_path):
    csv1 = tmp_path / "part1.csv"
    csv1.write_text(dedent("""
        Name   , Age!!
        Alice,30
        Álvaro,37
    """).strip(), encoding="utf-8")
    csv2 = tmp_path / "part2.csv"
    csv2.write_text(dedent("""
        name,age
        Bob,25
    """).strip(), encoding="utf-8")
    output_file = tmp_path / "total.csv"
    result = runner.invoke(
        cli,
        ["sum", str(csv1), str(csv2), str(output_file)],
    )
    assert result.exit_code == 0
    assert output_file.exists()
    data = read_csv(output_file)
    expected = [
        {"name": "Alice", "age": "30"},
        {"name": "Álvaro", "age": "37"},
        {"name": "Bob", "age": "25"},
    ]
    assert data == expected


def test_print_command(runner, sample_csv):
    result = runner.invoke(cli, ["print", str(sample_csv)], catch_exceptions=False)
    assert result.exit_code == 0
    expected = dedent("""
        +--------+-----+
        |  name  | age |
        +--------+-----+
        |  Alice |  30 |
        |    Bob |  25 |
        | Álvaro |  37 |
        +--------+-----+
    """).strip()
    assert result.output.strip() == expected


def test_print_fields_exclude_no_frame(runner, sample_csv):
    result = runner.invoke(
        cli,
        [
            "print",
            "--fields-exclude", "age",
            "--frame-style", "double",
            str(sample_csv)
        ],
    )
    assert result.exit_code == 0
    expected = dedent("""
        ╔════════╗
        ║  name  ║
        ╠════════╣
        ║  Alice ║
        ║    Bob ║
        ║ Álvaro ║
        ╚════════╝
    """).strip()
    assert result.output.strip() == expected


def test_query_where_clause(runner, sample_csv):
    result = runner.invoke(
        cli,
        ["query", "age > 25 AND age < 35", str(sample_csv)],
    )
    assert result.exit_code == 0
    expected = dedent("""
        +-------+-----+
        |  name | age |
        +-------+-----+
        | Alice |  30 |
        +-------+-----+
    """).strip()
    assert result.output.strip() == expected


def test_schema_txt(runner, sample_csv, tmp_path):
    output_file = tmp_path / "schema.txt"
    result = runner.invoke(
        cli,
        ["schema", "--format", "txt", str(sample_csv), str(output_file)],
    )
    assert output_file.exists()
    result_data = output_file.read_text(encoding="utf-8")
    expected = dedent("""
        +------------+------------+-------+-----+-----+----------+----------------+------------+------------+---------------------------------+
        | field_name | field_type |  null | min | max | subtype  | decimal_places | max_digits | max_length |             choices             |
        +------------+------------+-------+-----+-----+----------+----------------+------------+------------+---------------------------------+
        |       name |       text | false |     |     |  VARCHAR |                |            |          6 | ["Alice", "Bob", "\\u00c1lvaro"] |
        |        age |    integer | false |  25 |  37 | SMALLINT |                |            |            |                            null |
        +------------+------------+-------+-----+-----+----------+----------------+------------+------------+---------------------------------+
    """).strip()
    assert result_data.strip() == expected


def test_schema_max_samples(runner, tmp_path):
    csvfile = tmp_path / "wrong-types.csv"
    csvfile.write_text(dedent("""
        name,age
        Alice,30
        Bob,25
        Álvaro,37
        Somebody,Not a number
    """).strip(), encoding="utf-8")
    output_file = tmp_path / "schema.txt"
    result = runner.invoke(
        cli,
        ["schema", "--format", "txt", "--samples", "3", str(csvfile), str(output_file)],
    )
    assert output_file.exists()
    result_data = output_file.read_text(encoding="utf-8")
    expected = dedent("""
        +------------+------------+-------+-----+-----+----------+----------------+------------+------------+---------------------------------+
        | field_name | field_type |  null | min | max | subtype  | decimal_places | max_digits | max_length |             choices             |
        +------------+------------+-------+-----+-----+----------+----------------+------------+------------+---------------------------------+
        |       name |       text | false |     |     |  VARCHAR |                |            |          6 | ["Alice", "Bob", "\\u00c1lvaro"] |
        |        age |    integer | false |  25 |  37 | SMALLINT |                |            |            |                            null |
        +------------+------------+-------+-----+-----+----------+----------------+------------+------------+---------------------------------+
    """).strip()
    assert result_data.strip() == expected


def test_schema_csv_detect_all_types(runner, sample_csv):
    result = runner.invoke(
        cli,
        ["schema", "--format", "csv", "--exclude-choices", "name", str(sample_csv), "-"],
    )
    assert result.exit_code == 0
    header = result.output.splitlines()[0]
    expected = [
        {
            "field_name": "name",
            "field_type": "text",
            "null": "false",
            "min": "",
            "max": "",
            "subtype": "VARCHAR",
            "decimal_places": "",
            "max_digits": "",
            "max_length": "6",
            "choices": "",
        },
        {
            "field_name": "age",
            "field_type": "integer",
            "null": "false",
            "min": "25",
            "max": "37",
            "subtype": "SMALLINT",
            "decimal_places": "",
            "max_digits": "",
            "max_length": "",
            "choices": "",
        }
    ]
    assert list(csv.DictReader(io.StringIO(result.output))) == expected


def test_csv_inspect_encoding(runner, sample_csv, sample_csv_iso_885915):
    result = runner.invoke(cli, ["csv-inspect", str(sample_csv)])
    assert result.exit_code == 0
    expected = dedent("""
        encoding = 'utf-8'
        dialect.delimiter = ','
        dialect.doublequote = True
        dialect.escapechar = None
        dialect.lineterminator = '\\r\\n'
        dialect.quotechar = '"'
        dialect.quoting = csv.QUOTE_MINIMAL
        dialect.skipinitialspace = True
        dialect.strict = False
    """).strip()
    # We don't test encoding here since the detection could go wrong (needs to enhance the encoding detection part)
    encoding_line = result.output.strip().splitlines()[0]
    assert encoding_line.startswith("encoding = ")
    assert result.output.strip().splitlines()[1:] == expected.splitlines()[1:]

    result2 = runner.invoke(cli, ["csv-inspect", str(sample_csv_iso_885915)])
    assert result2.exit_code == 0
    encoding_line2 = result2.output.strip().splitlines()[0]
    assert encoding_line2.startswith("encoding = ")
    assert encoding_line2 != encoding_line
    assert result.output.strip().splitlines()[1:] == expected.splitlines()[1:]


def test_csv_fix_basic(runner, tmp_path):
    # TODO: test csv with more empty fields (only in header) and other dirty cases
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text(dedent('''
        Name  , Age!
        Alice,30
        Bob,25
    ''').strip(), encoding="utf-8")
    fixed_csv = tmp_path / "fixed.csv"
    result = runner.invoke(
        cli,
        ["csv-fix", str(bad_csv), str(fixed_csv)],
    )
    assert result.exit_code == 0
    assert fixed_csv.exists()
    data = read_csv(fixed_csv)
    expected = [
        {"name": "Alice", "age": "30"},
        {"name": "Bob", "age": "25"},
    ]
    assert expected == data



def test_csv_to_sqlite_and_back(runner, tmp_path, sample_csv):
    dbfile = tmp_path / "data.sqlite"
    # csv-to-sqlite
    result1 = runner.invoke(cli, ["csv-to-sqlite", str(sample_csv), str(dbfile)])
    assert result1.exit_code == 0, result1.output
    assert dbfile.exists()
    # sqlite-to-csv
    out_csv = tmp_path / "roundtrip.csv"
    result2 = runner.invoke(
        cli,
        ["sqlite-to-csv", str(dbfile), "people", str(out_csv)],
    )
    # sqlite table name is based on original CSV name (without ".csv")
    assert result2.exit_code == 0, result2.output
    assert out_csv.exists()
    data = read_csv(out_csv)
    expected = [
        {"name": "Alice", "age": "30"},
        {"name": "Bob", "age": "25"},
        {"name": "Álvaro", "age": "37"},
    ]
    assert expected == data


def test_csv_merge(runner, tmp_path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    a.write_text(dedent("""
        id,name
        1,Alice
    """).strip(), encoding="utf-8")
    b.write_text(dedent("""
        id,score
        1,10
    """).strip(), encoding="utf-8")
    merged = tmp_path / "merged.csv"
    result = runner.invoke(
        cli,
        ["csv-merge", str(a), str(b), str(merged)],
    )
    assert result.exit_code == 0
    assert merged.exists()
    data = read_csv(merged)
    expected = [
        {"id": "1", "name": "Alice", "score": ""},
        {"id": "1", "name": "", "score": "10"},
    ]
    assert expected == data


def test_csv_merge_no_strip(runner, tmp_path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    a.write_text(dedent("""
        id , txt
        1 ,"  foo"
    """).strip(), encoding="utf-8")
    b.write_text(dedent("""
        id , txt
        1 ,"  bar"
    """).strip(), encoding="utf-8")
    merged = tmp_path / "merged.csv"
    result = runner.invoke(
        cli,
        [
            "csv-merge",
            "--no-strip",
            "--no-remove-empty-lines",
            str(a), str(b), str(merged)
        ],
    )
    assert result.exit_code == 0
    expected = [
        {"id": "1 ", "txt": "  foo"},
        {"id": "1 ", "txt": "  bar"},
    ]
    assert read_csv(merged) == expected

def test_csv_clean(tmp_path, runner):
    dirty = tmp_path / "dirty.csv"
    dirty.write_text(dedent("""
         id ,name ,
        1 , Alice ,

    """).strip(), encoding="utf-8")
    cleaned = tmp_path / "cleaned.csv"
    result = runner.invoke(
        cli,
        ["csv-clean", str(dirty), str(cleaned)],
    )
    assert result.exit_code == 0
    assert cleaned.exists()
    expected = [{"id": "1", "name": "Alice"}]
    assert read_csv(cleaned) == expected


def test_csv_clean_in_place(tmp_path, runner):
    dirty = tmp_path / "dirty.csv"
    dirty.write_text(dedent("""
         id ,name ,
        1 , Alice ,

    """).strip(), encoding="utf-8")
    result = runner.invoke(cli, ["csv-clean", "--in-place", str(dirty)])
    assert result.exit_code == 0, result.output
    expected = [{"id": "1", "name": "Alice"}]
    assert read_csv(dirty) == expected


def test_csv_row_count(runner, sample_csv):
    result = runner.invoke(cli, ["csv-row-count", str(sample_csv)])
    assert result.exit_code == 0
    assert result.output.strip() == "3"


def test_csv_split(runner, tmp_path):
    csvfile = tmp_path / "big.csv"
    csvfile.write_text(dedent("""
        id
        0
        1
        2
        3
        4
        5
        6
        7
        8
        9
    """).strip(), encoding="utf-8")
    result = runner.invoke(cli, ["csv-split", str(csvfile), "3"])
    assert result.exit_code == 0
    parts = sorted(tmp_path.glob("big-*.csv"))
    assert len(parts) == 4  # 10 rows -> 4 parts of 3,3,3,1
    assert len(read_csv(parts[0])) == 3
    assert len(read_csv(parts[1])) == 3
    assert len(read_csv(parts[2])) == 3
    assert len(read_csv(parts[3])) == 1


def test_csv_split_with_pattern(runner, tmp_path):
    csvfile = tmp_path / "data.csv"
    csvfile.write_text(dedent("""
        id
        0
        1
        2
        3
    """).strip(), encoding="utf-8")
    result = runner.invoke(
        cli,
        ["csv-split", "--destination-pattern", str(tmp_path / "part-{part:02d}.csv"), str(csvfile), "2"]
    )
    assert result.exit_code == 0
    parts = sorted([str(filename) for filename in tmp_path.glob("part-*.csv")])
    expected = [
        str(tmp_path / "part-01.csv"),
        str(tmp_path / "part-02.csv"),
    ]
    assert parts == expected


def test_list_sheets_invalid_extension(runner, tmp_path):
    filenames = [
        tests_data_path / "all-field-types.xls",
        tests_data_path / "all-field-types.xlsx",
    ]
    for filename in filenames:
        result = runner.invoke(cli, ["list-sheets", str(filename)])
        assert result.exit_code == 0
        assert result.output.strip() == "Sheet1"

    filename = tests_data_path / "empty-date.xls"
    result = runner.invoke(cli, ["list-sheets", str(filename)])
    assert result.exit_code == 0
    assert result.output.strip() == "Sheet1\nSheet2"


@pytest.mark.skipif(TEST_DATABASE_URL is None, reason="postgres service is not running")
def test_pgexport_import_cycle(tmp_path, runner):
    # First, create test database
    connection = psycopg2.connect(DATABASE_URL)
    connection.autocommit = True
    cursor = connection.cursor()
    cursor.execute("DROP DATABASE IF EXISTS {}".format(TEST_DATABASE_NAME))
    cursor.execute("CREATE DATABASE {}".format(TEST_DATABASE_NAME))
    cursor.close()

    conn = psycopg2.connect(TEST_DATABASE_URL)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS test_rows;")
    cur.execute("CREATE TABLE test_rows(id integer, txt text)")
    cur.execute("INSERT INTO test_rows VALUES (1, 'foo'), (2, 'bar')")
    conn.commit()

    # Export
    csvfile = tmp_path / "pg.csv"
    result = runner.invoke(
        cli,
        ["pgexport", TEST_DATABASE_URL, "test_rows", str(csvfile)],
    )
    assert result.exit_code == 0
    assert csvfile.exists()
    expected = [
        {"id": "1", "txt": "foo"},
        {"id": "2", "txt": "bar"},
    ]
    assert read_csv(csvfile) == expected

    # Export query
    csvfile2 = tmp_path / "pg2.csv"
    result = runner.invoke(
        cli,
        ["pgexport", TEST_DATABASE_URL, "--is-query", "SELECT * FROM test_rows WHERE id > 1", str(csvfile2)],
    )
    assert result.exit_code == 0
    assert csvfile2.exists()
    expected = [
        {"id": "2", "txt": "bar"},
    ]
    assert read_csv(csvfile2) == expected

    # Import to another table
    result2 = runner.invoke(
        cli,
        ["pgimport", str(csvfile), TEST_DATABASE_URL, "test_rows_copy"],
    )
    assert result2.exit_code == 0
    cur.execute("SELECT COUNT(*) FROM test_rows_copy")
    assert cur.fetchone()[0] == 2

    # pg2pg
    cur.execute("DROP TABLE IF EXISTS test_rows_copy_pg2pg")
    conn.commit()
    result = runner.invoke(
        cli,
        ["pg2pg", "--binary", TEST_DATABASE_URL, "test_rows", TEST_DATABASE_URL, "test_rows_copy_pg2pg"],
    )
    assert result.exit_code == 0, result.output
    cur.execute("SELECT COUNT(*) FROM test_rows_copy_pg2pg")
    assert cur.fetchone()[0] == 2
    conn.close()


def test_pdf_to_text_basic(runner, tmp_path):
    pdf_path = tests_data_path / "balneabilidade-26-2010.pdf"
    txt_path = tmp_path / "out.txt"
    result = runner.invoke(
        cli,
        ["pdf-to-text", str(pdf_path), str(txt_path)],
    )
    assert result.exit_code == 0
    assert "Em frente à Rua da Música" in txt_path.read_text(encoding="utf-8")


def test_create_complete_query():
    query = "-- Olá\n--Como vai?\n\n\n\t--aqui tem outro\n-- SELECT ahaha\n\t\n\n/*\nmultiline\ncomments\nin\nSQL\n\t\t\tWITH x AS (SELECT * FROM foo) SELECT * FROM x\n--teste\t\t*/\n\t\tSELECT * FROM bar"
    result = create_complete_query(query, [])
    expected = query
    assert result == expected

    result = create_complete_query("a > 1", ["tableX"])
    expected = "SELECT * FROM tableX WHERE a > 1"
    assert result == expected
