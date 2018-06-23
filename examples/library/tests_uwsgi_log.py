# coding: utf-8


from __future__ import unicode_literals

import datetime
import unittest

from uwsgi_log_plugin import import_from_uwsgi_log


class UwsgiLogPluginTestCase(unittest.TestCase):

    def test_import_from_uwsgi_log(self):
        filename = 'uwsgi.log'
        table = import_from_uwsgi_log(filename, 'utf-8')
        self.assertEqual(len(table), 2)
        first = table.Row(pid=879,
                          ip='127.0.0.1',
                          datetime=datetime.datetime(2015, 6, 1, 11, 23, 16),
                          generation_time=0.17378,
                          http_path='/something',
                          http_verb='GET',
                          http_version=1.1,
                          http_status=404)
        second = table.Row(pid=31460,
                           ip='127.0.1.1',
                           datetime=datetime.datetime(2015, 7, 15, 23, 49, 20),
                           generation_time=0.000466,
                           http_path='/about',
                           http_verb='OPTIONS',
                           http_version=1.1,
                           http_status=200)
        self.assertEqual(table[0], first)
        self.assertEqual(table[1], second)
