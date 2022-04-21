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

from copy import deepcopy
import sys

from collections.abc import Mapping



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
