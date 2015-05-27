# coding: utf-8

import datetime
import locale


# Order matters here
__all__ = ['IntegerField', 'FloatField', 'DateField', 'UnicodeField',
           'StringField', 'Field']
# TYPES = (bool, int, float, datetime.date, datetime.datetime, str)
# TODO: implement BoolField
# TODO: implement DatetimeField
# TODO: implement DecimalField
# TODO: implement PercentField


class Field(object):
    TYPE = type(None)

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        raise NotImplementedError('Should be implemented')

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        raise NotImplementedError('Should be implemented')


class IntegerField(Field):
    TYPE = int

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        return locale.format('%d', value, *args, **kwargs)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        return locale.atoi(value)


class FloatField(Field):
    TYPE = float

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        return locale.format('%f', value, *args, **kwargs)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        return locale.atof(value)


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


class UnicodeField(Field):
    TYPE = unicode

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if 'encoding' in kwargs:
            return value.encode(kwargs['encoding'])
        else:
            return str(value)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        if 'encoding' in kwargs:
            return value.decode(kwargs['encoding'])
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
