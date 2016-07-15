# coding: utf-8

from __future__ import unicode_literals

from io import BytesIO

import requests
import rows

from rows.plugins.html import extract_links, extract_text


# Get the HTML
url = 'http://wnpp.debian.net/'
response = requests.get(url)
html = response.content

# Import data, preserving cell's HTML
packages = rows.import_from_html(BytesIO(html), index=10, preserve_html=True)

def transform(row, table):
    'Extract links from "project" field and remove HTML from all'

    data = row._asdict()
    data['links'] = ' '.join(extract_links(row.project))
    for key, value in data.items():
        if isinstance(value, basestring):
            data[key] = extract_text(value)
    return data

new_fields = packages.fields.copy()
new_fields['links'] = rows.fields.TextField
packages = rows.transform(new_fields, transform, packages)

rows.export_to_csv(packages, 'debian-wnpp.csv')
