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

from rows.utils.date import date_range, last_day, last_month, last_week, next_day, next_month, next_week, next_year


def test_last_day():
    assert last_day(datetime.date(2021, 1, 1)) == datetime.date(2020, 12, 31)


def test_next_day():
    assert next_day(datetime.date(2020, 12, 31)) == datetime.date(2021, 1, 1)


def test_last_week():
    assert last_week(datetime.date(2021, 1, 7)) == datetime.date(2020, 12, 31)


def test_next_week():
    assert next_week(datetime.date(2020, 12, 31)) == datetime.date(2021, 1, 7)


def test_last_month():
    assert last_month(datetime.date(2020, 2, 5), semantic=True) == datetime.date(2020, 1, 5)
    assert last_month(datetime.date(2020, 2, 29), semantic=True) == datetime.date(2020, 1, 29)
    assert last_month(datetime.date(2021, 2, 28), semantic=True) == datetime.date(2021, 1, 28)

    assert last_month(datetime.date(2020, 2, 5), semantic=False) == datetime.date(2020, 1, 5)
    assert last_month(datetime.date(2020, 3, 10), semantic=False) == datetime.date(2020, 2, 10)
    assert last_month(datetime.date(2020, 2, 1), semantic=False) == datetime.date(2020, 1, 1)


def test_next_month():
    assert next_month(datetime.date(2020, 1, 5), semantic=True) == datetime.date(2020, 2, 5)
    assert next_month(datetime.date(2020, 1, 31), semantic=True) == datetime.date(2020, 2, 29)
    assert next_month(datetime.date(2021, 1, 31), semantic=True) == datetime.date(2021, 2, 28)

    assert next_month(datetime.date(2020, 1, 5), semantic=False) == datetime.date(2020, 2, 5)
    assert next_month(datetime.date(2020, 1, 31), semantic=False) == datetime.date(2020, 3, 2)


def test_last_year():
    assert next_year(datetime.date(2020, 2, 28)) == datetime.date(2021, 2, 28)
    assert next_year(datetime.date(2016, 2, 29)) == datetime.date(2017, 3, 1)


def test_next_year():
    assert next_year(datetime.date(2020, 2, 28)) == datetime.date(2021, 2, 28)
    assert next_year(datetime.date(2016, 2, 29)) == datetime.date(2017, 3, 1)


def test_date_range():
    result = list(date_range(datetime.date(2020, 1, 1), datetime.date(2020, 1, 3), step="daily"))
    expected = [datetime.date(2020, 1, 1), datetime.date(2020, 1, 2)]
    assert result == expected

    result = list(date_range(datetime.date(2020, 1, 1), datetime.date(2020, 3, 30), step="monthly"))
    expected = [
        datetime.date(2020, 1, 1),
        datetime.date(2020, 2, 1),
        datetime.date(2020, 3, 1),
    ]
    assert result == expected

    result = list(date_range(datetime.date(2020, 1, 1), datetime.date(2020, 1, 3)))
    expected = [datetime.date(2020, 1, 1), datetime.date(2020, 1, 2)]
    assert result == expected

    result = list(
        date_range(
            datetime.date(2020, 1, 1),
            datetime.date(2019, 12, 30),
            step=datetime.timedelta(days=-1),
        )
    )
    expected = [datetime.date(2020, 1, 1), datetime.date(2019, 12, 31)]
    assert result == expected
