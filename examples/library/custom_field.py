from __future__ import unicode_literals

import sys

import rows


class MyIntegerField(rows.fields.IntegerField):

    '''Weird integer represetation, having a `#` just before the number'''

    @classmethod
    def serialize(cls, value):
        return '#' + str(value)

    @classmethod
    def deserialize(cls, value):
        return int(value.replace('#', ''))


class PtBrDateField(rows.fields.DateField):

    INPUT_FORMAT = '%d/%m/%Y'


data = [['name', 'age', 'birthdate'],
        ['alvaro', '#30', '29/04/1987'],
        ['joao', '#17', '01/02/2000']]

table = rows.plugins.utils.create_table(
        data,
        force_types={'age': MyIntegerField,
                     'birthdate': PtBrDateField,})
print(type(table[0].age))  # `<class 'int'>`
print(type(table[0].birthdate))  # `<class 'datetime.date'>`
print(rows.export_to_txt(table)) # "age" values will start with "#"
