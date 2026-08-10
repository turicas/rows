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

from __future__ import unicode_literals
from decimal import Decimal
from rows.plugins.utils import create_table, get_filename_and_fobj
from tables import open_file
from re import findall

def import_hdf5(filename, *args, **kwargs):

    """Import HDF5 file
        Parameters
        ----------
        filename : path (string)
    """
    ff = open_file(filename, 'r')
    gg = []
    for group in ff.walk_groups():
        gg.append(group)

    gg = str(gg)
    gr = findall('(?<=children := \[\')(.*?)(?=\'\s)', gg)

    data = getattr(getattr(ff.root, gr[0]), gr[1])
    header = data.attrs.values_block_0_kind
    table_rows = []
    for val in data.read():
        table_rows.append(val[1])

    ff.close()

    return create_table(header, table_rows, *args, **kwargs)

