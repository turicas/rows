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

    def test_is_null(self):
        self.assertEqual(utils.is_null(None), True)
        self.assertEqual(utils.is_null(''), True)
        self.assertEqual(utils.is_null(' \t '), True)
        self.assertEqual(utils.is_null('null'), True)
        self.assertEqual(utils.is_null('nil'), True)
        self.assertEqual(utils.is_null('none'), True)
        self.assertEqual(utils.is_null('-'), True)

        self.assertEqual(utils.is_null('Álvaro'), False)
        self.assertEqual(utils.is_null('Álvaro'.encode('utf-8')), False)

    def test_as_string(self):
        self.assertEqual(utils.as_string(None), 'None')
        self.assertEqual(utils.as_string(42), '42')
        self.assertEqual(utils.as_string(3.141592), '3.141592')
        self.assertEqual(utils.as_string('Álvaro'), 'Álvaro')
        self.assertEqual(utils.as_string('Álvaro'.encode('utf-8')),
                         'Álvaro'.encode('utf-8'))

    def test_ipartition(self):
        iterable = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = utils.ipartition(iterable, 3)
        self.assertEqual(type(result), types.GeneratorType)
        self.assertEqual(list(result), [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]])
