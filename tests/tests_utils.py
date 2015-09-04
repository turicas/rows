# coding: utf-8

from __future__ import unicode_literals

import types
import unittest

from collections import OrderedDict

import rows.fields as fields

from rows.utils import create_table, ipartition, slug


class UtilsTestCase(unittest.TestCase):

    def test_slug(self):
        self.assertEqual(slug('Álvaro Justen'), 'alvaro_justen')
        self.assertEqual(slug("Moe's Bar"), 'moes_bar')
        self.assertEqual(slug("-----te-----st------"), 'te_st')

    def test_ipartition(self):
        iterable = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = ipartition(iterable, 3)
        self.assertEqual(type(result), types.GeneratorType)
        self.assertEqual(list(result), [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]])

    def test_create_table_skip_header(self):
        field_types = OrderedDict([('integer', fields.IntegerField),
                                   ('string', fields.UnicodeField),])
        data = [['1', 'Álvaro'], ['2', 'turicas'], ['3', 'Justen']]
        table_1 = create_table(data, fields=field_types, skip_header=True)
        table_2 = create_table(data, fields=field_types, skip_header=False)

        self.assertEqual(field_types, table_1.fields)
        self.assertEqual(table_1.fields, table_2.fields)
        self.assertEqual(len(table_1), 2)
        self.assertEqual(len(table_2), 3)

        first_row = {'integer': 1, 'string': 'Álvaro'}
        second_row = {'integer': 2, 'string': 'turicas'}
        third_row = {'integer': 3, 'string': 'Justen'}
        self.assertEqual(dict(table_1[0]._asdict()), second_row)
        self.assertEqual(dict(table_2[0]._asdict()), first_row)
        self.assertEqual(dict(table_1[1]._asdict()), third_row)
        self.assertEqual(dict(table_2[1]._asdict()), second_row)
        self.assertEqual(dict(table_2[2]._asdict()), third_row)

    # TODO: test make_header
    # TODO: test all features of create_table
    # TODO: test if error is raised if len(row) != len(fields)
    # TODO: test get_fobj_and_filename (BytesIO should return filename = None)
    # TODO: test download_file
    # TODO: test get_uri_information
    # TODO: test import_from_uri
    # TODO: test export_to_uri
