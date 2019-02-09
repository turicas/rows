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

import binascii
import datetime
import json
import locale
import re
from base64 import b64decode, b64encode
from collections import OrderedDict, defaultdict
from decimal import Decimal, InvalidOperation
from unicodedata import normalize

import six

if six.PY2:
    from itertools import izip_longest as zip_longest
else:
    from itertools import zip_longest


# Order matters here
__all__ = [
    "BoolField",
    "IntegerField",
    "FloatField",
    "DatetimeField",
    "DateField",
    "DecimalField",
    "PercentField",
    "JSONField",
    "EmailField",
    "TextField",
    "BinaryField",
    "Field",
]
NULL = ("-", "null", "none", "nil", "n/a", "na")
NULL_BYTES = (b"-", b"null", b"none", b"nil", b"n/a", b"na")
REGEXP_ONLY_NUMBERS = re.compile("[^0-9\-]")
SHOULD_NOT_USE_LOCALE = True  # This variable is changed by rows.locale_manager
SLUG_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_"


def value_error(value, cls):
    value = repr(value)
    if len(value) > 50:
        value = value[:50] + "..."
    raise ValueError("Value '{}' can't be {}".format(value, cls.__name__))


class Field(object):
    """Base Field class - all fields should inherit from this

    As the fallback for all other field types are the BinaryField, this Field
    actually implements what is expected in the BinaryField
    """

    TYPE = (type(None),)

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        """Serialize a value to be exported

        `cls.serialize` should always return an unicode value, except for
        BinaryField
        """

        if value is None:
            value = ""
        return value

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        """Deserialize a value just after importing it

        `cls.deserialize` should always return a value of type `cls.TYPE` or
        `None`.
        """

        if isinstance(value, cls.TYPE):
            return value
        elif is_null(value):
            return None
        else:
            return value


class BinaryField(Field):
    """Field class to represent byte arrays

    Is not locale-aware (does not need to be)
    """

    TYPE = (six.binary_type,)

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is not None:
            if not isinstance(value, six.binary_type):
                value_error(value, cls)
            else:
                try:
                    return b64encode(value).decode("ascii")
                except (TypeError, binascii.Error):
                    return value
        else:
            return ""

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        if value is not None:
            if isinstance(value, six.binary_type):
                return value
            elif isinstance(value, six.text_type):
                try:
                    return b64decode(value)
                except (TypeError, ValueError, binascii.Error):
                    raise ValueError("Can't decode base64")
            else:
                value_error(value, cls)
        else:
            return b""


class BoolField(Field):
    """Base class to representing boolean

    Is not locale-aware (if you need to, please customize by changing its
    attributes like `TRUE_VALUES` and `FALSE_VALUES`)
    """

    TYPE = (bool,)
    SERIALIZED_VALUES = {True: "true", False: "false", None: ""}
    TRUE_VALUES = ("true", "yes")
    FALSE_VALUES = ("false", "no")

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        # TODO: should we serialize `None` as well or give it to the plugin?
        return cls.SERIALIZED_VALUES[value]

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(BoolField, cls).deserialize(value)
        if value is None or isinstance(value, cls.TYPE):
            return value

        value = as_string(value).lower()
        if value in cls.TRUE_VALUES:
            return True
        elif value in cls.FALSE_VALUES:
            return False
        else:
            raise ValueError("Value is not boolean")


class IntegerField(Field):
    """Field class to represent integer

    Is locale-aware
    """

    TYPE = (int,)

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ""

        if SHOULD_NOT_USE_LOCALE:
            return six.text_type(value)
        else:
            grouping = kwargs.get("grouping", None)
            return locale.format("%d", value, grouping=grouping)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(IntegerField, cls).deserialize(value)
        if value is None or isinstance(value, cls.TYPE):
            return value
        elif isinstance(value, float):
            new_value = int(value)
            if new_value != value:
                raise ValueError("It's float, not integer")
            else:
                value = new_value

        value = as_string(value)
        return int(value) if SHOULD_NOT_USE_LOCALE else locale.atoi(value)


