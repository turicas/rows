# coding: utf-8

import unittest

from textwrap import dedent

from rows import tables_html


class TestRows(unittest.TestCase):
    def test_regular_table(self):
        html = dedent('''
            <html>
              <head>
                <title>test</title>
              </head>
              <body>
                <table>
                  <tr>
                    <th>header col 1</th>
                    <th>header col 2</th>
                    <th>header col 3</th>
                  </tr>
                  <tr>
                    <td>row 1 col 1</td>
                    <td>row 1 col 2</td>
                    <td>row 1 col 3</td>
                  </tr>
                  <tr>
                    <td>row 2 col 1</td>
                    <td>row 2 col 2</td>
                    <td>row 2 col 3</td>
                  </tr>
                </table>
              </body>
            </html>
        ''').strip()
        result = tables_html(html)
        expected_table = [['header col 1', 'header col 2', 'header col 3'],
                          ['row 1 col 1',  'row 1 col 2',  'row 1 col 3'],
                          ['row 2 col 1',  'row 2 col 2',  'row 2 col 3']]
        expected = [expected_table]
        self.assertEqual(result, expected)

    def test_no_ending_tags(self):
        html = dedent('''
            <html>
              <head>
                <title>test</title>
              </head>
              <body>
                <table>
                  <tr>
                    <th>header col 1
                    <th>header col 2</th>
                    <th>header col 3
                  </tr>
                  <tr>
                    <td>row 1 col 1
                    <td>row 1 col 2</td>
                    <td>row 1 col 3</td>
                  </tr>
                  <tr>
                    <td>row 2 col 1</td>
                    <td>row 2 col 2</td>
                    <td>row 2 col 3
                  <tr>
                    <td>row 3 col 1
                    <td>row 3 col 2
                    <td>row 3 col 3
                </table>
              </body>
            </html>
        ''').strip()
        result = tables_html(html)
        expected_table = [['header col 1', 'header col 2', 'header col 3'],
                          ['row 1 col 1',  'row 1 col 2',  'row 1 col 3'],
                          ['row 2 col 1',  'row 2 col 2',  'row 2 col 3'],
                          ['row 3 col 1',  'row 3 col 2',  'row 3 col 3']]
        expected = [expected_table]
        print
        print expected_table
        print
        print result[0]
        self.assertEqual(result, expected)

    def test_clear_html(self):
        pass

    def test_colspan(self):
        pass

    def test_rowspan(self):
        pass

    def test_nested_tables(self):
        pass
