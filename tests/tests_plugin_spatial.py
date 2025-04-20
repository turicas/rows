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

import pytest

from rows.compat import BINARY_TYPE, TEXT_TYPE
from rows.plugins.plugin_spatial import LineString2D, Point2D, extract_point_list_wkt

# TODO: add SRID, to_ewkb, to_ewkt, from_ewkb, from_ewkt


def hex_to_splits(data, splits):
    data_hex = data.hex()
    result = []
    index = 0
    for split in splits:
        this_split = []
        for _ in range(split):
            hex_index = index * 2
            if this_split:
                this_split.append(" ")
            this_split.append(data_hex[hex_index])
            this_split.append(data_hex[hex_index + 1])
            index += 1
        result.append("".join(this_split))
    if index != len(data):
        raise ValueError("Wrong number of splits")
    return result


POINT_1 = Point2D(x=10, y=20)
POINT_1_WKT = "POINT (10 20)"
POINT_1_GEOJSON = {
    "type": "Feature",
    "geometry": {
        "type": "Point",
        "coordinates": [10, 20]
    },
    "properties": {}
}
# ST_AsEWKB('POINT(10 20)'::geometry, 'XDR')
POINT_1_WKB_BIG = BINARY_TYPE.fromhex(
    "00"                                     # endianness (0 = big)
    "00" "00" "00" "01"                      # geometry type
    "40" "24" "00" "00" "00" "00" "00" "00"  # x
    "40" "34" "00" "00" "00" "00" "00" "00"  # y
)
# ST_AsEWKB('POINT(10 20)'::geometry, 'NDR')
POINT_1_WKB_LITTLE = BINARY_TYPE.fromhex(
    "01"                                     # endianness (1 = little)
    "01" "00" "00" "00"                      # geometry type
    "00" "00" "00" "00" "00" "00" "24" "40"  # x
    "00" "00" "00" "00" "00" "00" "34" "40"  # y
)
POINT_1_SHP = BINARY_TYPE.fromhex(
    "01" "00" "00" "00"                      # geometry type
    "00" "00" "00" "00" "00" "00" "24" "40"  # x
    "00" "00" "00" "00" "00" "00" "34" "40"  # y
)
assert POINT_1_SHP == POINT_1_WKB_LITTLE[1:]

POINT_2 = Point2D(x=123.45, y=67.89)
POINT_2_WKT = "POINT (123.45 67.89)"
POINT_2_GEOJSON = {
    "type": "Feature",
    "geometry": {
        "type": "Point",
        "coordinates": [123.45, 67.89]
    },
    "properties": {}
}
POINT_2_PROPERTIES = Point2D(x=123.45, y=67.89, properties={"some": 123, "value": 456})
POINT_2_GEOJSON_PROPERTIES = {
    "type": "Feature",
    "geometry": {
        "type": "Point",
        "coordinates": [123.45, 67.89]
    },
    "properties": {
        "some": 123,
        "value": 456
    }
}
# ST_AsEWKB('POINT(123.45 67.89)'::geometry, 'XDR')
POINT_2_WKB_BIG = BINARY_TYPE.fromhex(
    "00"                                     # endianness (0 = big)
    "00" "00" "00" "01"                      # geometry type
    "40" "5E" "DC" "CC" "CC" "CC" "CC" "CD"  # x
    "40" "50" "F8" "F5" "C2" "8F" "5C" "29"  # y
)
# ST_AsEWKB('POINT(123.45 67.89)'::geometry, 'NDR')
POINT_2_WKB_LITTLE = BINARY_TYPE.fromhex(
    "01"                                     # endianness (1 = little)
    "01" "00" "00" "00"                      # geometry type
    "CD" "CC" "CC" "CC" "CC" "DC" "5E" "40"  # x
    "29" "5C" "8F" "C2" "F5" "F8" "50" "40"  # y
)
POINT_2_SHP = BINARY_TYPE.fromhex(
    "01" "00" "00" "00"                      # geometry type
    "CD" "CC" "CC" "CC" "CC" "DC" "5E" "40"  # x
    "29" "5C" "8F" "C2" "F5" "F8" "50" "40"  # y
)
assert POINT_2_SHP == POINT_2_WKB_LITTLE[1:]

