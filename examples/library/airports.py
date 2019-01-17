# coding: utf-8

# This script downloads the list of airport codes and cities from
# worldnetlogistics.com and creates a `dict` called `code_to_city` with the
# correspondent mapping.
#
# Install dependencies:
#     pip install requests rows
# or
#     aptitude install python-requests python-rows

from __future__ import unicode_literals

from io import BytesIO

import requests

import rows

# Get data
url = 'http://www.worldnetlogistics.com/information/iata-city-airport-codes/'
response = requests.get(url)
html = response.content

# Parse/normalize data
table = rows.import_from_html(BytesIO(html), index=4)
code_to_city = {}
for row in table:
    code_to_city[row.code] = row.city
    if row.city_2 is not None:
        code_to_city[row.code_2] = row.city_2

codes = sorted(code_to_city.keys())
for code in codes:
    print('{} = {}'.format(code, code_to_city[code]))
