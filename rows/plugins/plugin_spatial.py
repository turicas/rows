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

import re
from struct import pack, unpack
from collections import namedtuple

from rows.compat import BINARY_TYPE

# TODO: move to just rows.spatial?

NUMBER_REGEXP = r"-?\s*[0-9]+(?:\.[0-9]+)?"
REGEXP_NEGATIVE_SIGN = re.compile(r"-\s+")
REGEXP_POINT_2D = re.compile(r"^\s*POINT\s*(\(.*\))\s*$")
REGEXP_POINTS_2D = re.compile(
    r"^\s*\(\s*"
    r"({0}\s+{0})".format(NUMBER_REGEXP)
    + "(.*)"
    + r"\s*\)\s*$"
)
REGEXP_POINTS_2D_OTHERS = re.compile(r"\s*,\s*({0}\s+{0})".format(NUMBER_REGEXP))
REGEXP_LINESTRING_2D = re.compile(r"^\s*LINESTRING\s*(\(.*\))\s*$")

def extract_point_list_wkt(text):
    result = REGEXP_POINTS_2D.findall(text)
    if len(result) != 1:
        raise ValueError("Cannot parse list of points: {}".format(repr(text)))
    first, others = result[0]
    return [
        Point2D.from_str(item) for item in [first] + (REGEXP_POINTS_2D_OTHERS.findall(others) if others else [])
    ]


def float_or_int(value):
    return float(value) if "." in value else int(value)


class Point2D(namedtuple("Point2D", ("x", "y", "properties"))):
    def __new__(cls, x, y, properties=None):
        # TODO: validate coords and properties
        return super().__new__(cls, x, y, properties if properties is not None else {})

    @classmethod
    def from_str(cls, text):
        x, y = REGEXP_NEGATIVE_SIGN.sub("-", text).split()
        return cls(x=float_or_int(x), y=float_or_int(y))

    def __str__(self):
        return "POINT ({} {})".format(self.x, self.y)

    def __bytes__(self):
        # Field 1: B (uchar, 1 B), endianness: 1 = little, 0 = big
        # Field 2: I (uint, 4 B), geometry type: 1 = Point
        # Field 3: d (double, 8 B), x
        # Field 4: d (double, 8 B), y
        return pack("<BIdd", 1, 1, self.x, self.y)
        # Big endian would be:
        # pack("<BI", 0, 1) + pack(">dd", self.x, self.y)

    # TODO: create `to_wkb` (same as `__bytes__`, maybe with endianness selection)?

    def shp(self):
        return pack("<idd", 1, self.x, self.y)

    @classmethod
    def from_wkb(cls, data):
        if len(data) != 21:  # 21 = 1 + 4 + 8 + 8
            raise ValueError("Invalid length for Point2D: {} (expected: 21)".format(len(data)))
        endianness = unpack("B", data[:1])[0]
        geometry_type, x, y = unpack(("<" if endianness == 1 else ">") + "Idd", data[1:])
        if geometry_type != 1:
            raise ValueError("Invalid geometry type for Point2D: {} (expected: 1)".format(geometry_type))
        return cls(x=x, y=y)

    @classmethod
    def from_shp(cls, data):
        if len(data) != 20:  # 20 = 4 + 8 + 8
            raise ValueError("Invalid length for Point2D: {} (expected: 20)".format(len(data)))
        geometry_type = unpack("<i", data[:4])[0]  # shp uses little endian
        if geometry_type != 1:
            raise ValueError("Invalid geometry type for Point2D: {} (expected: 1)".format(geometry_type))
        x, y = unpack("<dd", data[4:])
        return cls(x=x, y=y)

    @classmethod
    def from_wkt(cls, text):
        result = REGEXP_POINT_2D.findall(text)
        if len(result) != 1:
            raise ValueError("Cannot parse value as Point2D: {}".format(repr(text)))
        points = extract_point_list_wkt(result[0])
        if len(points) > 1:
            raise ValueError("Wrong number of values for Point2D: {}".format(repr(text)))
        return points[0]

    def geojson(self):
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.x, self.y],
            },
            "properties": {} if self.properties is None else self.properties,
        }

    @classmethod
    def from_geojson(cls, data):
        type_ = data.get("type")
        geometry = data.get("geometry", {}) or {}
        geometry_type = geometry.get("type")
        geometry_coords = geometry.get("coordinates")
        if not type_ or not geometry or type_ != "Feature" or not geometry_type or not geometry_coords:
            raise ValueError("Missing type or geometry fields for GeoJSON: {}".format(repr(data)))
        elif geometry_type != "Point":
            raise ValueError("Geometry type is not Point: {}".format(repr(data)))
        x, y = geometry_coords
        return cls(x=x, y=y, properties=data.get("properties"))