class FloatField(Field):
    """Field class to represent float

    Is locale-aware
    """

    TYPE = (float,)

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ""

        if SHOULD_NOT_USE_LOCALE:
            return six.text_type(value)
        else:
            grouping = kwargs.get("grouping", None)
            return locale.format("%f", value, grouping=grouping)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(FloatField, cls).deserialize(value)
        if value is None or isinstance(value, cls.TYPE):
            return value

        value = as_string(value)
        if SHOULD_NOT_USE_LOCALE:
            return float(value)
        else:
            return locale.atof(value)


class DecimalField(Field):
    """Field class to represent decimal data (as Python's decimal.Decimal)

    Is locale-aware
    """

    TYPE = (Decimal,)

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ""

        value_as_string = six.text_type(value)
        if SHOULD_NOT_USE_LOCALE:
            return value_as_string
        else:
            grouping = kwargs.get("grouping", None)
            has_decimal_places = value_as_string.find(".") != -1
            if not has_decimal_places:
                string_format = "%d"
            else:
                decimal_places = len(value_as_string.split(".")[1])
                string_format = "%.{}f".format(decimal_places)
            return locale.format(string_format, value, grouping=grouping)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(DecimalField, cls).deserialize(value)
        if value is None or isinstance(value, cls.TYPE):
            return value
        elif type(value) in (int, float):
            return Decimal(six.text_type(value))

        if SHOULD_NOT_USE_LOCALE:
            try:
                return Decimal(value)
            except InvalidOperation:
                value_error(value, cls)
        else:
            locale_vars = locale.localeconv()
            decimal_separator = locale_vars["decimal_point"]
            interesting_vars = (
                "decimal_point",
                "mon_decimal_point",
                "mon_thousands_sep",
                "negative_sign",
                "positive_sign",
                "thousands_sep",
            )
            chars = (
                locale_vars[x].replace(".", r"\.").replace("-", r"\-")
                for x in interesting_vars
            )
            interesting_chars = "".join(set(chars))
            regexp = re.compile(r"[^0-9{} ]".format(interesting_chars))
            value = as_string(value)
            if regexp.findall(value):
                value_error(value, cls)

            parts = [
                REGEXP_ONLY_NUMBERS.subn("", number)[0]
                for number in value.split(decimal_separator)
            ]
            if len(parts) > 2:
                raise ValueError("Can't deserialize with this locale.")
            try:
                value = Decimal(parts[0])
                if len(parts) == 2:
                    decimal_places = len(parts[1])
                    value = value + (Decimal(parts[1]) / (10 ** decimal_places))
            except InvalidOperation:
                value_error(value, cls)
            return value


class PercentField(DecimalField):
    """Field class to represent percent values

    Is locale-aware (inherit this behaviour from `rows.DecimalField`)
    """

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ""
        elif value == Decimal("0"):
            return "0.00%"

        value = Decimal(six.text_type(value * 100)[:-2])
        value = super(PercentField, cls).serialize(value, *args, **kwargs)
        return "{}%".format(value)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        if isinstance(value, cls.TYPE):
            return value
        elif is_null(value):
            return None

        value = as_string(value)
        if "%" not in value:
            value_error(value, cls)
        value = value.replace("%", "")
        return super(PercentField, cls).deserialize(value) / 100


class DateField(Field):
    """Field class to represent date

    Is not locale-aware (does not need to be)
    """

    TYPE = (datetime.date,)
    INPUT_FORMAT = "%Y-%m-%d"
    OUTPUT_FORMAT = "%Y-%m-%d"

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ""

        return six.text_type(value.strftime(cls.OUTPUT_FORMAT))

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(DateField, cls).deserialize(value)
        if value is None or isinstance(value, cls.TYPE):
            return value

        value = as_string(value)

        dt_object = datetime.datetime.strptime(value, cls.INPUT_FORMAT)
        return datetime.date(dt_object.year, dt_object.month, dt_object.day)


