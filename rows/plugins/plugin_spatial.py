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
import struct
from collections import namedtuple

NUMBER_REGEXP = r"(-?\s*[0-9]+(?:\.[0-9]+)?)"
REGEXP_POINT_2D = re.compile(r"^\s*POINT\s*\(\s*{0}\s+{0}\)\s*$".format(NUMBER_REGEXP))


class Point2D(namedtuple("Point2D", ("x", "y", "properties"))):
    def __new__(cls, x, y, properties=None):
        return super().__new__(cls, x, y, properties if properties is not None else {})

    def __str__(self):
        return "POINT ({} {})".format(self.x, self.y)

    def __bytes__(self):
        # Field 1: B (uchar, 1 B), endianness: 1 = little, 0 = big
        # Field 2: I (uint, 4 B), geometry type: 1 = Point
        # Field 3: d (double, 8 B), x
        # Field 4: d (double, 8 B), y
        return struct.pack("<BIdd", 1, 1, self.x, self.y)
        # Big endian would be:
        # struct.pack("<BI", 0, 1) + struct.pack(">dd", self.x, self.y)

    # TODO: create `to_wkb` (same as `__bytes__`, maybe with endianness selection)?

    @classmethod
    def from_wkb(cls, data):
        if len(data) != 21:  # 21 = 1 + 4 + 8 + 8
            raise ValueError("Invalid length for Point2D: {} (expected: 21)".format(len(data)))
        endianness = struct.unpack("B", data[:1])[0]
        geometry_type, x, y = struct.unpack(("<" if endianness == 1 else ">") + "Idd", data[1:])
        if geometry_type != 1:
            raise ValueError("Invalid geometry type for Point2D: {} (expected: 1)".format(geometry_type))
        return cls(x=x, y=y)

    @classmethod
    def from_shp(cls, data):
        if len(data) != 20:  # 20 = 4 + 8 + 8
            raise ValueError("Invalid length for Point2D: {} (expected: 20)".format(len(data)))
        geometry_type = struct.unpack("<i", data[:4])[0]  # shp uses little endian
        if geometry_type != 1:
            raise ValueError("Invalid geometry type for Point2D: {} (expected: 1)".format(geometry_type))
        x, y = struct.unpack("<dd", data[4:])
        return cls(x=x, y=y)

    def shp(self):
        return struct.pack("<idd", 1, self.x, self.y)

    @classmethod
    def from_wkt(cls, text):
        result = REGEXP_POINT_2D.findall(text)
        if len(result) != 1:
            raise ValueError("Cannot parse value as Point: {}".format(repr(text)))
        return cls(x=float(result[0][0].replace(" ", "")), y=float(result[0][1].replace(" ", "")))

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
