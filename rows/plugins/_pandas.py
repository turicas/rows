# coding: utf-8

# Copyright 2014-2015 Álvaro Justen <https://github.com/turicas/rows/>
#
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

import pandas

from rows.plugins.utils import create_table

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def import_from_pandas(data_frame, *args, **kwargs):
    meta = {'imported_from': 'pandas', 'filename': 'DataFrame', }
    return create_table(_dataframe_generator(data_frame), meta=meta, *args,
                        **kwargs)

def _dataframe_generator(data_frame):
    yield list(data_frame)

    for _, row in data_frame.iterrows():
        yield dataframe_row_to_list(row)

def dataframe_row_to_list(row):
    result = []
    for element_index, element in enumerate(row):
        #Problem importing pandas.tslib.Timestamp or pandas.Timestamp
        if isinstance(element, pandas.tslib.Timestamp):
            date_string = element.strftime(DATE_FORMAT)
            if date_string.endswith("00:00:00"):
                value = datetime.datetime.strptime(date_string,
                                                   DATE_FORMAT).date()
            else:
                value = element.to_datetime()
        result.append(value)
    return result


def export_to_pandas(table_obj):
    data_frame = pandas.DataFrame(_generator_table(table_obj),
                                  columns=table_obj.field_names)

    return data_frame

def _generator_table(table_obj):
    for row in table_obj:
        yield list(row)
