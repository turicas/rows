# coding: utf-8

# Copyright 2014-2020 Álvaro Justen <https://github.com/turicas/rows/>

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

import datetime
import json
import platform
import unittest
import uuid
from base64 import b64encode
from decimal import Decimal

import rows
from rows import fields
from rows.compat import BINARY_TYPE, TEXT_TYPE

if platform.system() == "Windows":
    locale_name = "ptb_bra"
else:
    locale_name = "pt_BR.UTF-8"


class FieldsTestCase(unittest.TestCase):
    def test_Field(self):
        assert fields.Field.TYPE == (type(None),)
        assert fields.Field.deserialize(None) is None
        assert fields.Field.deserialize("Álvaro") == "Álvaro"
        assert fields.Field.serialize(None) == ""
        assert type(fields.Field.serialize(None)) is TEXT_TYPE
        assert fields.Field.serialize("Álvaro") == "Álvaro"
        assert type(fields.Field.serialize("Álvaro")) is TEXT_TYPE

    def test_BinaryField(self):
        deserialized = "Álvaro".encode("utf-8")
        serialized = b64encode(deserialized).decode("ascii")

        assert type(deserialized) == BINARY_TYPE
        assert type(serialized) == TEXT_TYPE

        assert fields.BinaryField.TYPE == (bytes,)
        assert fields.BinaryField.serialize(None) == ""
        assert type(fields.BinaryField.serialize(None)) is TEXT_TYPE
        assert fields.BinaryField.serialize(deserialized) == serialized
        assert type(fields.BinaryField.serialize(deserialized)) is TEXT_TYPE
        with self.assertRaises(ValueError):
            fields.BinaryField.serialize(42)
        with self.assertRaises(ValueError):
            fields.BinaryField.serialize(3.14)
        with self.assertRaises(ValueError):
            fields.BinaryField.serialize("Álvaro")
        with self.assertRaises(ValueError):
            fields.BinaryField.serialize("123")

        assert fields.BinaryField.deserialize(None) is b""
        assert fields.BinaryField.deserialize(serialized) == deserialized
        assert type(fields.BinaryField.deserialize(serialized)) is BINARY_TYPE
        with self.assertRaises(ValueError):
            fields.BinaryField.deserialize(42)
        with self.assertRaises(ValueError):
            fields.BinaryField.deserialize(3.14)
        with self.assertRaises(ValueError):
            fields.BinaryField.deserialize("Álvaro")

        assert fields.BinaryField.deserialize(deserialized) == deserialized
        assert fields.BinaryField.deserialize(serialized) == deserialized
        assert fields.BinaryField.deserialize(serialized.encode("ascii")) == serialized.encode("ascii")

    def test_BoolField(self):
        assert fields.BoolField.TYPE == (bool,)
        assert fields.BoolField.serialize(None) == ""

        false_values = ("False", "false", "f", "no", False)
        for value in false_values:
            assert fields.BoolField.deserialize(value) is False

        assert fields.BoolField.deserialize(None) is None
        assert fields.BoolField.deserialize("") is None

        true_values = ("True", "true", "t", "yes", True)
        for value in true_values:
            assert fields.BoolField.deserialize(value) is True

        assert fields.BoolField.serialize(False) == "false"
        assert type(fields.BoolField.serialize(False)) is TEXT_TYPE

        assert fields.BoolField.serialize(True) == "true"
        assert type(fields.BoolField.serialize(True)) is TEXT_TYPE

        # '0' and '1' should be not accepted as boolean values because the
        # sample could not contain other integers but the actual type could be
        # integer
        with self.assertRaises(ValueError):
            fields.BoolField.deserialize("0")
        with self.assertRaises(ValueError):
            fields.BoolField.deserialize(b"0")
        with self.assertRaises(ValueError):
            fields.BoolField.deserialize("1")
        with self.assertRaises(ValueError):
            fields.BoolField.deserialize(b"1")

    def test_IntegerField(self):
        assert fields.IntegerField.TYPE == (int,)
        assert fields.IntegerField.serialize(None) == ""
        assert type(fields.IntegerField.serialize(None)) is TEXT_TYPE
        assert type(fields.IntegerField.deserialize("42")) in fields.IntegerField.TYPE
        assert fields.IntegerField.deserialize("42") == 42
        assert fields.IntegerField.deserialize(42) == 42
        assert fields.IntegerField.serialize(42) == "42"
        assert type(fields.IntegerField.serialize(42)) is TEXT_TYPE
        assert fields.IntegerField.deserialize(None) is None
        assert fields.IntegerField.deserialize("10152709355006317") == 10152709355006317

        with rows.locale_context(locale_name):
            assert fields.IntegerField.serialize(42000) == "42000"
            assert type(fields.IntegerField.serialize(42000)) is TEXT_TYPE
            assert fields.IntegerField.serialize(42000, grouping=True) == "42.000"
            assert fields.IntegerField.deserialize("42.000") == 42000
            assert fields.IntegerField.deserialize(42) == 42
            assert fields.IntegerField.deserialize(42.0) == 42

        with self.assertRaises(ValueError):
            fields.IntegerField.deserialize(1.23)

        assert fields.IntegerField.deserialize("       42") == 42
        assert fields.IntegerField.deserialize("42       ") == 42
        assert fields.IntegerField.deserialize("042") == 42
        assert fields.IntegerField.deserialize("0") == 0

    def test_FloatField(self):
        assert fields.FloatField.TYPE == (float,)
        assert fields.FloatField.serialize(None) == ""
        assert type(fields.FloatField.serialize(None)) is TEXT_TYPE
        assert type(fields.FloatField.deserialize("42.0")) in fields.FloatField.TYPE
        assert fields.FloatField.deserialize("42.0") == 42.0
        assert fields.FloatField.deserialize(42.0) == 42.0
        assert fields.FloatField.deserialize(42) == 42.0
        assert fields.FloatField.deserialize(None) is None
        assert fields.FloatField.serialize(42.0) == "42.0"
        assert type(fields.FloatField.serialize(42.0)) is TEXT_TYPE

        with rows.locale_context(locale_name):
            assert fields.FloatField.serialize(42000.0), "42000 == 000000"
            assert type(fields.FloatField.serialize(42000.0)) is TEXT_TYPE
            assert fields.FloatField.serialize(42000, grouping=True) == "42.000,000000"
            assert fields.FloatField.deserialize("42.000,00") == 42000.0
            assert fields.FloatField.deserialize(42) == 42.0
            assert fields.FloatField.deserialize(42.0) == 42.0

    def test_DecimalField(self):
        deserialized = Decimal("42.010")
        assert fields.DecimalField.TYPE == (Decimal,)
        assert fields.DecimalField.serialize(None) == ""
        assert type(fields.DecimalField.serialize(None)) is TEXT_TYPE
        assert fields.DecimalField.deserialize("") is None
        assert type(fields.DecimalField.deserialize("42.0")) in fields.DecimalField.TYPE
        assert fields.DecimalField.deserialize("42.0") == Decimal("42.0")
        assert fields.DecimalField.deserialize(deserialized) == deserialized
        assert fields.DecimalField.serialize(deserialized) == "42.010"
        assert type(fields.DecimalField.serialize(deserialized)) == TEXT_TYPE
        assert fields.DecimalField.deserialize("21.21657469231") == Decimal("21.21657469231")
        assert fields.DecimalField.deserialize("-21.34") == Decimal("-21.34")
        assert fields.DecimalField.serialize(Decimal("-21.34")) == "-21.34"
        assert fields.DecimalField.deserialize(None) is None

        with rows.locale_context(locale_name):
            assert TEXT_TYPE == type(fields.DecimalField.serialize(deserialized))
            assert fields.DecimalField.serialize(Decimal("4200")) == "4200"
            assert fields.DecimalField.serialize(Decimal("42.0")), "42 == 0"
            assert fields.DecimalField.serialize(Decimal("42000.0")), "42000 == 0"
            assert fields.DecimalField.serialize(Decimal("-42.0")), "-42 == 0"
            assert fields.DecimalField.deserialize("42.000,00") == Decimal("42000.00")
            assert fields.DecimalField.deserialize("-42.000,00") == Decimal("-42000.00")
            assert fields.DecimalField.serialize(Decimal("42000.0"), grouping=True) == "42.000,0"
            assert fields.DecimalField.deserialize(42000) == Decimal("42000")
            assert fields.DecimalField.deserialize(42000.0) == Decimal("42000")

    def test_PercentField(self):
        deserialized = Decimal("0.42010")
        assert fields.PercentField.TYPE == (Decimal,)
        assert type(fields.PercentField.deserialize("42.0%")) in fields.PercentField.TYPE
        assert fields.PercentField.deserialize("42.0%") == Decimal("0.420")
        assert fields.PercentField.deserialize(Decimal("0.420")) == Decimal("0.420")
        assert fields.PercentField.deserialize(deserialized) == deserialized
        assert fields.PercentField.deserialize(None) is None
        assert fields.PercentField.serialize(deserialized) == "42.010%"
        assert type(fields.PercentField.serialize(deserialized)) == TEXT_TYPE
        assert fields.PercentField.serialize(Decimal("42.010")) == "4201.0%"
        assert fields.PercentField.serialize(Decimal("0")) == "0.00%"
        assert fields.PercentField.serialize(None) == ""
        assert fields.PercentField.serialize(Decimal("0.01")) == "1%"
        with rows.locale_context(locale_name):
            assert type(fields.PercentField.serialize(deserialized)) == TEXT_TYPE
            assert fields.PercentField.serialize(Decimal("42.0")) == "4200%"
            assert fields.PercentField.serialize(Decimal("42000.0")) == "4200000%"
            assert fields.PercentField.deserialize("42.000,00%") == Decimal("420.0000")
            assert fields.PercentField.serialize(Decimal("42000.00"), grouping=True) == "4.200.000%"
        with self.assertRaises(ValueError):
            fields.PercentField.deserialize(42)

    def test_DateField(self):
        # TODO: test timezone-aware datetime.date
        serialized = "2015-05-27"
        deserialized = datetime.date(2015, 5, 27)
        assert fields.DateField.TYPE == (datetime.date,)
        assert fields.DateField.serialize(None) == ""
        assert type(fields.DateField.serialize(None)) is TEXT_TYPE
        assert type(fields.DateField.deserialize(serialized)) in fields.DateField.TYPE
        assert fields.DateField.deserialize(serialized) == deserialized
        assert fields.DateField.deserialize(deserialized) == deserialized
        assert fields.DateField.deserialize(None) is None
        assert fields.DateField.deserialize("") is None
        assert fields.DateField.serialize(deserialized) == serialized
        assert type(fields.DateField.serialize(deserialized)) is TEXT_TYPE
        with self.assertRaises(ValueError):
            fields.DateField.deserialize(42)
        with self.assertRaises(ValueError):
            fields.DateField.deserialize(serialized + "T00:00:00")
        with self.assertRaises(ValueError):
            fields.DateField.deserialize("Álvaro")
        with self.assertRaises(ValueError):
            fields.DateField.deserialize(serialized.encode("utf-8"))

    def test_DatetimeField(self):
        # TODO: test timezone-aware datetime.date
        serialized = "2015-05-27T01:02:03"
        assert fields.DatetimeField.TYPE == (datetime.datetime,)
        deserialized = fields.DatetimeField.deserialize(serialized)
        assert type(deserialized) in fields.DatetimeField.TYPE
        assert fields.DatetimeField.serialize(None) == ""
        assert type(fields.DatetimeField.serialize(None)) is TEXT_TYPE

        value = datetime.datetime(2015, 5, 27, 1, 2, 3)
        assert fields.DatetimeField.deserialize(serialized) == value
        assert fields.DatetimeField.deserialize(deserialized) == deserialized
        assert fields.DatetimeField.deserialize(None) is None
        assert fields.DatetimeField.serialize(value) == serialized
        assert type(fields.DatetimeField.serialize(value)) is TEXT_TYPE
        with self.assertRaises(ValueError):
            fields.DatetimeField.deserialize(42)
        with self.assertRaises(ValueError):
            fields.DatetimeField.deserialize("2015-01-01")
        with self.assertRaises(ValueError):
            fields.DatetimeField.deserialize("Álvaro")
        with self.assertRaises(ValueError):
            fields.DatetimeField.deserialize(serialized.encode("utf-8"))

    def test_EmailField(self):
        # TODO: accept spaces also
        serialized = "test@domain.com"
        assert fields.EmailField.TYPE == (TEXT_TYPE,)
        deserialized = fields.EmailField.deserialize(serialized)
        assert type(deserialized) in fields.EmailField.TYPE
        assert fields.EmailField.serialize(None) == ""
        assert type(fields.EmailField.serialize(None)) is TEXT_TYPE

        assert fields.EmailField.serialize(serialized) == serialized
        assert fields.EmailField.deserialize(serialized) == serialized
        assert fields.EmailField.deserialize(None) is None
        assert fields.EmailField.deserialize("") is None
        assert type(fields.EmailField.serialize(serialized)) is TEXT_TYPE

        with self.assertRaises(ValueError):
            fields.EmailField.deserialize(42)
        with self.assertRaises(ValueError):
            fields.EmailField.deserialize("2015-01-01")
        with self.assertRaises(ValueError):
            fields.EmailField.deserialize("Álvaro")
        with self.assertRaises(ValueError):
            fields.EmailField.deserialize("test@example.com".encode("utf-8"))

    def test_TextField(self):
        assert fields.TextField.TYPE == (TEXT_TYPE,)
        assert fields.TextField.serialize(None) == ""
        assert type(fields.TextField.serialize(None)) is TEXT_TYPE
        assert type(fields.TextField.deserialize("test")) in fields.TextField.TYPE

        assert fields.TextField.deserialize("Álvaro") == "Álvaro"
        assert fields.TextField.deserialize(None) is None
        assert fields.TextField.deserialize("") is ""
        assert fields.TextField.serialize("Álvaro") == "Álvaro"
        assert type(fields.TextField.serialize("Álvaro")) is TEXT_TYPE

        with self.assertRaises(ValueError) as exception_context:
            fields.TextField.deserialize("Álvaro".encode("utf-8"))
        assert exception_context.exception.args[0] == "Binary is not supported"

    def test_JSONField(self):
        assert fields.JSONField.TYPE == (list, dict)
        assert type(fields.JSONField.deserialize("[]")) == list
        assert type(fields.JSONField.deserialize("{}")) == dict

        deserialized = {"a": 123, "b": 3.14, "c": [42, 24]}
        serialized = json.dumps(deserialized)
        assert fields.JSONField.deserialize(serialized) == deserialized

    def test_UUIDField(self):
        with self.assertRaises(ValueError) as exception_context:
            fields.UUIDField.deserialize("not an UUID value")
        with self.assertRaises(ValueError) as exception_context:
            # "z" not hex
            fields.UUIDField.deserialize("z" * 32)

        fields.UUIDField.deserialize("a" * 32)  # no exception should be raised

        data = uuid.uuid4()
        assert fields.UUIDField.deserialize(data) == data
        assert fields.UUIDField.deserialize(TEXT_TYPE(data)) == data
        assert fields.UUIDField.deserialize(TEXT_TYPE(data).replace("-", "")) == data


