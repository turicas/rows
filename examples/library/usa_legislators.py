# coding: utf-8

# This example was based on:
# https://github.com/compjour/search-script-scrape/blob/master/scripts/101.py

from io import BytesIO

import requests
import rows


# Capture
url = 'http://unitedstates.sunlightfoundation.com/legislators/legislators.csv'
csv = BytesIO(requests.get(url).content)

# Normalize
table = rows.import_from_csv(csv)

# Analyze
total = len(table)
total_in_office = sum(1 for row in table if row.in_office)
men = sum(1 for row in table if row.gender == 'M')
men_in_office = sum(1 for row in table if row.gender == 'M' and row.in_office)
women = sum(1 for row in table if row.gender == 'F')
women_in_office = sum(1 for row in table if row.gender == 'F' and row.in_office)

# View
print('  Men: {}/{} ({:02.2f}%), in office: {}/{} ({:02.2f}%)'
      .format(men, total, 100 * men / float(total), men_in_office,
               total_in_office, 100 * men_in_office / float(total)))
print('Women: {}/{} ({:02.2f}%), in office: {}/{} ({:02.2f}%)'
      .format(women, total, 100 * women / float(total), women_in_office,
               total_in_office, 100 * women_in_office / float(total)))
