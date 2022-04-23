# coding: utf-8

# Copyright 2014-2022 Álvaro Justen <https://github.com/turicas/rows/>
# Copyright 2022 João S. O. Bueno <https://github.com/turicas/rows/>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.

#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

# from __future__ import unicode_literals

import re

from copy import deepcopy
import operator
import sys

from collections.abc import Mapping

def ensure_query(query):
    if isinstance(query, str):
        tokens = tokenize(query)
        return Query._from_tokens(tokens)
    if not isinstance(query, QueryBase):
        raise TypeError(f"Can't create a query from a {type(query).__name__} instance.")
    return query

"""
To think about:
possibly plug-ins will want to add their own operators for the tokens
(example: geometry operators "ABOVE", "BELLOW" for the PDF plugin)

So, the token hierarchy will likely have to be contained as an object,
which plug-ins can then create a copy, enhance, and change.
"""


class Token:
    # these are not just "tokens": they will also be structured as Query tree nodes, and perform ops.
    literal_registry = {}
    match_registry = []
    literal = None

    def __new__(cls, value):

        if value.upper() in __class__.literal_registry:
            instance = super().__new__(__class__.literal_registry[value.upper()])
        else:
            for subcls in __class__.match_registry:
                if subcls._match(value):
                    instance = super().__new__(subcls)
                    break
            else:
                raise ValueError(f"No registerd token type matches {value!r}")
        # Python won't call __init__ if what __new__ returns is not an strict instance of __class__:
        instance.__init__(value)
        return instance

    def __init__(self, value):
        self.value = value

    def __init_subclass__(cls, *args, **kw):
        super().__init_subclass__(*args, **kw)
        if cls.literal:
            __class__.literal_registry[cls.literal.upper()] = cls
        elif "_match" in cls.__dict__:
            __class__.match_registry.append(cls)

    @classmethod
    def _match(cls, value):
        raise NotImplementedError()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value!r})"


class BinOpToken(Token):
    pass

class EqualToken(BinOpToken):
    literal = "=="
    op = operator.eq

# TODO: instantiate other operator token classes


# IMPORTANT: Do not change declaration order of classes that do not declare a "literal" field.
class LiteralToken(Token):
    pass

class FieldNameToken(Token):
    @classmethod
    def _match(cls, value):
        return re.match(r"\w+", value) and not value[0].isdigit()

class LiteralIntToken(LiteralToken):
    def __init__(self, value):
        self.value = int(value)

    @classmethod
    def _match(cls, value):
        return re.match(r"\d+", value)

class LiteralStrToken(Token):
    def __init__(self, value):
        self.value = value[1:-1]

    @classmethod
    def _match(cls, value):
        return re.match(r"""(?P<quote>['"]).*?(?P=quote)""", value)


def tokenize(query:str) -> "list[Token]":
    tokens =  [Token(g[0]) for g in re.findall(r"""(OR|AND|\w+|((?P<quote>['"]).*?(?P=quote))|==|<|>|>=|<=)""", query, flags=re.IGNORECASE)]
    return tokens


class QueryBase:
    @classmethod
    def _from_tokens(cls, tokens):
        raise NotImplementedError()

class Query(QueryBase):
    pass

'''

class Field:
    """Acessor class to identify a field (class attribute, dataclass field or dicionary key) to be used in queries

        params:
            name: Field name as a string. If a dotted name, the path up to the field name is located in the
            scope of the calling code and used as the "cls"  attribute.

            cls: A  class or Mapping where "name" will be searched as an attribute or a key when the Query where this field is used is resolved.

    """
    def __init__(self, name, cls=None, _depth=0):
        self.name = name
        if not cls and "." in name:
                self.cls, self.name = name.rsplit(".", 1)

        else:
            self.cls = cls
        if isinstance(self.cls, str):
            self.cls = self._retrieve_class_from_string(sys._getframe(1 + _depth), self.cls) or self.cls

    def retrieve(self, instance):
        if isinstance(instance, Mapping):
            return instance[self.name]
        return getattr(instance, self.name)

        #if isinstance(self.cls, type) and not (hasattr(self.cls, self.name) or self.name in getattr(self.cls, "__dataclass_fields__", {})):
            #raise ValueError

    def __repr__(self):
        return f"Field {(self.cls.__name__ + '.') if self.cls else ''}{self.name}"

    @staticmethod
    def _retrieve_class_from_string(frame, name):
        if "." in name:
            name, remainder = name.split(".", 1)
        else:
            remainder = None
        cls = frame.f_locals.get(name, frame.f_globals.get(name, None))
        if cls and remainder:
            for component in remainder.split("."):
                cls = getattr(cls, component)
        return cls


class Q:
    def __init__(self, field=None, /,  **kwargs):
        if field and kwargs:
            raise TypeError("A Q object should either encapsulate a Field, or represent a keyword argument test expression")
        if field:
            if isinstance(field, Q):
                # just create another instance of whatever query was passed:
                if hasattr(field, "tree"):
                    self.tree = deepcopy(field.tree)
                self.field = copy(field.field)
                return
            if isinstance(field, str):
                field = Field(field, _depth=1)
                self.field = field

            elif isinstance(field, Q):
                self.__dict__ = field.__dict__.copy()
        elif isinstance(field, str):
            self.param = Field(name=str, cls=None)
        if kwargs:
            ops = self._parse_ops(kwargs)

    def _parse_ops(self, keyword_expressions)-> "list[tuple[op, Field, arg]]":
        pass
'''

