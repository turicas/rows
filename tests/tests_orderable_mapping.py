# Copyright 2014-2022 Álvaro Justen <https://github.com/turicas/rows/>

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


from rows.utils import OrderableMapping

import pytest


def test_orderable_mapping_stores__and_retrieves_key():
    a = OrderableMapping({"a": 1})
    assert a["a"] == 1


def test_orderable_mapping_delete_and_len():
    a = OrderableMapping({"a": 1})
    del a["a"]
    assert len(a) == 0


def test_orderable_mapping_preserves_insertion_order():
    a = OrderableMapping({"a": 1, "b": 2})
    a["c"] = 3
    assert list(a.keys()) == ["a", "b", "c"]


def test_orderable_mapping_preserves_inner_order():
    # low level test: if implementation changes,feel free to drop this test
    a = OrderableMapping({"a": 1, "b": 2, "c": 3})
    a.order.insert(1, a.order.pop())
    assert list(a.keys()) == ["a", "c", "b"]


def test_orderable_mapping_insert_at_pos():
    # low level test: if implementation changes,feel free to drop this test
    a = OrderableMapping({"a": 1, "b": 2, "c": 3})
    a.insert(1, "d", 4)
    assert list(a.keys()) == ["a", "d", "b", "c"]


def test_orderable_mapping_insert_at_pos_keeps_order_on_failure():
    # low level test: if implementation changes,feel free to drop this test
    a = OrderableMapping({"a": 1, "b": 2, "c": 3})
    try:
        a.insert(1, ["unhashable"], 4)
    except TypeError:
        pass
    assert len(a.order) == 3


def test_orderable_mapping_move_col():
    # low level test: if implementation changes,feel free to drop this test
    a = OrderableMapping({"a": 1, "b": 2, "c": 3})
    a.move("c", 1)
    assert list(a.keys()) == ["a", "c", "b"]


