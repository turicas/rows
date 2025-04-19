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

from rows.plugins.plugin_spatial import Point2D


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
POINT_1_WKB_BIG = (
    "00"                                     # endianness (0 = big)
    "00" "00" "00" "01"                      # geometry type
    "40" "24" "00" "00" "00" "00" "00" "00"  # x
    "40" "34" "00" "00" "00" "00" "00" "00"  # y
)
# ST_AsEWKB('POINT(10 20)'::geometry, 'NDR')
POINT_1_WKB_LITTLE = (
    "01"                                     # endianness (1 = little)
    "01" "00" "00" "00"                      # geometry type
    "00" "00" "00" "00" "00" "00" "24" "40"  # x
    "00" "00" "00" "00" "00" "00" "34" "40"  # y
)
POINT_1_SHP = (
    "01" "00" "00" "00"                      # geometry type
    "00" "00" "00" "00" "00" "00" "24" "40"  # x
    "00" "00" "00" "00" "00" "00" "34" "40"  # y
)
assert POINT_1_SHP == POINT_1_WKB_LITTLE[2:]

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
POINT_2_WKB_BIG = (
    "00"                                     # endianness (0 = big)
    "00" "00" "00" "01"                      # geometry type
    "40" "5E" "DC" "CC" "CC" "CC" "CC" "CD"  # x
    "40" "50" "F8" "F5" "C2" "8F" "5C" "29"  # y
)
# ST_AsEWKB('POINT(123.45 67.89)'::geometry, 'NDR')
POINT_2_WKB_LITTLE = (
    "01"                                     # endianness (1 = little)
    "01" "00" "00" "00"                      # geometry type
    "CD" "CC" "CC" "CC" "CC" "DC" "5E" "40"  # x
    "29" "5C" "8F" "C2" "F5" "F8" "50" "40"  # y
)
POINT_2_SHP = (
    "01" "00" "00" "00"                      # geometry type
    "CD" "CC" "CC" "CC" "CC" "DC" "5E" "40"  # x
    "29" "5C" "8F" "C2" "F5" "F8" "50" "40"  # y
)
assert POINT_2_SHP == POINT_2_WKB_LITTLE[2:]

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
POINT_3_WKB_BIG = (
    "00"                                     # endianness (0 = big)
    "00" "00" "00" "01"                      # geometry type
    "C0" "24" "00" "00" "00" "00" "00" "00"  # x
    "C0" "41" "47" "AE" "14" "7A" "E1" "48"  # y
)
# ST_AsEWKB('POINT(-10 -34.56)'::geometry, 'NDR')
POINT_3_WKB_LITTLE = (
    "01"                                     # endianness (1 = little)
    "01" "00" "00" "00"                      # geometry type
    "00" "00" "00" "00" "00" "00" "24" "C0"  # x
    "48" "E1" "7A" "14" "AE" "47" "41" "C0"  # y
)
POINT_3_SHP = (
    "01" "00" "00" "00"                      # geometry type
    "00" "00" "00" "00" "00" "00" "24" "C0"  # x
    "48" "E1" "7A" "14" "AE" "47" "41" "C0"  # y
)
assert POINT_3_SHP == POINT_3_WKB_LITTLE[2:]


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
    with pytest.raises(ValueError, match=re.escape("Cannot parse value as Point: '{}'".format(text))):
        result = Point2D.from_wkt(text)

    assert Point2D.from_wkt(POINT_1_WKT) == POINT_1
    assert Point2D.from_wkt(POINT_2_WKT) == POINT_2
    assert Point2D.from_wkt(POINT_3_WKT) == POINT_3


def test_point_2d_to_wkt():
    assert str(POINT_1) == POINT_1_WKT
    assert str(POINT_2) == POINT_2_WKT
    assert str(POINT_3) == POINT_3_WKT


def test_point_2d_to_wkb():
    assert bytes(POINT_1).hex().upper() == POINT_1_WKB_LITTLE
    assert bytes(POINT_2).hex().upper() == POINT_2_WKB_LITTLE
    assert bytes(POINT_3).hex().upper() == POINT_3_WKB_LITTLE


def test_point_2d_from_wkb():
    assert Point2D.from_wkb(bytes.fromhex(POINT_1_WKB_LITTLE)) == POINT_1
    assert Point2D.from_wkb(bytes.fromhex(POINT_2_WKB_LITTLE)) == POINT_2
    assert Point2D.from_wkb(bytes.fromhex(POINT_3_WKB_LITTLE)) == POINT_3
    assert Point2D.from_wkb(bytes.fromhex(POINT_1_WKB_BIG)) == POINT_1
    assert Point2D.from_wkb(bytes.fromhex(POINT_2_WKB_BIG)) == POINT_2
    assert Point2D.from_wkb(bytes.fromhex(POINT_3_WKB_BIG)) == POINT_3


def test_point_2d_from_shp():
    assert Point2D.from_shp(bytes.fromhex(POINT_1_SHP)) == POINT_1
    assert Point2D.from_shp(bytes.fromhex(POINT_2_SHP)) == POINT_2
    assert Point2D.from_shp(bytes.fromhex(POINT_3_SHP)) == POINT_3


def test_point_2d_to_shp():
    assert POINT_1.shp().hex().upper() == POINT_1_SHP
    assert POINT_2.shp().hex().upper() == POINT_2_SHP
    assert POINT_3.shp().hex().upper() == POINT_3_SHP


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
