# coding: utf-8

from __future__ import unicode_literals

import datetime
import re

from collections import OrderedDict

import rows.fields

from rows.table import Table


REGEXP_UWSGI_LOG = re.compile(r'\[pid: ([0-9]+)\|app: [0-9]+\|req: '
                              r'[0-9]+/[0-9]+\] '
                              r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+) .+ \[(.+)\] '
                              r'([^ ]+) (.+) => generated .+ in ([0-9]+) '
                              r'micros \(HTTP/([^ ]+) ([^)]+)\)')
UWSGI_FIELDS = OrderedDict([('pid', rows.fields.IntegerField),
                            ('ip', rows.fields.TextField),
                            ('datetime', rows.fields.DatetimeField),
                            ('http_verb', rows.fields.TextField),
                            ('http_path', rows.fields.TextField),
                            ('generation_time', rows.fields.FloatField),
                            ('http_version', rows.fields.FloatField),
                            ('http_status', rows.fields.IntegerField)])
UWSGI_DATETIME_FORMAT = '%a %b %d %H:%M:%S %Y'
strptime = datetime.datetime.strptime


def import_from_uwsgi_log(filename):
    fields = UWSGI_FIELDS.keys()
    table = Table(fields=UWSGI_FIELDS)
    with open(filename) as fobj:
        for line in fobj:
            result = REGEXP_UWSGI_LOG.findall(line)
            if result:
                data = list(result[0])
                # Convert datetime
                data[2] = strptime(data[2], UWSGI_DATETIME_FORMAT)
                # Convert generation time (micros -> seconds)
                data[5] = float(data[5]) / 1000000
                table.append({field_name: value
                              for field_name, value in zip(fields, data)})
    return table


if __name__ == '__main__':

    table = import_from_uwsgi_log('uwsgi.log')
    for row in table:
        print(row)
