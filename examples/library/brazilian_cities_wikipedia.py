# coding: utf-8

from __future__ import unicode_literals

import re

from collections import OrderedDict
from io import BytesIO
try:
    from urlparse import urljoin # Python 2
except ImportError:
    from urllib.parse import urljoin  # Python 3

import requests
import rows


# Get data from Portuguese Wikipedia
city_list_url = 'https://pt.wikipedia.org/wiki/Lista_de_munic%C3%ADpios_do_Brasil'
response = requests.get(city_list_url)
html = response.content

# Extract desired data using XPath
cities = rows.import_from_xpath(
        BytesIO(html),
        rows_xpath='//table/tr/td/ul/li',
        fields_xpath=OrderedDict([('name', './/text()'),
                                  ('link', './/a/@href')]))

regexp_city_state = re.compile(r'(.*) \(([A-Z]{2})\)')

def transform(row, table):
    'Transform row "link" into full URL and add "state" based on "name"'

    data = row._asdict()
    data['link'] = urljoin('https://pt.wikipedia.org', data['link'])
    data['name'], data['state'] = regexp_city_state.findall(data['name'])[0]
    return data

new_fields = OrderedDict()
new_fields['name'] = cities.fields['name']
new_fields['state'] = rows.fields.TextField  # new field
new_fields['link'] = cities.fields['link']
cities = rows.transform(new_fields, transform, cities)
rows.export_to_csv(cities, 'brazilian-cities.csv')
