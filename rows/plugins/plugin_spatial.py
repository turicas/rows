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
from collections import namedtuple
from itertools import zip_longest
from struct import pack, unpack

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
REGEXP_POLYGON_2D = re.compile(
    r"^\s*POLYGON\s*\(\s*"
    + r"(\([^)]+\))"
    + "(.*)?"
    + r"\)\s*$"
)
REGEXP_LIST_OTHERS = re.compile(r"\s*,\s*(\([^)]*\))\s*")

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


def read_shp(filename):
    geom_type_mapping = {1: Point2D, 3: LineString2D, 5: Polygon2D}
    with open(filename, mode="rb", buffering=1024 * 1024) as fobj:
        header = fobj.read(100)
        while True:
            record_header = fobj.read(8)
            if not record_header:
                break
            record_number, content_length = unpack(">ii", record_header)
            content_length_bytes = content_length * 2
            record_data = fobj.read(content_length_bytes)
            geometry_type = unpack("<i", record_data[0:4])[0]
            if geometry_type not in geom_type_mapping:
                raise ValueError("Cannot read geometry of type {}".format(geometry_type))
            yield geom_type_mapping[geometry_type].from_shp(record_data)


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
        if len(data) < 80:  # 80 = 4 + 8*4 + 4*3 + 8*2*2 -> 1 part with at least 2 pts
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


class Polygon2D(namedtuple("Polygon2D", ("rings", "properties"))):
    def __new__(cls, rings, properties=None):
        # TODO: validate rings and properties
        for ring in rings:
            if ring[0] != ring[-1]:
                raise ValueError("Geometry contains a non-closed ring: {}".format(repr(ring)))
            elif len(ring) < 4:
                raise ValueError(
                    "Geometry contains a ring of invalid size (expected: at least 4, got {}): {}".format(
                        len(ring), repr(ring)
                    )
                )
        return super().__new__(cls, rings, properties if properties is not None else {})

    def __str__(self):
        return (
            "POLYGON ("
            + ", ".join(
                "(" + ", ".join("{} {}".format(point.x, point.y) for point in ring) + ")"
                for ring in self.rings
            )
            + ")"
        )

    def __bytes__(self):
        # Field 1: B (uchar, 1 B), endianness: 1 = little, 0 = big
        # Field 2: I (uint, 4 B), geometry type: 3 = Polygon
        # Field 3: I (uint, 4 B), number of rings
        # For each ring:
        # Field 4: I (uint, 4 B), number of points
        # Field 5: d (double, 8 B), x1
        # Field 6: d (double, 8 B), y1
        # Field 5 + i: d, Field 6 + i: d (xi, yi)
        n_rings = len(self.rings)
        rings_data = BINARY_TYPE()
        for ring in self.rings:
            n_points = len(ring)
            points_numbers = [value for point in ring for value in (point.x, point.y)]
            rings_data += pack("<I" + ("dd" * n_points), n_points, *points_numbers)
        return pack("<BII", 1, 3, n_rings) + rings_data

    def geojson(self):
        return {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[point.x, point.y] for point in ring]
                    for ring in self.rings
                ],
            },
            "properties": {} if self.properties is None else self.properties,
        }

    def shp(self):
        total_points = 0
        point = self.rings[0][0]
        xmin, xmax, ymin, ymax = point.x, point.x, point.y, point.y
        points_numbers, parts_indices = [], []
        for ring in self.rings:
            parts_indices.append(total_points)
            for point in ring:
                total_points += 1
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
        return pack(
            "<Iddddii" + ("I" * len(parts_indices)) + "d" * len(points_numbers),
            5, xmin, ymin, xmax, ymax, len(self.rings), total_points,
            *parts_indices,
            *points_numbers,
        )

    @classmethod
    def from_geojson(cls, data):
        type_ = data.get("type")
        geometry = data.get("geometry", {}) or {}
        geometry_type = geometry.get("type")
        geometry_coords = geometry.get("coordinates")
        if not type_ or not geometry or type_ != "Feature" or not geometry_type or not geometry_coords:
            raise ValueError("Missing type or geometry fields for GeoJSON: {}".format(repr(data)))
        elif geometry_type != "Polygon":
            raise ValueError("Geometry type is not Polygon: {}".format(repr(data)))
        return cls(
            rings=tuple([
                tuple([Point2D(x=point[0], y=point[1]) for point in ring])
                for ring in geometry_coords
            ]),
            properties=data.get("properties"),
        )

    @classmethod
    def from_wkt(cls, text):
        result = REGEXP_POLYGON_2D.findall(text)
        if len(result) != 1:
            raise ValueError("Cannot parse value as Polygon2D: {}".format(repr(text)))
        first_ring, other_rings = result[0]
        return cls(
            rings=tuple([
                tuple(extract_point_list_wkt(ring_wkt))
                for ring_wkt in [first_ring] + (REGEXP_LIST_OTHERS.findall(other_rings) if other_rings else [])
            ])
        )

    @classmethod
    def from_wkb(cls, data):
        if len(data) < 77:  # 77 = 1 + 4 + 4 + 4 + 8 + 8 + 8 + 8 + 8 + 8 + 8 + 8
            raise ValueError("Invalid length for Polygon2D: {} (expected: at least 77)".format(len(data)))
        endianness = unpack("B", data[:1])[0]
        endian = ("<" if endianness == 1 else ">")
        geometry_type, n_rings = unpack(endian + "II", data[1:9])
        if geometry_type != 3:
            raise ValueError("Invalid geometry type for Polygon2D: {} (expected: 3)".format(geometry_type))
        index, rings = 9, []
        for ring_index in range(n_rings):
            n_points = unpack(endian + "I", data[index:index + 4])[0]
            if n_points < 4:
                raise ValueError(
                    "Invalid number of points for ring {}: {} (expected: at least 4)".format(ring_index + 1, n_points)
                )
            index += 4
            stop_index = index + 2 * n_points * 8  # 2 coords per point, 8 bytes per coord
            coords = unpack(endian + ("dd" * n_points), data[index:stop_index])
            rings.append(tuple([Point2D(x=x, y=y) for x, y in zip(coords[::2], coords[1::2])]))
            index = stop_index
        return cls(rings=tuple(rings))

    @classmethod
    def from_shp(cls, data):
        if len(data) < 112:  # 112 = 4 + 8*4 + 4*3 + 8*2*4 -> 1 part with at least 4 pts
            raise ValueError("Invalid length for Polygon2D: {} (expected: at least 80)".format(len(data)))
        geometry_type, xmin, ymin, xmax, ymax, n_parts, n_points = unpack("<iddddii", data[:44])
        if geometry_type != 5:
            raise ValueError("Invalid geometry type for Polygon2D: {} (expected: 5)".format(geometry_type))
        elif n_points < 4 * n_parts:
            raise ValueError(
                "Invalid number of points for Polygon2D: {} (expected: at least {})".format(n_points, 4 * n_parts)
            )
        coords_index = 44 + 4 * n_parts
        part_indices = unpack("<" + ("i" * n_parts), data[44:coords_index])
        rings = []
        for part_index, next_part_index in zip_longest(part_indices, part_indices[1:]):
            if next_part_index is not None:
                n_points = next_part_index - part_index
            else:
                n_points = (len(data) - coords_index) // 8 // 2
            new_coords_index = coords_index + n_points * 8 * 2
            coords = unpack("<" + ("dd" * n_points), data[coords_index:new_coords_index])
            coords_index = new_coords_index
            rings.append(tuple([Point2D(x=x, y=y) for x, y in zip(coords[::2], coords[1::2])]))
        return cls(rings=tuple(rings))
