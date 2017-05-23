# coding: utf-8

# Copyright 2014-2016 Álvaro Justen <https://github.com/turicas/rows/>
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

from itertools import chain

from rows.plugins.utils import create_table


def import_from_dicts(data, samples=1000, *args, **kwargs):
    '''Import data from a iterable of dicts in a lazy way

    The algorithm will use the `samples` first `dict`s to determine the field
    names.
    '''

    data = iter(data)

    cached_rows, headers = [], []
    for index, row in enumerate(data, start=1):
        cached_rows.append(row)

        for key in row.keys():
            if key not in headers:
                headers.append(key)

        if index == samples:
            break

    data_rows = ([row.get(header, None) for header in headers]
                 for row in chain(cached_rows, data))

    kwargs['samples'] = samples
    meta = {'imported_from': 'dicts', }
    return create_table(chain([headers], data_rows), meta=meta,
            *args, **kwargs)


def export_to_dicts(table, *args, **kwargs):
    return [{key: getattr(row, key) for key in table.field_names}
            for row in table]