POINT_3 = Point2D(x=-10, y=-34.56)
POINT_3_WKT = "POINT (-10 -34.56)"
POINT_3_GEOJSON = {
    "type": "Feature",
    "geometry": {
        "type": "Point",
        "coordinates": [-10, -34.56]
    },
    "properties": {}
}
# ST_AsEWKB('POINT(-10 -34.56)'::geometry, 'XDR')
POINT_3_WKB_BIG = BINARY_TYPE.fromhex(
    "00"                                     # endianness (0 = big)
    "00" "00" "00" "01"                      # geometry type
    "C0" "24" "00" "00" "00" "00" "00" "00"  # x
    "C0" "41" "47" "AE" "14" "7A" "E1" "48"  # y
)
# ST_AsEWKB('POINT(-10 -34.56)'::geometry, 'NDR')
POINT_3_WKB_LITTLE = BINARY_TYPE.fromhex(
    "01"                                     # endianness (1 = little)
    "01" "00" "00" "00"                      # geometry type
    "00" "00" "00" "00" "00" "00" "24" "C0"  # x
    "48" "E1" "7A" "14" "AE" "47" "41" "C0"  # y
)
POINT_3_SHP = BINARY_TYPE.fromhex(
    "01" "00" "00" "00"                      # geometry type
    "00" "00" "00" "00" "00" "00" "24" "C0"  # x
    "48" "E1" "7A" "14" "AE" "47" "41" "C0"  # y
)
assert POINT_3_SHP == POINT_3_WKB_LITTLE[1:]

LINESTRING_1 = LineString2D(points=(POINT_1, POINT_2, POINT_3))
LINESTRING_1_WKT = "LINESTRING (10 20, 123.45 67.89, -10 -34.56)"
LINESTRING_1_GEOJSON = {
    "type": "Feature",
    "geometry": {
        "type": "LineString",
        "coordinates": [
            [10, 20],
            [123.45, 67.89],
            [-10, -34.56],
        ]
    },
    "properties": {}
}
# ST_AsEWKB('LINESTRING (10 20, 123.45 67.89, -10 -34.56)'::geometry, 'XDR')
LINESTRING_1_WKB_BIG = BINARY_TYPE.fromhex(
    "00"                                     # endianness (0 = big)
    "00" "00" "00" "02"                      # geometry type
    "00" "00" "00" "03"                      # number of points
    "40" "24" "00" "00" "00" "00" "00" "00"  # x1
    "40" "34" "00" "00" "00" "00" "00" "00"  # y1
    "40" "5E" "DC" "CC" "CC" "CC" "CC" "CD"  # x2
    "40" "50" "F8" "F5" "C2" "8F" "5C" "29"  # y2
    "C0" "24" "00" "00" "00" "00" "00" "00"  # x3
    "C0" "41" "47" "AE" "14" "7A" "E1" "48"  # y3
)
# ST_AsEWKB('LINESTRING (10 20, 123.45 67.89, -10 -34.56)'::geometry, 'NDR')
LINESTRING_1_WKB_LITTLE = BINARY_TYPE.fromhex(
    "01"                                     # endianness (1 = little)
    "02" "00" "00" "00"                      # geometry type (2 = LineString)
    "03" "00" "00" "00"                      # number of points
    "00" "00" "00" "00" "00" "00" "24" "40"  # x1
    "00" "00" "00" "00" "00" "00" "34" "40"  # y1
    "CD" "CC" "CC" "CC" "CC" "DC" "5E" "40"  # x2
    "29" "5C" "8F" "C2" "F5" "F8" "50" "40"  # y2
    "00" "00" "00" "00" "00" "00" "24" "C0"  # x3
    "48" "E1" "7A" "14" "AE" "47" "41" "C0"  # y3
)
LINESTRING_1_SHP = BINARY_TYPE.fromhex(
    "03" "00" "00" "00"                      # geometry type (3 = PolyLine)
    "00" "00" "00" "00" "00" "00" "24" "C0"  # xmin = x3
    "48" "E1" "7A" "14" "AE" "47" "41" "C0"  # ymin = y3
    "CD" "CC" "CC" "CC" "CC" "DC" "5E" "40"  # xmax = x2
    "29" "5C" "8F" "C2" "F5" "F8" "50" "40"  # ymax = y2
    "01" "00" "00" "00"                      # number of parts
    "03" "00" "00" "00"                      # number of points
    "00" "00" "00" "00"                      # index of the first point in this part
    "00" "00" "00" "00" "00" "00" "24" "40"  # x1
    "00" "00" "00" "00" "00" "00" "34" "40"  # y1
    "CD" "CC" "CC" "CC" "CC" "DC" "5E" "40"  # x2
    "29" "5C" "8F" "C2" "F5" "F8" "50" "40"  # y2
    "00" "00" "00" "00" "00" "00" "24" "C0"  # x3
    "48" "E1" "7A" "14" "AE" "47" "41" "C0"  # y3
)
assert LINESTRING_1_SHP[-16:] == LINESTRING_1_WKB_LITTLE[-16:]
assert LINESTRING_1_SHP[40:44] == LINESTRING_1_WKB_LITTLE[5:9]



