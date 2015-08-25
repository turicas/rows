# coding: utf-8

from __future__ import unicode_literals

import unicodecsv

import rows.utils


def import_from_csv(filename_or_fobj, delimiter=',', quotechar='"',
                    *args, **kwargs):
    'Import data from a CSV file'

    if getattr(filename_or_fobj, 'read', None) is None:
        fobj = open(filename_or_fobj)
    else:
        fobj = filename_or_fobj

    encoding = kwargs.get('encoding', 'utf-8')
    csv_reader = unicodecsv.reader(fobj, encoding=encoding,
                                   delimiter=str(delimiter),
                                   quotechar=str(quotechar))

    return rows.utils.create_table(csv_reader, *args, **kwargs)


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
