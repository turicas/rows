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
import datetime
import uuid

from rows.compat import BINARY_TYPE, ORDERED_DICT, PYTHON_VERSION, TEXT_TYPE
from rows import fields as rows_fields


DESERIALIZATION_ERROR = object()
DEFAULT_TYPES = rows_fields.DEFAULT_TYPES
is_null = rows_fields.is_null
TextField = rows_fields.TextField
make_header = rows_fields.make_header


class ColumnTypeDetector(object):
    """Type detector for one column with internal LFU cache for deserialization and stats of values"""

    _cacheable_types = (
        TEXT_TYPE, BINARY_TYPE, int, float, bool, type(None), datetime.date, datetime.datetime, uuid.UUID
    )

    def __init__(self, types=DEFAULT_TYPES, locale_config=None, cache_max_size=10000, cache_purge=9000):
        self._cache_max_size = cache_max_size
        self._cache_purge = cache_purge
        self._cache = {}
        self._possible_types = list(types)
        self._read_values = self._null_values = self._cache_hits = self._cache_misses = self._cache_unhashable = 0
        # TODO: implement everything `rows.utils.generate_schema` has and replace it with this class, unifying the
        # behavior
        # TODO: store min, max, min_length, max_length, choices when in "inference" mode
        self._locale_config = locale_config

    @property
    def stats(self):
        return {
            "read_values": self._read_values,
            "null_values": self._null_values,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_unhashable": self._cache_unhashable
        }

    def real_deserialize(self, value):
        type_ = self._possible_types[0]
        should_cache = isinstance(value, self._cacheable_types)
        cache_key = hash((type_, type(value), value, self._locale_config)) if should_cache else None
        cache = self._cache
        if not should_cache:
            self._cache_unhashable += 1
        if not should_cache or cache_key not in cache:
            result = type_.deserialize(value)
            if should_cache:
                cache[cache_key] = [result, 1]
                if len(cache) >= self._cache_max_size:
                    min_freq = cache[sorted(cache.keys(), key=lambda key: cache[key][1])[self._cache_purge]][1]
                    self._cache = cache = {k: v for k, v in cache.items() if v[1] > min_freq}
                self._cache_misses += 1
        else:
            result, _ = cache[cache_key]
            cache[cache_key][1] += 1
            self._cache_hits += 1
        return result

    def deserialize(self, type_, value, true_behavior=True):
        """
        Calls `type_.deserialize(value)`. When `true_behavior` is `True`, exception is raised if value can't be
        deserialized; returns `_deserialization_error` sentinel, otherwise.
        Will only cache values that can be hashed and on `_cacheable_types`.
        """
        # TODO: this should not be the "deserialize" method! The real deserialize must be when the type is already
        # defined. This one is for discovery.

        should_cache = isinstance(value, self._cacheable_types)
        cache_key = hash((type_, type(value), value, self._locale_config)) if should_cache else None
        cache = self._cache
        if not should_cache:
            self._cache_unhashable += 1
        if not should_cache or cache_key not in cache:
            try:
                result = type_.deserialize(value)
            except (ValueError, TypeError):
                if true_behavior:
                    raise
                return DESERIALIZATION_ERROR
            else:
                if should_cache:
                    cache[cache_key] = [result, 1]
                    if len(cache) >= self._cache_max_size:
                        min_freq = cache[sorted(cache.keys(), key=lambda key: cache[key][1])[self._cache_purge]][1]
                        self._cache = cache = {k: v for k, v in cache.items() if v[1] > min_freq}
                    self._cache_misses += 1
        else:
            result, _ = cache[cache_key]
            cache[cache_key][1] += 1
            self._cache_hits += 1
        return result

    # TODO: the behavior must be different when inferring type and when it's just serializing - regarding data storage
    # and the way it collects statistics

    def feed(self, values):
        deserialize, possible_types = self.deserialize, self._possible_types
        read_values, null_values = self._read_values, self._null_values
        unique_values = []
        for value in values:
            read_values += 1
            if is_null(value):
                null_values += 1
            if value not in unique_values:
                for type_ in possible_types.copy():
                    if deserialize(type_, value, true_behavior=False) is DESERIALIZATION_ERROR:
                        possible_types.remove(type_)
                unique_values.append(value)
        self._read_values, self._null_values = read_values, null_values

    @property
    def possible_types(self):
        return self._possible_types.copy()