def test_parse_point_list():
    text = "(20 30, 35 35, 30 20, 20 30)"
    expected = [Point2D(x=20, y=30), Point2D(x=35, y=35), Point2D(x=30, y=20), Point2D(x=20, y=30)]
    assert extract_point_list_wkt(text) == expected

    text = "(10 20, 123.45 67.89, 75 -10, -10 -34.56, 10 20)"
    expected = [POINT_1, POINT_2, POINT_4, POINT_3, POINT_1]
    assert extract_point_list_wkt(text) == expected


def test_point_2d():
    point = Point2D(x=123, y=456)
    assert point.x == 123
    assert point.y == 456
    assert point.properties == {}

    point = Point2D(x=123, y=456, properties={"abc": 123, "def": 456})
    assert point.x == 123
    assert point.y == 456
    assert point.properties == {"abc": 123, "def": 456}


def test_point_2d_from_wkt():
    assert Point2D.from_wkt("   POINT (10 20)   ") == POINT_1  # int, extra spaces
    assert Point2D.from_wkt("POINT(30 -10)") == Point2D(x=30, y=-10)  # int negative, no space
    assert Point2D.from_wkt("POINT (- 30 10)") == Point2D(x=-30, y=10)  # int negative with space
    assert Point2D.from_wkt("POINT (30.123 10.456)") == Point2D(x=30.123, y=10.456)  # float
    assert Point2D.from_wkt("POINT (- 30.123 -10.456)") == Point2D(x=-30.123, y=-10.456)  # float negative

    text = "POINT (1,23 4,56)"
    with pytest.raises(ValueError, match=re.escape("Cannot parse list of points: '(1,23 4,56)'")):
        result = Point2D.from_wkt(text)

    assert Point2D.from_wkt(POINT_1_WKT) == POINT_1
    assert Point2D.from_wkt(POINT_2_WKT) == POINT_2
    assert Point2D.from_wkt(POINT_3_WKT) == POINT_3


def test_point_2d_to_wkt():
    assert TEXT_TYPE(POINT_1) == POINT_1_WKT
    assert TEXT_TYPE(POINT_2) == POINT_2_WKT
    assert TEXT_TYPE(POINT_3) == POINT_3_WKT


def test_point_2d_to_wkb():
    splits = [1, 4, 8, 8]
    assert hex_to_splits(BINARY_TYPE(POINT_1), splits) == hex_to_splits(POINT_1_WKB_LITTLE, splits)
    assert hex_to_splits(BINARY_TYPE(POINT_2), splits) == hex_to_splits(POINT_2_WKB_LITTLE, splits)
    assert hex_to_splits(BINARY_TYPE(POINT_3), splits) == hex_to_splits(POINT_3_WKB_LITTLE, splits)


def test_point_2d_from_wkb():
    assert Point2D.from_wkb(POINT_1_WKB_LITTLE) == POINT_1
    assert Point2D.from_wkb(POINT_2_WKB_LITTLE) == POINT_2
    assert Point2D.from_wkb(POINT_3_WKB_LITTLE) == POINT_3
    assert Point2D.from_wkb(POINT_1_WKB_BIG) == POINT_1
    assert Point2D.from_wkb(POINT_2_WKB_BIG) == POINT_2
    assert Point2D.from_wkb(POINT_3_WKB_BIG) == POINT_3


