# coding: utf-8

import unittest

from textwrap import dedent

import rows


def file_contents(filename):
    with open(filename) as fobj:
        contents = fobj.read()
    return contents


class TestImportFromHTML(unittest.TestCase):


    def test_simple_tables(self):
        html = file_contents('tests/data/simple-table.html')

        table = rows.import_from_html(html, table_index=0)

        fields = ['t0r0c0', 't0r0c1']
        self.assertEqual(table.fields, fields)

        self.assertEqual(len(table), 1)
        self.assertEqual(table[0], dict(zip(fields, ['t0r1c0', 't0r1c1'])))

        table = rows.import_from_html(html, table_index=1)

        fields = ['t1r0c0', 't1r0c1']
        self.assertEqual(table.fields, fields)

        self.assertEqual(len(table), 2)
        self.assertEqual(table[0], dict(zip(fields, ['t1r1c0', 't1r1c1'])))
        self.assertEqual(table[1], dict(zip(fields, ['t1r2c0', 't1r2c1'])))


    def test_nested_tables(self):
        html = file_contents('tests/data/nested-table.html')
        table = rows.import_from_html(html, table_index=0)

        fields = ['t1,0r0c0', 't1,0r0c1', 't1,0r0c2']
        self.assertEqual(table.fields, fields)
        self.assertEqual(len(table), 3)

        first_row = dict(zip(fields, ['t1,0r1c0', 't1,0r1c1', 't1,0r1c2']))
        self.assertEqual(table[0], first_row)

        self.assertEqual(table[2][fields[0]], 't1,0r2c0')
        inside_table = dedent('''
        t1,1r0c0
        t1,1r0c1
        t1,1r1c0
        t1,1r1c1
        t1,1r2c0
        t1,1r2c1
        t1,1r2c0
        t1,1r2c1
        t1,1r3c0
        t1,1r3c1
        t1,1r4c0
        t1,1r4c1
        ''').strip()
        self.assertEqual(table[2][fields[1]], inside_table)
        self.assertEqual(table[2][fields[2]], 't1,0r2c2')

        last_row = dict(zip(fields, ['t1,0r3c0', 't1,0r3c1', 't1,0r3c2']))
        self.assertEqual(table[0], first_row)


    def test_inception_one_level(self):
        html = file_contents('tests/data/nested-table.html')

        table_inception_2 = rows.import_from_html(html, table_index=2)
        fields = ['t0,2r0c0', 't0,2r0c1']
        self.assertEqual(table_inception_2.fields, fields)
        self.assertEqual(len(table_inception_2), 1)

        expected_rows = [dict(zip(fields, ['t0,2r1c0', 't0,2r1c1'])),]
        for expected_row, row in zip(expected_rows, table_inception_2):
            self.assertEqual(expected_row, row)

        table_inception = rows.import_from_html(html, table_index=1)
        fields = ['t0,1r0c0', 't0,1r0c1']
        self.assertEqual(table_inception.fields, fields)
        self.assertEqual(len(table_inception), 5)

        inception_2 = dedent('''
        t0,2r0c0
        t0,2r0c1

        t0,2r1c0
        t0,2r1c1
        ''').strip()
        expected_rows = [
                dict(zip(fields, ['t0,1r1c0', 't0,1r1c1'])),
                dict(zip(fields, ['t0,1r2c0', 't0,1r2c1'])),
                dict(zip(fields, [inception_2, 't0,1r2c1'])),
                dict(zip(fields, ['t0,1r3c0', 't0,1r3c1'])),
                dict(zip(fields, ['t0,1r4c0', 't0,1r4c1'])),]
        for expected_row, row in zip(expected_rows, table_inception):
            self.assertEqual(expected_row, row)


    @unittest.skip('to do')
    def test_unescape(self):
        pass


    @unittest.skip('to do')
    def test_table_with_header(self):
        pass


    @unittest.skip('to do')
    def test_rowspan(self):
        pass


    @unittest.skip('to do')
    def test_colspan(self):
        pass


    @unittest.skip('to do')
    def test_nested_tables(self):
        import requests
        URL = 'https://finance.yahoo.com/q;_ylt=At7WXTIEGzyrIHemoSMI7I.iuYdG;_ylu=X3oDMTBxdGVyNzJxBHNlYwNVSCAzIERlc2t0b3AgU2VhcmNoIDEx;_ylg=X3oDMTByaDM4cG9kBGxhbmcDZW4tVVMEcHQDMgR0ZXN0AzUxMjAxMw--;_ylv=3?s=GOOG&uhb=uhb2&type=2button&fr=uh3_finance_web_gs'
        URL_2 = 'http://www.rio.rj.gov.br/dlstatic/10112/2147539/DLFE-237833.htm/paginanova2.0.0.0._B.htm'
        html = requests.get(URL).content
        t = rows.import_from_html(html)


    @unittest.skip('to do')
    def test_inception_inception(self):
        pass