class DatetimeField(Field):
    """Field class to represent date-time

    Is not locale-aware (does not need to be)
    """

    TYPE = (datetime.datetime,)
    DATETIME_REGEXP = re.compile(
        "^([0-9]{4})-([0-9]{2})-([0-9]{2})[ T]" "([0-9]{2}):([0-9]{2}):([0-9]{2})$"
    )

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ""

        return six.text_type(value.isoformat())

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(DatetimeField, cls).deserialize(value)
        if value is None or isinstance(value, cls.TYPE):
            return value

        value = as_string(value)
        # TODO: may use iso8601
        groups = cls.DATETIME_REGEXP.findall(value)
        if not groups:
            value_error(value, cls)
        else:
            return datetime.datetime(*[int(x) for x in groups[0]])


class TextField(Field):
    """Field class to represent unicode strings

    Is not locale-aware (does not need to be)
    """

    TYPE = (six.text_type,)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        if value is None or isinstance(value, cls.TYPE):
            return value
        else:
            return as_string(value)


class EmailField(TextField):
    """Field class to represent e-mail addresses

    Is not locale-aware (does not need to be)
    """

    EMAIL_REGEXP = re.compile(
        r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]+$", flags=re.IGNORECASE
    )

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ""

        return six.text_type(value)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(EmailField, cls).deserialize(value)
        if value is None or not value.strip():
            return None

        result = cls.EMAIL_REGEXP.findall(value)
        if not result:
            value_error(value, cls)
        else:
            return result[0]


class JSONField(Field):
    """Field class to represent JSON-encoded strings

    Is not locale-aware (does not need to be)
    """

    TYPE = (list, dict)

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        return json.dumps(value)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(JSONField, cls).deserialize(value)
        if value is None or isinstance(value, cls.TYPE):
            return value
        else:
            return json.loads(value)


def as_string(value):
    if isinstance(value, six.binary_type):
        raise ValueError("Binary is not supported")
    elif isinstance(value, six.text_type):
        return value
    else:
        return six.text_type(value)


def is_null(value):
    if value is None:
        return True
    elif type(value) is six.binary_type:
        value = value.strip().lower()
        return not value or value in NULL_BYTES
    else:
        value_str = as_string(value).strip().lower()
        return not value_str or value_str in NULL


def unique_values(values):
    result = []
    for value in values:
        if not is_null(value) and value not in result:
            result.append(value)
    return result


def get_items(*indexes):
    """Return a callable that fetches the given indexes of an object
    Always return a tuple even when len(indexes) == 1.

    Similar to `operator.itemgetter`, but will insert `None` when the object
    does not have the desired index (instead of raising IndexError).
    """
    return lambda obj: tuple(
        obj[index] if len(obj) > index else None for index in indexes
    )


def slug(text, separator="_", permitted_chars=SLUG_CHARS, replace_with_separator=" -_"):
    """Generate a slug for the `text`.

    >>> slug(' ÁLVARO  justen% ')
    'alvaro_justen'
    >>> slug(' ÁLVARO  justen% ', separator='-')
    'alvaro-justen'
    """

    text = six.text_type(text or "")

    # Strip non-ASCII characters
    # Example: u' ÁLVARO  justen% ' -> ' ALVARO  justen% '
    text = normalize("NFKD", text.strip()).encode("ascii", "ignore").decode("ascii")

    # Replace spaces and other chars with separator
    # Example: u' ALVARO  justen% ' -> u'_ALVARO__justen%_'
    for char in replace_with_separator:
        text = text.replace(char, separator)

    # Remove non-permitted characters and put everything to lowercase
    # Example: u'_ALVARO__justen%_' -> u'_alvaro__justen_'
    text = "".join(char for char in text if char in permitted_chars).lower()

    # Remove double occurrencies of separator
    # Example: u'_alvaro__justen_' -> u'_alvaro_justen_'
    double_separator = separator + separator
    while double_separator in text:
        text = text.replace(double_separator, separator)

    # Strip separators
    # Example: u'_alvaro_justen_' -> u'alvaro_justen'
    return text.strip(separator)


