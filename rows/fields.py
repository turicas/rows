# coding: utf-8

import datetime
import locale
import re

from decimal import Decimal, InvalidOperation


# Order matters here
__all__ = ['BoolField', 'IntegerField', 'FloatField', 'DateField',
           'DatetimeField', 'DecimalField', 'PercentField', 'UnicodeField',
           'StringField', 'Field']
REGEXP_ONLY_NUMBERS = re.compile('[^0-9]')
# TODO: all fields must accept `consider_locale=False` parameter so we can set
#       it fo True if want to use locale but if not it won't slow down the
#       process of serializing/deserializing data


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


class DecimalField(Field):
    TYPE = Decimal

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        grouping = kwargs.get('grouping', None)
        value_as_string = str(value)
        has_decimal_places = value_as_string.find('.') != -1
        if not has_decimal_places:
            string_format = '%d'
        else:
            decimal_places = len(value_as_string.split('.')[1])
            string_format = '%.{}f'.format(decimal_places)
        return locale.format(string_format, value, grouping=grouping)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        locale_vars = locale.localeconv()
        decimal_separator = locale_vars['decimal_point']
        interesting_vars = ['decimal_point', 'mon_decimal_point',
                            'mon_thousands_sep', 'negative_sign',
                            'positive_sign', 'thousands_sep']
        chars = (locale_vars[x].replace('.', '\.').replace('-', '\-')
                 for x in interesting_vars)
        interesting_chars = ''.join(set(chars))
        regexp = re.compile(r'[^0-9{} ]'.format(interesting_chars))
        if regexp.findall(value):
            raise ValueError("Can't be {}".format(cls.__name__))

        parts = [REGEXP_ONLY_NUMBERS.subn('', number)[0]
                 for number in value.split(decimal_separator)]
        if len(parts) > 2:
            raise ValueError("Can't deserialize with this locale.")
        try:
            value = Decimal(parts[0])
            if len(parts) == 2:
                decimal_places = len(parts[1])
                value = value + (Decimal(parts[1]) / decimal_places)
        except InvalidOperation:
            raise ValueError("Can't be {}".format(cls.__name__))
        return value


class PercentField(DecimalField):
    TYPE = Decimal

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        grouping = kwargs.get('grouping', None)
        # Multiply by 100 and cut 2 zeroes (added by '* 100')
        value = Decimal(str(value * 100)[:-2])
        value = super(PercentField, cls).serialize(value, grouping=grouping)
        return '{}%'.format(value)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        if '%' not in value:
            raise ValueError("Can't be {}".format(cls.__name__))
        value = value.replace('%', '')
        return super(PercentField, cls).deserialize(value) / 100


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
            raise ValueError("Can't be {}".format(cls.__name__))
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
