import datetime
import operator
from calendar import isleap

# TODO: create objects like `one_month`, `one_year` etc. so we can
# use like:
# >>> datetime.date(2020, 1, 31) + one_month
# datetime.date(2020, 2, 29)

# TODO: test using timezone info

LAST_DAY = (None, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)  # noqa
LAST_DAY_LEAP = (None, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)  # noqa


def today():
    return datetime.datetime.now().date()


def last_day(date):
    """
    >>> last_day(datetime.date(2021, 1, 1))
    datetime.date(2020, 12, 31)
    """
    return date - datetime.timedelta(days=1)


def next_day(date):
    """
    >>> next_day(datetime.date(2020, 12, 31))
    datetime.date(2021, 1, 1)
    """
    return date + datetime.timedelta(days=1)


def last_week(date):
    """
    >>> last_week(datetime.date(2021, 1, 7))
    datetime.date(2020, 12, 31)
    """
    # Preserve day of week
    return date - datetime.timedelta(days=7)


def next_week(date):
    """
    >>> next_week(datetime.date(2020, 12, 31))
    datetime.date(2021, 1, 7)
    """
    # Preserve day of week
    return date + datetime.timedelta(days=7)


def last_month(date, semantic=True):
    """
    >>> last_month(datetime.date(2020, 2, 5), semantic=True)
    datetime.date(2020, 1, 5)
    >>> last_month(datetime.date(2020, 2, 29), semantic=True)
    datetime.date(2020, 1, 29)
    >>> last_month(datetime.date(2021, 2, 28), semantic=True)
    datetime.date(2021, 1, 28)
    >>> last_month(datetime.date(2020, 2, 5), semantic=False)
    datetime.date(2020, 1, 5)
    >>> last_month(datetime.date(2020, 3, 10), semantic=False)
    datetime.date(2020, 2, 10)
    >>> last_month(datetime.date(2020, 2, 1), semantic=False)
    datetime.date(2020, 1, 1)
    """

    year = date.year if date.month > 1 else date.year - 1
    month = date.month - 1 if date.month > 1 else 12
    day = date.day

    if semantic:
        # "Semantically" remove one month from the date (even if it means the
        # difference between current date and last is not 30-31 days).
        # Works differently from `next_month`.
        last_day_last_month = (
            LAST_DAY[month] if not isleap(year) else LAST_DAY_LEAP[month]
        )
        day = day if day <= last_day_last_month else last_day_last_month

        return datetime.date(year=year, month=month, day=day)

    else:
        # Just remove the total number of days from the last month
        days = LAST_DAY[month] if not isleap(year) else LAST_DAY_LEAP[month]
        return date - datetime.timedelta(days=days)


def next_month(date, semantic=True):
    """
    >>> next_month(datetime.date(2020, 1, 5), semantic=True)
    datetime.date(2020, 2, 5)
    >>> next_month(datetime.date(2020, 1, 31), semantic=True)
    datetime.date(2020, 2, 29)
    >>> next_month(datetime.date(2021, 1, 31), semantic=True)
    datetime.date(2021, 2, 28)
    >>> next_month(datetime.date(2020, 1, 5), semantic=False)
    datetime.date(2020, 2, 5)
    >>> next_month(datetime.date(2020, 1, 31), semantic=False)
    datetime.date(2020, 3, 2)
    """
    if semantic:
        # "Semantically" add one month to the date (even if it means the
        # difference between current date and next is not 30-31 days).
        # Works differently from `last_month`: will use .
        year = date.year if date.month < 12 else date.year + 1
        month = date.month + 1 if date.month < 12 else 1
        day = date.day

        last_day_this_month = (
            LAST_DAY[date.month] if not isleap(date.year) else LAST_DAY_LEAP[date.month]
        )
        if date.day == last_day_this_month:
            day = LAST_DAY[month] if not isleap(year) else LAST_DAY_LEAP[month]

        return datetime.date(year=year, month=month, day=day)

    else:
        # Just add the total number of days the current month has
        days = (
            LAST_DAY[date.month] if not isleap(date.year) else LAST_DAY_LEAP[date.month]
        )
        return date + datetime.timedelta(days=days)


def last_year(date):
    """
    >>> next_year(datetime.date(2020, 2, 28))
    datetime.date(2021, 2, 28)
    >>> next_year(datetime.date(2016, 2, 29))
    datetime.date(2017, 3, 1)
    """
    # TODO: add `semantic` as in `next_month`

    days = 365 if not isleap(date.year - 1) else 366
    return date - datetime.timedelta(days=days)


def next_year(date):
    """
    >>> next_year(datetime.date(2020, 2, 28))
    datetime.date(2021, 2, 28)
    >>> next_year(datetime.date(2016, 2, 29))
    datetime.date(2017, 3, 1)
    """
    # TODO: add `semantic` as in `next_month`

    days = 365 if not isleap(date.year) else 366
    return date + datetime.timedelta(days=days)


DATE_INTERVALS = {
    "daily": (last_day, next_day),
    "weekly": (last_week, next_week),
    "monthly": (last_month, next_month),
    "yearly": (last_year, next_year),
}


def date_range(start, stop, step="daily"):
    """
    >>> list(date_range(datetime.date(2020, 1, 1), datetime.date(2020, 1, 3), step="daily"))
    [datetime.date(2020, 1, 1), datetime.date(2020, 1, 2)]
    >>> list(date_range(datetime.date(2020, 1, 1), datetime.date(2020, 3, 30), step="monthly"))
    [datetime.date(2020, 1, 1), datetime.date(2020, 2, 1), datetime.date(2020, 3, 1)]
    >>> list(date_range(datetime.date(2020, 1, 1), datetime.date(2020, 1, 3)))
    [datetime.date(2020, 1, 1), datetime.date(2020, 1, 2)]
    >>> list(date_range(datetime.date(2020, 1, 1), datetime.date(2019, 12, 30), step=datetime.timedelta(days=-1)))
    [datetime.date(2020, 1, 1), datetime.date(2019, 12, 31)]
    """

    if step in DATE_INTERVALS:
        check_operation = operator.lt if start < stop else operator.gt
        last_func, next_func = DATE_INTERVALS[step]
        next_value = next_func if start < stop else last_func

    else:
        next_value = lambda date: date + step
        if step > datetime.timedelta(days=0):
            check_operation = operator.lt
            if start > stop:
                raise ValueError(
                    "start cannot be greater than stop when step is positive"
                )
        else:
            check_operation = operator.gt
            if start < stop:
                raise ValueError(
                    "start cannot be lower than stop when step is negative"
                )

    current = start
    while check_operation(current, stop):
        yield current
        current = next_value(current)


def last_date(date, interval="daily"):
    last_func, _ = DATE_INTERVALS.get(interval, (None, None))
    if last_func is None:
        raise ValueError("internal not in: {}".format(", ".join(DATE_INTERVALS.keys())))

    return last_func(date)


def next_date(date, interval="daily"):
    _, next_func = DATE_INTERVALS.get(interval, (None, None))
    if next_func is None:
        raise ValueError("internal not in: {}".format(", ".join(DATE_INTERVALS.keys())))

    return next_func(date)
