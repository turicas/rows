# coding: utf-8

from __future__ import print_function, unicode_literals

from io import BytesIO

import requests

import rows

# This example was based on:
# https://github.com/compjour/search-script-scrape/blob/master/scripts/42.py

try:
    from urlparse import urljoin  # Python 2
except ImportError:
    from urllib.parse import urljoin  # Python 3



tag_to_dict = rows.plugins.html.tag_to_dict
url = 'http://www.supremecourt.gov/opinions/slipopinions.aspx'
html = requests.get(url).content
table = rows.import_from_html(BytesIO(html), index=1, preserve_html=True)
for element in table:
    attributes = tag_to_dict(element.name)
    print(attributes['text'], urljoin(url, attributes['href']))
