# coding: utf-8

import sys

from collections import OrderedDict

import rows

# taken from:
# http://www.supercom.gob.ec/es/informate-y-participa/directorio-de-medios/21-radiodifusoras
filename = 'tests/data/ecuador-medios-radiodifusoras.html'
rows_xpath = '//*[@class="entry-container"]/*[@class="row-fluid"]/*[@class="span6"]'
fields_xpath = OrderedDict([
        ('url', '//h2/a/@href'),
        ('name', '//h2/a/text()'),
        ('address', '//div[@class="spField field_direccion"]/text()'),
        ('phone', '//div[@class="spField field_telefono"]/text()'),
        ('website', '//div[@class="spField field_sitio_web"]/text()'),
        ('email', '//div[@class="spField field_email"]/text()'), ])

table = rows.import_from_xpath(filename, rows_xpath, fields_xpath)
rows.export_to_csv(table, 'ecuador-radiodifusoras.csv')