def test_point_2d_from_shp():
    assert Point2D.from_shp(POINT_1_SHP) == POINT_1
    assert Point2D.from_shp(POINT_2_SHP) == POINT_2
    assert Point2D.from_shp(POINT_3_SHP) == POINT_3


def test_point_2d_to_shp():
    splits = [4, 8, 8]
    assert hex_to_splits(POINT_1.shp(), splits) == hex_to_splits(POINT_1_SHP, splits)
    assert hex_to_splits(POINT_2.shp(), splits) == hex_to_splits(POINT_2_SHP, splits)
    assert hex_to_splits(POINT_3.shp(), splits) == hex_to_splits(POINT_3_SHP, splits)


def test_point_2d_to_geojson():
    assert POINT_1.geojson() == POINT_1_GEOJSON
    assert POINT_2.geojson() == POINT_2_GEOJSON
    assert POINT_2_PROPERTIES.geojson() == POINT_2_GEOJSON_PROPERTIES
    assert POINT_3.geojson() == POINT_3_GEOJSON


def test_point_2d_from_geojson():
    assert Point2D.from_geojson(POINT_1_GEOJSON) == POINT_1
    assert Point2D.from_geojson(POINT_2_GEOJSON) == POINT_2
    assert Point2D.from_geojson(POINT_2_GEOJSON_PROPERTIES) == POINT_2_PROPERTIES
    assert Point2D.from_geojson(POINT_3_GEOJSON) == POINT_3
    # TODO: add test for ValueErrors in `from_geojson`


def test_line_string_2d():
    line = LineString2D(points=(POINT_1, POINT_2, POINT_3))
    assert len(line.points) == 3
    assert line.points[0] == POINT_1
    assert line.points[1] == POINT_2
    assert line.points[2] == POINT_3
    assert line == LINESTRING_1

    line = LineString2D(points=(POINT_1, POINT_2, POINT_3), properties={"def": 123, "abc": 456})
    assert len(line.points) == 3
    assert line.points[0] == POINT_1
    assert line.points[1] == POINT_2
    assert line.points[2] == POINT_3
    assert line.properties == {"def": 123, "abc": 456}


def test_line_string_2d_to_wkt():
    assert TEXT_TYPE(LINESTRING_1) == LINESTRING_1_WKT


def test_line_string_2d_from_wkt():
    assert LineString2D.from_wkt(LINESTRING_1_WKT) == LINESTRING_1
    # TODO: test behavior of "others" when garbage is added? (REGEXP_LINESTRING_2D_OTHERS don't have `^...$`)
    # TODO: add more tests


def test_line_string_2d_to_wkb():
    splits = [1] + [4] * 2 + [8] * 6
    assert hex_to_splits(BINARY_TYPE(LINESTRING_1), splits) == hex_to_splits(LINESTRING_1_WKB_LITTLE, splits)


def test_line_string_2d_from_wkb():
    assert LineString2D.from_wkb(LINESTRING_1_WKB_LITTLE) == LINESTRING_1
    assert LineString2D.from_wkb(LINESTRING_1_WKB_BIG) == LINESTRING_1


def test_line_string_2d_from_shp():
    splits = [4] + [8] * 4 + [4] * 3 + [8] * 6
    assert LineString2D.from_shp(LINESTRING_1_SHP) == LINESTRING_1


def test_line_string_2d_to_shp():
    splits = [4] + [8] * 4 + [4] * 3 + [8] * 6
    assert hex_to_splits(LINESTRING_1.shp(), splits) == hex_to_splits(LINESTRING_1_SHP, splits)


def test_line_string_2d_to_geojson():
    assert LINESTRING_1.geojson() == LINESTRING_1_GEOJSON
    # TODO: test properties


def test_line_string_2d_from_geojson():
    assert LineString2D.from_geojson(LINESTRING_1_GEOJSON) == LINESTRING_1
    # TODO: test properties
    # TODO: add test for ValueErrors in `from_geojson`