def make_unique_name(name, existing_names, name_format="{name}_{index}", start=2):
    """Return a unique name based on `name_format` and `name`."""
    index = start
    new_name = name
    while new_name in existing_names:
        new_name = name_format.format(name=name, index=index)
        index += 1

    return new_name


def make_header(field_names, permit_not=False):
    """Return unique and slugged field names."""
    slug_chars = SLUG_CHARS if not permit_not else SLUG_CHARS + "^"

    header = [
        slug(field_name, permitted_chars=slug_chars) for field_name in field_names
    ]
    result = []
    for index, field_name in enumerate(header):
        if not field_name:
            field_name = "field_{}".format(index)
        elif field_name[0].isdigit():
            field_name = "field_{}".format(field_name)

        if field_name in result:
            field_name = make_unique_name(
                name=field_name, existing_names=result, start=2
            )
        result.append(field_name)

    return result


DEFAULT_TYPES = (
    BoolField,
    IntegerField,
    FloatField,
    DecimalField,
    PercentField,
    DecimalField,
    DatetimeField,
    DateField,
    JSONField,
    TextField,
    BinaryField,
)


class TypeDetector(object):
    """Detect data types based on a list of Field classes"""

    def __init__(
        self,
        field_names=None,
        field_types=DEFAULT_TYPES,
        fallback_type=TextField,
        skip_indexes=None,
    ):
        self.field_names = field_names or []
        self.field_types = list(field_types)
        self.fallback_type = fallback_type
        self._possible_types = defaultdict(lambda: list(self.field_types))
        self._samples = []
        self._skip = skip_indexes or tuple()

    def check_type(self, index, value):
        for type_ in self._possible_types[index][:]:
            try:
                type_.deserialize(value)
            except (ValueError, TypeError):
                self._possible_types[index].remove(type_)

    def process_row(self, row):
        for index, value in enumerate(row):
            if index in self._skip:
                continue
            self.check_type(index, value)

    def feed(self, data):
        for row in data:
            self.process_row(row)

    def priority(self, *field_types):
        """Decide the priority between each possible type"""

        return field_types[0] if field_types else self.fallback_type

    @property
    def fields(self):
        possible, skip = self._possible_types, self._skip

        if possible:
            # Create a header with placeholder values for each detected column
            # and then join this placeholders with original header - the
            # original header may have less columns then the detected ones, so
            # we end with a full header having a name for every possible
            # column.
            placeholders = make_header(range(max(possible.keys()) + 1))
            header = [a or b for a, b in zip_longest(self.field_names, placeholders)]
        else:
            header = self.field_names

        return OrderedDict(
            [
                (
                    field_name,
                    self.priority(*(possible[index] if index in possible else [])),
                )
                for index, field_name in enumerate(header)
                if index not in skip
            ]
        )


def detect_types(
    field_names,
    field_values,
    field_types=DEFAULT_TYPES,
    skip_indexes=None,
    type_detector=TypeDetector,
    fallback_type=TextField,
    *args,
    **kwargs
):
    """Detect column types (or "where the magic happens")"""

    # TODO: look strategy of csv.Sniffer.has_header
    # TODO: may receive 'type hints'
    detector = type_detector(
        field_names,
        field_types=field_types,
        fallback_type=fallback_type,
        skip_indexes=skip_indexes,
    )
    detector.feed(field_values)
    return detector.fields


def identify_type(value):
    """Identify the field type for a specific value"""

    return detect_types(["name"], [[value]])["name"]
