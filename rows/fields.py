# coding: utf-8

import datetime
import locale
import re


# Order matters here
__all__ = ['BoolField', 'IntegerField', 'FloatField', 'DateField',
           'DatetimeField', 'UnicodeField', 'StringField', 'Field']
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

class BoolField(Field):
    TYPE = bool

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        return str(value).lower()

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        if value in ('true', '1', 'yes'):
            return True
        elif value in ('false', '0', 'no'):
            return False
        else:
            raise ValueError()

class IntegerField(Field):
    TYPE = int

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        grouping = kwargs.get('grouping', None)
        return locale.format('%d', value, grouping=grouping)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        return locale.atoi(value)


class FloatField(Field):
    TYPE = float

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        grouping = kwargs.get('grouping', None)
        return locale.format('%f', value, grouping=grouping)

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


class DatetimeField(Field):
    TYPE = datetime.datetime
    DATETIME_REGEXP = re.compile('^([0-9]{4})-([0-9]{2})-([0-9]{2})[ T]'
                                 '([0-9]{2}):([0-9]{2}):([0-9]{2})$')

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        return value.isoformat()

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        # TODO: may use iso8601
        groups = cls.DATETIME_REGEXP.findall(value)
        if not groups:
            raise ValueError("Can't be datetime")
        else:
            return datetime.datetime(*[int(x) for x in groups[0]])


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
        if type(value) is unicode:
            return value
        elif 'encoding' in kwargs:
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
