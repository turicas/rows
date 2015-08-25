# coding: utf-8

from __future__ import unicode_literals

import types
import unittest

import rows.utils as utils


class UtilsTestCase(unittest.TestCase):

    def test_slug(self):
        self.assertEqual(utils.slug('Álvaro Justen'), 'alvaro_justen')
        self.assertEqual(utils.slug("Moe's Bar"), 'moes_bar')
        self.assertEqual(utils.slug("-----te-----st------"), 'te_st')

    def test_ipartition(self):
        iterable = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = utils.ipartition(iterable, 3)
        self.assertEqual(type(result), types.GeneratorType)
        self.assertEqual(list(result), [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]])

    # TODO: test make_header
    # TODO: test create_table
