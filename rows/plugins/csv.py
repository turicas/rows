# coding: utf-8

from __future__ import unicode_literals

import unicodecsv

from rows.fields import detect_field_types
from rows.table import Table
from rows.utils import slug


def import_from_csv(filename, fields=None, delimiter=',', quotechar='"',
                    encoding='utf-8'):
    'Import data from a CSV file'
    # TODO: add auto_detect_types=True parameter
    # this import will be moved in the future (to another module, actually)

    fobj = open(filename)
    csv_reader = unicodecsv.reader(fobj, encoding=encoding,
                                   delimiter=str(delimiter),
                                   quotechar=str(quotechar))
    table_rows = [row for row in csv_reader]
    header, table_rows = table_rows[0], table_rows[1:]
    header = [slug(field_name).lower() for field_name in header]

    if fields is None:
        fields = detect_field_types(header, table_rows, encoding=encoding)
    table = Table(fields=fields)
    for row in table_rows:
        table.append({field_name: value
                      for field_name, value in zip(header, row)})
    return table

def export_to_csv(table, filename, encoding='utf-8'):
    # TODO: will work only if table.fields is OrderedDict

    fields = table.fields
    with open(filename, mode='w') as fobj:
        csv_writer = unicodecsv.writer(fobj, encoding=encoding)
        csv_writer.writerow(fields.keys())

        for row in table:
            csv_writer.writerow([type_.serialize(getattr(row, field),
                                                 encoding=encoding)
                                 for field, type_ in fields.items()])