class LineString2D(namedtuple("LineString2D", ("points", "properties"))):
    def __new__(cls, points, properties=None):
        # TODO: validate points and properties
        return super().__new__(cls, points, properties if properties is not None else {})

    def __str__(self):
        points_str = ["{} {}".format(point.x, point.y) for point in self.points]
        return "LINESTRING ({})".format(", ".join(points_str))

    def __bytes__(self):
        # Field 1: B (uchar, 1 B), endianness: 1 = little, 0 = big
        # Field 2: I (uint, 4 B), geometry type: 2 = LineString
        # Field 3: I (uint, 4 B), number of points
        # Field 4: d (double, 8 B), x1
        # Field 5: d (double, 8 B), y2
        # Field 4 + i: d, Field 5 + i: d
        n_points = len(self.points)
        points_numbers = [value for point in self.points for value in (point.x, point.y)]
        return pack("<BII" + ("dd" * n_points), 1, 2, n_points, *points_numbers)

    def shp(self):
        point = self.points[0]
        xmin, xmax, ymin, ymax = point.x, point.x, point.y, point.y
        points_numbers = []
        for point in self.points:
            x, y = point.x, point.y
            points_numbers.extend((x, y))
            if x < xmin:
                xmin = x
            elif x > xmax:
                xmax = x
            if y < ymin:
                ymin = y
            elif y > ymax:
                ymax = y
        n_points = len(self.points)
        return pack("<Iddddiii" + ("dd" * n_points), 3, xmin, ymin, xmax, ymax, 1, n_points, 0, *points_numbers)

    @classmethod
    def from_wkb(cls, data):
        if len(data) < 41:  # 41 = (1 + 4 + 4) + (8 + 8) + (8 + 8)
            raise ValueError("Invalid length for LineString2D: {} (expected: at least 41)".format(len(data)))
        endianness = unpack("B", data[:1])[0]
        geometry_type, n_points = unpack(("<" if endianness == 1 else ">") + "II", data[1:9])  # TODO endian?
        if geometry_type != 2:
            raise ValueError("Invalid geometry type for LineString2D: {} (expected: 2)".format(geometry_type))
        elif n_points < 2:
            raise ValueError("Invalid number of points for LineString2D: {} (expected: at least 2)".format(n_points))
        coords = unpack(("<" if endianness == 1 else ">") + ("dd" * n_points), data[9:])
        return cls(points=tuple([Point2D(x=x, y=y) for x, y in zip(coords[::2], coords[1::2])]))

    @classmethod
    def from_shp(cls, data):
        if len(data) < 80:  # 80 = 4 + (8 + 8 + 8 + 8) + 4 + 4 + 4 + (8 + 8) + (8 + 8) -> 1 part with at least 2 pts
            raise ValueError("Invalid length for LineString2D: {} (expected: at least 80)".format(len(data)))
        geometry_type, xmin, ymin, xmax, ymax, n_parts, n_points, start_index = unpack("<iddddiii", data[:48])
        if geometry_type != 3:
            raise ValueError("Invalid geometry type for LineString2D: {} (expected: 3)".format(geometry_type))
        elif n_parts != 1:
            raise ValueError("Invalid number of parts for LineString2D: {} (expected: 1)".format(n_parts))
        elif n_points < 2 * n_parts:
            raise ValueError(
                "Invalid number of points for LineString2D: {} (expected: at least {})".format(n_points, 2 * n_parts)
            )
        elif start_index != 0:
            raise ValueError("Invalid start index for part 1 for LineString2D: {} (expected: 0)".format(start_index))
        coords = unpack("<" + ("dd" * n_points), data[48:])
        return cls(points=tuple([Point2D(x=x, y=y) for x, y in zip(coords[::2], coords[1::2])]))

    @classmethod
    def from_wkt(cls, text):
        result = REGEXP_LINESTRING_2D.findall(text)
        if len(result) != 1:
            raise ValueError("Cannot parse value as LineString: {}".format(repr(text)))
        return cls(points=tuple(extract_point_list_wkt(result[0])))

    @classmethod
    def from_geojson(cls, data):
        type_ = data.get("type")
        geometry = data.get("geometry", {}) or {}
        geometry_type = geometry.get("type")
        geometry_coords = geometry.get("coordinates")
        if not type_ or not geometry or type_ != "Feature" or not geometry_type or not geometry_coords:
            raise ValueError("Missing type or geometry fields for GeoJSON: {}".format(repr(data)))
        elif geometry_type != "LineString":
            raise ValueError("Geometry type is not LineString: {}".format(repr(data)))
        return cls(points=tuple([Point2D(x=x, y=y) for x, y in geometry_coords]), properties=data.get("properties"))

    def geojson(self):
        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[point.x, point.y] for point in self.points],
            },
            "properties": {} if self.properties is None else self.properties,
        }
