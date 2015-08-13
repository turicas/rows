# coding: utf-8

import datetime
import locale
import re

from decimal import Decimal, InvalidOperation

from rows.utils import as_string, is_null


# Order matters here
__all__ = ['BoolField', 'IntegerField', 'FloatField', 'DateField',
           'DatetimeField', 'DecimalField', 'PercentField', 'UnicodeField',
           'ByteField', 'Field']
REGEXP_ONLY_NUMBERS = re.compile('[^0-9]')
SHOULD_NOT_USE_LOCALE = True  # This variable is changed on rows.locale_manager


class Field(object):
    '''Base Field class - all fields should inherit from this

    As the fallback for all other field types are the ByteField, this Field
    actually implements what is expected in the ByteField'''

    TYPE = str

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        return str(value)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        if isinstance(value, cls.TYPE):
            return value
        elif is_null(value):
            return None
        else:
            return as_string(value)


class ByteField(Field):
    '''Field class to represent byte arrays

    Is not locale-aware (does not need to be)
    '''

    pass


class BoolField(Field):
    '''Base class to representing boolean

    Is not locale-aware (if you need to, please customize by changing its
    attributes like `TRUE_VALUES` and `FALSE_VALUES`)
    '''

    TYPE = bool
    SERIALIZE_VALUES = {True: 'true', False: 'false'}
    TRUE_VALUES = ('true', '1', 'yes')
    FALSE_VALUES = ('false', '0', 'no')

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ''  # TODO: should always be this way?

        return cls.SERIALIZE_VALUES[value]

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(BoolField, cls).deserialize(value)
        if value is None:
            return None

        if value in cls.TRUE_VALUES:
            return True
        elif value in cls.FALSE_VALUES:
            return False
        else:
            raise ValueError()


class IntegerField(Field):
    '''Field class to represent integer

    Is locale-aware
    '''

    TYPE = int

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ''  # TODO: should always be this way?

        if SHOULD_NOT_USE_LOCALE:
            return str(value)
        else:
            grouping = kwargs.get('grouping', None)
            return locale.format('%d', value, grouping=grouping)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(IntegerField, cls).deserialize(value)
        if value is None:
            return None

        if SHOULD_NOT_USE_LOCALE:
            return int(value)
        else:
            return locale.atoi(value)


class FloatField(Field):
    '''Field class to represent float

    Is locale-aware
    '''

    TYPE = float

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ''  # TODO: should always be this way?

        if SHOULD_NOT_USE_LOCALE:
            return str(value)
        else:
            grouping = kwargs.get('grouping', None)
            return locale.format('%f', value, grouping=grouping)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(FloatField, cls).deserialize(value)
        if value is None:
            return None

        if SHOULD_NOT_USE_LOCALE:
            return float(value)
        else:
            return locale.atof(value)


class DecimalField(Field):
    '''Field class to represent decimal data (as Python's decimal.Decimal)

    Is locale-aware
    '''

    TYPE = Decimal

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ''  # TODO: should always be this way?
        # TODO: test None on all Field.serialize

        if SHOULD_NOT_USE_LOCALE:
            return str(value)
        else:
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
        value = super(DecimalField, cls).deserialize(value)
        if value is None:
            return None

        if SHOULD_NOT_USE_LOCALE:
            try:
                return Decimal(value)
            except InvalidOperation:
                raise ValueError("Can't be {}".format(cls.__name__))
        else:
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
                    value = value + (Decimal(parts[1]) / (10 ** decimal_places))
            except InvalidOperation:
                raise ValueError("Can't be {}".format(cls.__name__))
            return value


class PercentField(DecimalField):
    '''Field class to represent percent values

    Is locale-aware (inherit this behaviour from `rows.DecimalField`)
    '''

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        if isinstance(value, cls.TYPE):
            return value
        elif is_null(value):
            return None

        if '%' not in value:
            raise ValueError("Can't be {}".format(cls.__name__))
        value = value.replace('%', '')
        return super(PercentField, cls).deserialize(value) / 100


class DateField(Field):
    '''Field class to represent date

    Is not locale-aware (does not need to be)
    '''

    TYPE = datetime.date
    INPUT_FORMAT = '%Y-%m-%d'
    OUTPUT_FORMAT = '%Y-%m-%d'

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ''  # TODO: should always be this way?

        return value.strftime(cls.OUTPUT_FORMAT)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(DateField, cls).deserialize(value)
        if value is None:
            return None

        dt_object = datetime.datetime.strptime(value, cls.INPUT_FORMAT)
        return datetime.date(dt_object.year, dt_object.month, dt_object.day)


class DatetimeField(Field):
    '''Field class to represent date-time

    Is not locale-aware (does not need to be)
    '''

    TYPE = datetime.datetime
    DATETIME_REGEXP = re.compile('^([0-9]{4})-([0-9]{2})-([0-9]{2})[ T]'
                                 '([0-9]{2}):([0-9]{2}):([0-9]{2})$')

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ''  # TODO: should always be this way?

        return value.isoformat()

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(DatetimeField, cls).deserialize(value)
        if value is None:
            return None

        # TODO: may use iso8601
        groups = cls.DATETIME_REGEXP.findall(value)
        if not groups:
            raise ValueError("Can't be {}".format(cls.__name__))
        else:
            return datetime.datetime(*[int(x) for x in groups[0]])


class UnicodeField(Field):
    '''Field class to represent unicode strings

    Is not locale-aware (does not need to be)
    '''

    TYPE = unicode

    @classmethod
    def serialize(cls, value, *args, **kwargs):
        if value is None:
            return ''  # TODO: should always be this way?

        if 'encoding' in kwargs:
            return value.encode(kwargs['encoding'])
        else:
            return str(value)

    @classmethod
    def deserialize(cls, value, *args, **kwargs):
        value = super(UnicodeField, cls).deserialize(value)
        if value is None:
            return None

        if type(value) is unicode:
            return value
        elif 'encoding' in kwargs:
            return value.decode(kwargs['encoding'])
        else:
            return unicode(value)