class TypeDetector(object):
    """Detect data types based on a list of Field classes"""

    def __init__(
        self,
        field_names,
        field_types=DEFAULT_TYPES,
        fallback_type=TextField,
        skip_indexes=None,
    ):
        from collections import defaultdict

        self.field_names = list(field_names)
        self.field_types = list(field_types)
        self.fallback_type = fallback_type
        self._samples = []
        self._skip_indexes = skip_indexes or tuple()
        self._detectors = None

    # TODO: create two kinds of `feed`: by row and by column (some formats will have it by column)

    def set_types(self, fields):
        if self._detectors is None:
            from locale import getlocale

            locale_config = rows_fields.SHOULD_NOT_USE_LOCALE or getlocale()
            self._ncols = len(self.field_names)
            self._detectors = tuple([
                ColumnTypeDetector(types=self.field_types, locale_config=locale_config)
                for index in range(self._ncols)
            ])
        for field_name, field_type in fields.items():
            if field_name not in self.field_names:
                raise ValueError("Unknown field name: {}".format(repr(field_name)))
            self._detectors[self.field_names.index(field_name)]._possible_types = [field_type]

    def feed(self, data, batch_size=1024):
        if not isinstance(data, list):
            data = list(data)  # Must have all values in memory and indexable
        if not data:
            return
        first_row = data[0]
        indices = tuple([index for index in range(len(first_row)) if index not in self._skip_indexes])
        if not indices:
            return

        futures = []
        while data:
            if self._detectors is None:
                from locale import getlocale

                # On the first batch we get max row size to define the type detectors
                locale_config = rows_fields.SHOULD_NOT_USE_LOCALE or getlocale()
                self._ncols = max(len(self.field_names), max(len(row) for row in data[:batch_size]))
                self._detectors = tuple([
                    ColumnTypeDetector(types=self.field_types, locale_config=locale_config) if index in indices else None
                    for index in range(self._ncols)
                ])
            batch = data[:batch_size]
            for col_index in indices:
                self._detectors[col_index].feed([row[col_index] for row in batch])
            data = data[batch_size:]

    def priority(self, *field_types):
        """Decide the priority between each possible type"""

        return field_types[0] if field_types else self.fallback_type

    def _column_is_empty(self, index):
        stats = self._detectors[index].stats
        return stats["read_values"] > 0 and stats["null_values"] == stats["read_values"]

    def define_field_type(self, is_empty, possible_types):
        if is_empty:
            return self.fallback_type
        else:
            return self.priority(*possible_types)

    @property
    def fields(self):
        header = self.field_names
        if len(self.field_names) < len(self._detectors):
            if PYTHON_VERSION < (3, 0, 0):
                from itertools import izip_longest as zip_longest  # noqa
            else:
                from itertools import zip_longest  # noqa
            # Create a header with placeholder values for each detected column and then zip these placeholders with
            # original header - the original header may have less columns then the detected ones, so we end with a full
            # header having a name for every possible column.
            placeholders = make_header(range(len(self._detectors) + 1))
            header = [a or b for a, b in zip_longest(self.field_names, placeholders)]

        return ORDERED_DICT(
            [
                (
                    field_name,
                    self.define_field_type(
                        is_empty=self._column_is_empty(index),
                        possible_types=self._detectors[index].possible_types or [],
                    ),
                )
                for index, field_name in enumerate(header)
                if index not in self._skip_indexes
            ]
        )
