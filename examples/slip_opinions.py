# coding: utf-8

# This example was based on:
# https://github.com/compjour/search-script-scrape/blob/master/scripts/42.py

from io import BytesIO
from urlparse import urljoin

import requests
import rows

from rows.plugins.html import tag_to_dict


url = 'http://www.supremecourt.gov/opinions/slipopinions.aspx'
html = requests.get(url).content
table = rows.import_from_html(BytesIO(html), index=1, preserve_html=True)
for element in table:
    attributes = tag_to_dict(element.name)
    print attributes['text'], urljoin(url, attributes['href'])
