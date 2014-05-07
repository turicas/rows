# coding: utf-8

# Copyright 2014 Álvaro Justen <https://github.com/turicas/rows/>
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import locale
import re


DATE_REGEXP = re.compile('^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
DATETIME_REGEXP = re.compile('^[0-9]{4}-[0-9]{2}-[0-9]{2} '
                             '[0-9]{2}:[0-9]{2}:[0-9]{2}$')
NULL = ('-', 'null', 'none', 'nil')

def convert_to_bool(value, input_encoding):
    value = unicode(value).lower().strip()
    if not value or value in NULL:
        return None
    elif value in ('y', 't', '1','true'):
        return True
    elif value in ('n', 'f', '0', 'false'):
        return False
    else:
        raise ValueError("Can't be bool")

def convert_to_int(value, input_encoding):
    value = unicode(value).lower().strip()
    if not value or value in NULL:
        return None

    return locale.atoi(value)

def convert_to_float(value, input_encoding):
    value = unicode(value).lower().strip()
    if not value or value in NULL:
        return None

    return locale.atof(value)

def convert_to_datetime(value, input_encoding):
    value = unicode(value).lower().strip()
    if not value or value in NULL:
        return None

    if DATETIME_REGEXP.match(value) is None:
        raise ValueError("Can't be datetime")
    else:
        info = value.split()
        date = [int(x) for x in info[0].split('-')]
        rest = [int(x) for x in info[1].split(':')]
        return datetime.datetime(*(date + rest))

def convert_to_date(value, input_encoding):
    value = unicode(value).lower().strip()
    if not value or value in NULL:
        return None

    if DATE_REGEXP.match(value) is None:
        raise ValueError("Can't be date")
    else:
        year, month, day = [int(x) for x in unicode(value).split('-')]
        return datetime.date(year, month, day)

def convert_to_str(value, input_encoding):
    if isinstance(value, unicode):
        return value
    else:
        if not isinstance(value, str):
            value = str(value)
        return value.decode(input_encoding)

TYPE_CONVERTERS = {
        bool: convert_to_bool,
        int: convert_to_int,
        float: convert_to_float,
        datetime.date: convert_to_date,
        datetime.datetime: convert_to_datetime,
        str: convert_to_str,}
TYPES = (bool, int, float, datetime.date, datetime.datetime, str)
