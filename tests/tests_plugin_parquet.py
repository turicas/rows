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

import unittest

import mock

import rows
import rows.plugins._parquet


DATA = [['nation_key', 'name', 'region_key', 'comment_col'],
        [0, 'ALGERIA', 0, ' haggle. carefully final deposits detect slyly agai'],
        [1, 'ARGENTINA', 1, 'al foxes promise slyly according to the regular accounts. bold requests alon'],
        [2, 'BRAZIL', 1, 'y alongside of the pending deposits. carefully special packages are about the ironic forges. slyly special '],
        [3, 'CANADA', 1, 'eas hang ironic, silent packages. slyly regular packages are furiously over the tithes. fluffily bold'],
        [4, 'EGYPT', 4, 'y above the carefully unusual theodolites. final dugouts are quickly across the furiously regular d'],
        [5, 'ETHIOPIA', 0, 'ven packages wake quickly. regu'],
        [6, 'FRANCE', 3, 'refully final requests. regular, ironi'],
        [7, 'GERMANY', 3, 'l platelets. regular accounts x-ray: unusual, regular acco'],
        [8, 'INDIA', 2, 'ss excuses cajole slyly across the packages. deposits print aroun'],
        [9, 'INDONESIA', 2, ' slyly express asymptotes. regular deposits haggle slyly. carefully ironic hockey players sleep blithely. carefull'],
        [10, 'IRAN', 4, 'efully alongside of the slyly final dependencies. '],
        [11, 'IRAQ', 4, 'nic deposits boost atop the quickly final requests? quickly regula'],
        [12, 'JAPAN', 2, 'ously. final, express gifts cajole a'],
        [13, 'JORDAN', 4, 'ic deposits are blithely about the carefully regular pa'],
        [14, 'KENYA', 0, ' pending excuses haggle furiously deposits. pending, express pinto beans wake fluffily past t'],
        [15, 'MOROCCO', 0, 'rns. blithely bold courts among the closely regular packages use furiously bold platelets?'],
        [16, 'MOZAMBIQUE', 0, 's. ironic, unusual asymptotes wake blithely r'],
        [17, 'PERU', 1, 'platelets. blithely pending dependencies use fluffily across the even pinto beans. carefully silent accoun'],
        [18, 'CHINA', 2, 'c dependencies. furiously express notornis sleep slyly regular accounts. ideas sleep. depos'],
        [19, 'ROMANIA', 3, 'ular asymptotes are about the furious multipliers. express dependencies nag above the ironically ironic account'],
        [20, 'SAUDI ARABIA', 4, 'ts. silent requests haggle. closely express packages sleep across the blithely'],
        [21, 'VIETNAM', 2, 'hely enticingly express accounts. even, final '],
        [22, 'RUSSIA', 3, ' requests against the platelets use never according to the quickly regular pint'],
        [23, 'UNITED KINGDOM', 3, 'eans boost carefully special requests. accounts are. carefull'],
        [24, 'UNITED STATES', 1, 'y final packages. slow foxes cajole quickly. quickly silent platelets breach ironic accounts. unusual pinto be']]


class PluginParquetTestCase(unittest.TestCase):

    plugin_name = 'parquet'
    filename = 'tests/data/nation.dict.parquet'

    def test_imports(self):
        self.assertIs(rows.import_from_parquet,
                      rows.plugins._parquet.import_from_parquet)

    @mock.patch('rows.plugins._parquet.create_table')
    def test_import_from_parquet_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'some_key': 123, 'other': 456, }
        result = rows.import_from_parquet(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['meta'] = {'imported_from': 'parquet',
                          'filename': self.filename, }
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins._parquet.create_table')
    def test_import_from_parquet_retrieve_desired_data(self,
                                                       mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        table = rows.import_from_parquet(self.filename)
        args = mocked_create_table.call_args[0][0]

        self.assertEqual(args, DATA)
