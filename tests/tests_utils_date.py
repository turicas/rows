import datetime

from rows.utils.date import (
    date_range,
    last_day,
    last_month,
    last_week,
    next_day,
    next_month,
    next_week,
    next_year,
)


def test_last_day():
    assert last_day(datetime.date(2021, 1, 1)) == datetime.date(2020, 12, 31)


def test_next_day():
    assert next_day(datetime.date(2020, 12, 31)) == datetime.date(2021, 1, 1)


def last_week(date):
    assert last_week(datetime.date(2021, 1, 7)) == datetime.date(2020, 12, 31)


def test_next_week():
    assert next_week(datetime.date(2020, 12, 31)) == datetime.date(2021, 1, 7)


def test_last_month():
    assert last_month(datetime.date(2020, 2, 5), semantic=True) == datetime.date(
        2020, 1, 5
    )
    assert last_month(datetime.date(2020, 2, 29), semantic=True) == datetime.date(
        2020, 1, 29
    )
    assert last_month(datetime.date(2021, 2, 28), semantic=True) == datetime.date(
        2021, 1, 28
    )

    assert last_month(datetime.date(2020, 2, 5), semantic=False) == datetime.date(
        2020, 1, 5
    )
    assert last_month(datetime.date(2020, 3, 10), semantic=False) == datetime.date(
        2020, 2, 10
    )
    assert last_month(datetime.date(2020, 2, 1), semantic=False) == datetime.date(
        2020, 1, 1
    )


def test_next_month():
    assert next_month(datetime.date(2020, 1, 5), semantic=True) == datetime.date(
        2020, 2, 5
    )
    assert next_month(datetime.date(2020, 1, 31), semantic=True) == datetime.date(
        2020, 2, 29
    )
    assert next_month(datetime.date(2021, 1, 31), semantic=True) == datetime.date(
        2021, 2, 28
    )

    assert next_month(datetime.date(2020, 1, 5), semantic=False) == datetime.date(
        2020, 2, 5
    )
    assert next_month(datetime.date(2020, 1, 31), semantic=False) == datetime.date(
        2020, 3, 2
    )


def test_last_year():
    assert next_year(datetime.date(2020, 2, 28)) == datetime.date(2021, 2, 28)
    assert next_year(datetime.date(2016, 2, 29)) == datetime.date(2017, 3, 1)


def test_next_year():
    assert next_year(datetime.date(2020, 2, 28)) == datetime.date(2021, 2, 28)
    assert next_year(datetime.date(2016, 2, 29)) == datetime.date(2017, 3, 1)


def test_date_range():
    result = list(
        date_range(datetime.date(2020, 1, 1), datetime.date(2020, 1, 3), step="daily")
    )
    expected = [datetime.date(2020, 1, 1), datetime.date(2020, 1, 2)]
    assert result == expected

    result = list(
        date_range(
            datetime.date(2020, 1, 1), datetime.date(2020, 3, 30), step="monthly"
        )
    )
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
