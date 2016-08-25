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

from collections import OrderedDict

import mock

import rows


DATA = [['nation_key', 'name', 'region_key', 'comment_col'],
        [0, b'ALGERIA', 0, b' haggle. carefully final deposits detect slyly agai'],
        [1, b'ARGENTINA', 1, b'al foxes promise slyly according to the regular accounts. bold requests alon'],
        [2, b'BRAZIL', 1, b'y alongside of the pending deposits. carefully special packages are about the ironic forges. slyly special '],
        [3, b'CANADA', 1, b'eas hang ironic, silent packages. slyly regular packages are furiously over the tithes. fluffily bold'],
        [4, b'EGYPT', 4, b'y above the carefully unusual theodolites. final dugouts are quickly across the furiously regular d'],
        [5, b'ETHIOPIA', 0, b'ven packages wake quickly. regu'],
        [6, b'FRANCE', 3, b'refully final requests. regular, ironi'],
        [7, b'GERMANY', 3, b'l platelets. regular accounts x-ray: unusual, regular acco'],
        [8, b'INDIA', 2, b'ss excuses cajole slyly across the packages. deposits print aroun'],
        [9, b'INDONESIA', 2, b' slyly express asymptotes. regular deposits haggle slyly. carefully ironic hockey players sleep blithely. carefull'],
        [10, b'IRAN', 4, b'efully alongside of the slyly final dependencies. '],
        [11, b'IRAQ', 4, b'nic deposits boost atop the quickly final requests? quickly regula'],
        [12, b'JAPAN', 2, b'ously. final, express gifts cajole a'],
        [13, b'JORDAN', 4, b'ic deposits are blithely about the carefully regular pa'],
        [14, b'KENYA', 0, b' pending excuses haggle furiously deposits. pending, express pinto beans wake fluffily past t'],
        [15, b'MOROCCO', 0, b'rns. blithely bold courts among the closely regular packages use furiously bold platelets?'],
        [16, b'MOZAMBIQUE', 0, b's. ironic, unusual asymptotes wake blithely r'],
        [17, b'PERU', 1, b'platelets. blithely pending dependencies use fluffily across the even pinto beans. carefully silent accoun'],
        [18, b'CHINA', 2, b'c dependencies. furiously express notornis sleep slyly regular accounts. ideas sleep. depos'],
        [19, b'ROMANIA', 3, b'ular asymptotes are about the furious multipliers. express dependencies nag above the ironically ironic account'],
        [20, b'SAUDI ARABIA', 4, b'ts. silent requests haggle. closely express packages sleep across the blithely'],
        [21, b'VIETNAM', 2, b'hely enticingly express accounts. even, final '],
        [22, b'RUSSIA', 3, b' requests against the platelets use never according to the quickly regular pint'],
        [23, b'UNITED KINGDOM', 3, b'eans boost carefully special requests. accounts are. carefull'],
        [24, b'UNITED STATES', 1, b'y final packages. slow foxes cajole quickly. quickly silent platelets breach ironic accounts. unusual pinto be'],
]


class PluginParquetTestCase(unittest.TestCase):

    plugin_name = 'parquet'
    filename = 'tests/data/nation.dict.parquet'

    def test_imports(self):
        self.assertIs(rows.import_from_parquet,
                      rows.plugins.plugin_parquet.import_from_parquet)

    @mock.patch('rows.plugins.plugin_parquet.create_table')
    def test_import_from_parquet_uses_create_table(self, mocked_create_table):
        mocked_create_table.return_value = 42
        kwargs = {'some_key': 123, 'other': 456, }
        result = rows.import_from_parquet(self.filename, **kwargs)
        self.assertTrue(mocked_create_table.called)
        self.assertEqual(mocked_create_table.call_count, 1)
        self.assertEqual(result, 42)

        call = mocked_create_table.call_args
        kwargs['force_types'] = OrderedDict([
            ('nation_key', rows.fields.IntegerField),
            ('name', rows.fields.BinaryField),
            ('region_key', rows.fields.IntegerField),
            ('comment_col', rows.fields.BinaryField)
        ])
        kwargs['meta'] = {'imported_from': 'parquet',
                          'filename': self.filename, }
        self.assertEqual(call[1], kwargs)

    @mock.patch('rows.plugins.plugin_parquet.create_table')
    def test_import_from_parquet_retrieve_desired_data(self,
                                                       mocked_create_table):
        mocked_create_table.return_value = 42

        # import using filename
        table = rows.import_from_parquet(self.filename)
        args = mocked_create_table.call_args[0][0]

        self.assertEqual(args, DATA)

    # TODO: test all supported field types
