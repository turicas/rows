# coding: utf-8

import datetime
import tempfile
import textwrap
import unittest

import rows


class ExportToTextTestCase(unittest.TestCase):

    def setUp(self):
        self.table = rows.Table(fields=['id', 'username', 'birthday'])
        self.table._rows = [
                [1, u'turicas', datetime.date(1987, 4, 29)],
                [2, u'another-user', datetime.date(2000, 1, 1)],
                [3, u'álvaro', datetime.date(1900, 1, 1)], ]
        #TODO: should use .append instead of writing directly to _rows?

        self.table.identify_data_types(sample_size=None)
        self.expected = textwrap.dedent(u'''
        +----+--------------+------------+
        | id |   username   |  birthday  |
        +----+--------------+------------+
        |  1 |      turicas | 1987-04-29 |
        |  2 | another-user | 2000-01-01 |
        |  3 |       álvaro | 1900-01-01 |
        +----+--------------+------------+
        ''').strip()
        self.custom_expected = textwrap.dedent(u'''
        -++++-++++++++++++++-++++++++++++-
        * id *   username   *  birthday  *
        -++++-++++++++++++++-++++++++++++-
        *  1 *      turicas * 1987-04-29 *
        *  2 * another-user * 2000-01-01 *
        *  3 *       álvaro * 1900-01-01 *
        -++++-++++++++++++++-++++++++++++-
        ''').strip()

    def test_return_simple_test(self):
        returned = self.table.export_to_text()
        self.assertEqual(returned.strip(), self.expected)
        self.assertEqual(type(returned), unicode)

    def test_column_sizes(self):
        table = rows.Table(fields=['id', 'username', 'big-column-name'])
        table._rows = [
                [1, u'a', datetime.date(1987, 4, 29)],
                [2, u'b', datetime.date(2000, 1, 1)],
                [3, u'c', datetime.date(1900, 1, 1)], ]
        #TODO: should use .append instead of writing directly to _rows?

        table.identify_data_types(sample_size=None)
        expected = textwrap.dedent(u'''
        +----+----------+-----------------+
        | id | username | big-column-name |
        +----+----------+-----------------+
        |  1 |        a |      1987-04-29 |
        |  2 |        b |      2000-01-01 |
        |  3 |        c |      1900-01-01 |
        +----+----------+-----------------+
        ''').strip()
        returned = table.export_to_text()
        self.assertEqual(returned.strip(), expected)


    def test_return_custom_elements(self):
        returned = self.table.export_to_text(dash='+', plus='-', pipe='*')
        self.assertEqual(returned.strip(), self.custom_expected)
        self.assertEqual(type(returned), unicode)

    def test_return_custom_encoding(self):
        encoding = 'iso-8859-1'
        returned = self.table.export_to_text(encoding=encoding)
        self.assertEqual(returned.strip(), self.expected.encode(encoding))
        self.assertEqual(type(returned), str)

    def test_filename_simple_test(self):
        tmp = tempfile.NamedTemporaryFile(delete=True)
        with self.assertRaises(ValueError):
            self.table.export_to_text(tmp.name)

        self.table.export_to_text(tmp.name, encoding='utf-8')
        tmp.file.seek(0)
        returned = tmp.file.read()
        tmp.close()

        self.assertEqual(returned.strip(), self.expected.encode('utf-8'))

    def test_fobj_simple_test(self):
        tmp = tempfile.NamedTemporaryFile(delete=True)
        with self.assertRaises(ValueError):
            self.table.export_to_text(tmp.file)

        self.table.export_to_text(tmp.file, encoding='utf-8')
        tmp.file.seek(0)
        returned = tmp.file.read()
        tmp.close()

        self.assertEqual(returned.strip(), self.expected.encode('utf-8'))
