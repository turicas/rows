# coding: utf-8

import datetime


# Order matters here
__all__ = ['DateField', 'UnicodeField', 'StringField', 'Field']
# TYPES = (bool, int, float, datetime.date, datetime.datetime, str)


class Field(object):
    TYPE = type(None)

    def serialize(self, value, *args, **kwargs):
        raise NotImplementedError('Should be implemented')

    def deserialize(self, value, *args, **kwargs):
        raise NotImplementedError('Should be implemented')


class UnicodeField(Field):
    TYPE = unicode

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if 'encoding' in kwargs:
            return value.encode(encoding)
        else:
            return str(value)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        if 'encoding' in kwargs:
            return value.decode(encoding)
        else:
            return unicode(value)


class StringField(Field):
    TYPE = str

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        return value

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        return value


class DateField(Field):
    TYPE = datetime.date
    INPUT_FORMAT = '%Y-%m-%d'
    OUTPUT_FORMAT = '%Y-%m-%d'

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        return value.strftime(cls.OUTPUT_FORMAT)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        dt_object = datetime.datetime.strptime(value, cls.INPUT_FORMAT)
        return datetime.date(dt_object.year, dt_object.month, dt_object.day)

# TODO: implement IntegerField
# TODO: implement DatetimeField
# TODO: implement FloatField
# TODO: implement DecimalField
# TODO: implement PercentField