class FieldUtilsTestCase(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        with open("tests/data/all-field-types.csv", "rb") as fobj:
            data = fobj.read().decode("utf-8")
        lines = [line.split(",") for line in data.splitlines()]

        self.fields = lines[0]
        self.data = lines[1:]
        self.expected = {
            "bool_column": fields.BoolField,
            "integer_column": fields.IntegerField,
            "float_column": fields.FloatField,
            "decimal_column": fields.FloatField,
            "percent_column": fields.PercentField,
            "date_column": fields.DateField,
            "datetime_column": fields.DatetimeField,
            "unicode_column": fields.TextField,
        }

    def test_slug(self):
        assert fields.slug(None) == ""
        assert fields.slug("Álvaro Justen") == "alvaro_justen"
        assert fields.slug("Moe's Bar") == "moe_s_bar"
        assert fields.slug("-----te-----st------") == "te_st"
        assert fields.slug("first line\nsecond line") == "first_line_second_line"
        assert fields.slug("first/second") == "first_second"
        assert fields.slug("first\xa0second") == "first_second"
        # As in <https://github.com/turicas/rows/issues/179>
        assert fields.slug('Query Occurrence"( % ),"First Seen') == "query_occurrence_first_seen"
        assert fields.slug(" ÁLVARO  justen% ") == "alvaro_justen"
        assert fields.slug(42) == "42"

        assert fields.slug("^test") == "test"
        assert fields.slug("^test", permitted_chars=fields.SLUG_CHARS + "^") == "^test"

        assert fields.slug("this/is\ta\ntest", separator="-") == "this-is-a-test"

    def test_camel_to_snake(self):
        assert fields.camel_to_snake(None) == ""
        assert fields.camel_to_snake("myFieldName") == "my_field_name"
        assert fields.camel_to_snake("MyFieldName") == "my_field_name"
        assert fields.camel_to_snake("TheHTTPLink") == "the_http_link"
        assert fields.camel_to_snake("TheHTTPURL") == "the_httpurl"
        assert fields.camel_to_snake("First\xa0second") == "first_second"
        assert fields.camel_to_snake("this/is\ta\ntest") == "this_is_a_test"

    def test_make_header_should_add_underscore_if_starts_with_number(self):
        result = fields.make_header(["123", "456", "123"])
        expected_result = ["field_123", "field_456", "field_123_2"]
        assert result == expected_result

    def test_make_header_should_not_ignore_permit_not(self):
        result = fields.make_header(["abc", "^qwe", "rty"], permit_not=True)
        expected_result = ["abc", "^qwe", "rty"]
        assert result == expected_result

    def test_make_header_prefix(self):
        result = fields.make_header(["abc", "123"])
        expected_result = ["abc", "field_123"]
        assert result == expected_result

        result = fields.make_header(["abc", "123"], prefix="table_")
        expected_result = ["abc", "table_123"]
        assert result == expected_result

    def test_make_header_max_size(self):
        result = fields.make_header(["test", "another test", "another string"], max_size=8)
        expected_result = ["test", "another", "anothe_2"]
        assert result == expected_result

    def test_make_header_python_keywords(self):
        result = fields.make_header(["def", "try", "if", "for", "while", "def"], max_size=8)
        expected = ["def_1", "try_1", "if_1", "for_1", "while_1", "def_2"]
        assert result == expected

    def test_detect_types_no_sample(self):
        expected = {key: fields.TextField for key in self.expected.keys()}
        result = fields.detect_types(self.fields, [])
        self.assertDictEqual(dict(result), expected)

    def test_detect_types_binary(self):

        # first, try values as (`bytes`/`str`)
        expected = {key: fields.BinaryField for key in self.expected.keys()}
        values = [
            [b"some binary data" for _ in range(len(self.data[0]))] for __ in range(20)
        ]
        result = fields.detect_types(self.fields, values)
        self.assertDictEqual(dict(result), expected)

        # second, try base64-encoded values (as `str`/`unicode`)
        expected = {key: fields.TextField for key in self.expected.keys()}
        values = [
            [b64encode(value.encode("utf-8")).decode("ascii") for value in row]
            for row in self.data
        ]
        result = fields.detect_types(self.fields, values)
        self.assertDictEqual(dict(result), expected)

    def test_detect_types(self):
        result = fields.detect_types(self.fields, self.data)
        self.assertDictEqual(dict(result), self.expected)

    def test_detect_types_different_number_of_fields(self):
        result = fields.detect_types(["f1", "f2"], [["a", "b", "c"]])
        assert list(result.keys()) == ["f1", "f2", "field_2"]

    def test_empty_sequences_should_not_be_bool(self):
        result = fields.detect_types(["field_1"], [[""], [""]])["field_1"]
        expected = fields.TextField
        assert result == expected

    # TODO: add tests for `TypeDetector` using many kinds of unhashable objects

    def test_precedence(self):
        field_types = [
            ("bool", fields.BoolField),
            ("integer", fields.IntegerField),
            ("float", fields.FloatField),
            ("datetime", fields.DatetimeField),
            ("date", fields.DateField),
            ("float", fields.FloatField),
            ("percent", fields.PercentField),
            ("json", fields.JSONField),
            ("email", fields.EmailField),
            ("binary1", fields.BinaryField),
            ("binary2", fields.BinaryField),
            ("text", fields.TextField),
        ]
        data = [
            [
                "false",
                "42",
                "3.14",
                "2016-08-15T05:21:10",
                "2016-08-15",
                "2.71",
                "76.38%",
                '{"key": "value"}',
                "test@example.com",
                b"cHl0aG9uIHJ1bGVz",
                b"python rules",
                "Álvaro Justen",
            ]
        ]
        result = fields.detect_types(
            [item[0] for item in field_types],
            data,
            field_types=[item[1] for item in field_types],
        )
        self.assertDictEqual(dict(result), dict(field_types))

    def test_detect_types_integer_with_leading_zeroes(self):
        result = fields.detect_types(
            ["month", "document"],
            [["%02d" % x, "%09d" % (x * 1000)] for x in range(1, 13)]
        )
        expected = {
            "month": fields.IntegerField,
            "document": fields.IntegerField,
        }
        self.assertDictEqual(result, expected)

    def test_type_deserialize_cache(self):
        from rows.fields import _deserialization_error, cached_type_deserialize
        fields._deserialization_cache = {}
        len_before = 0

        # If `Field.deserialize` raises an exception, it should not be cached
        assert cached_type_deserialize(fields.BoolField, "xxx", true_behavior=False) is _deserialization_error
        assert len(fields._deserialization_cache) == len_before
        assert cached_type_deserialize(fields.IntegerField, "xxx", true_behavior=False) is _deserialization_error
        assert len(fields._deserialization_cache) == len_before

        # Values which result in `hash(value) == 0` must not be confused if from different types
        types_values = [
            (fields.BoolField, False),
            (fields.IntegerField, 0),
            (fields.FloatField, 0.0),
            (fields.TextField, ""),
            (fields.UUIDField, uuid.UUID(int=0)),
        ]
        len_expected = len_before
        for type_, value in types_values:
            assert cached_type_deserialize(type_, value, true_behavior=False) == value
            len_expected += 1
            assert len(fields._deserialization_cache) == len_expected
        for type_, value in types_values:
            for other_type, other_value in types_values:
                if type_ == other_type or value == other_value:  # Skip equal types and 0 vs 0.0
                    continue
                assert (
                    cached_type_deserialize(type_, value, true_behavior=False) !=
                    cached_type_deserialize(type_, other_value, true_behavior=False)
                )


class FieldsFunctionsTestCase(unittest.TestCase):
    def test_is_null(self):
        assert fields.is_null(None)
        assert fields.is_null("")
        assert fields.is_null(" \t ")
        assert fields.is_null("null")
        assert fields.is_null("nil")
        assert fields.is_null("none")
        assert fields.is_null("-")

        self.assertFalse(fields.is_null("Álvaro"))
        self.assertFalse(fields.is_null("Álvaro".encode("utf-8")))

    def test_as_string(self):
        assert fields.as_string(None) == "None"
        assert fields.as_string(42) == "42"
        assert fields.as_string(3.141592) == "3.141592"
        assert fields.as_string("Álvaro") == "Álvaro"

        with self.assertRaises(ValueError) as exception_context:
            fields.as_string("Álvaro".encode("utf-8"))
        assert exception_context.exception.args[0] == "Binary is not supported"

    def test_get_items(self):
        func = fields.get_items(2)
        assert func("a b c d e f".split()) == ("c",)

        func = fields.get_items(0, 2, 3)
        assert func("a b c d e f".split()) == ("a", "c", "d")
        assert func("a b c".split()) == ("a", "c", None)
