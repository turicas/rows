# coding: utf-8

# Copyright 2016 Álvaro Justen <https://github.com/turicas/rows/>
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

from __future__ import unicode_literals

import logging

from collections import namedtuple

from rows.plugins.utils import create_table


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


logging.getLogger("parquet").addHandler(NullHandler())

import parquet


OPTIONS = namedtuple('Options', ['col', 'format'])(col=None, format='custom')


def _callback(*args):
    return args


def import_from_parquet(filename, encoding='utf-8', *args, **kwargs):
    'Import data from a Parquet file'

    # TODO: should be able to used fobj also

    data, field_names = parquet.dump(filename, OPTIONS, _callback)
    length = len(data[field_names[0]])
    table_rows = [[data[field_name][index] for field_name in field_names]
                  for index in range(length)]

    meta = {'imported_from': 'parquet', 'filename': filename,}
    return create_table([field_names] + table_rows, meta=meta, *args, **kwargs)
