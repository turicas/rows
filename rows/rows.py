# coding: utf-8

# Copyright 2014-2022 Álvaro Justen <https://github.com/turicas/rows/>
# Copyright 2022 João S. O. Bueno <https://github.com/jsbueno/>

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

from collections import namedtuple
from collections.abc import Mapping


def _get_param_spec(func) -> "(inspect.Parameter, int)":
    from inspect import signature
    try:
        sig = signature(func)
    except (ValueError, TypeError):
        return None, 0
    if not sig.parameters:
        return None, 0
    p1_name = next(iter(sig.parameters.keys()))
    p1 = sig.parameters[p1_name]
    return p1, len(sig.parameters)


class CustomRowMixin:

    def __init__(self, *, row_class=None, row_factory=None, row_class_name="Row", **kwargs):
        """Table component used for customizing the objects returned as "Rows" from a table

        If none of "row_factory" or "row_class" are given, the classic default of a lazily created
        namedtuple, with the field names as fields.

        Args:
           - row_class: Optional, is used as the class  (or instance factory) for rows. Some introspection
        is used to guess how this class expects its parameters, if the signature includes a single *args row
        values are passed in sequence, if a **kwargs, they are passed as named arguments, if a single
        value, row values are passed as a sequence (which will work for "lists" and "tuples" as row_classes.
        If the instance is a mapping with no detectable parameters (ex. dict), fields are passed as named arguments
        as in the case of the sole **kwargs.

          - row_factory: Optional,  if given, it is lazily called with the field_names at each row instantiation,
        its return value is them used with the *args strategy: field values are passed by position.

          - row_name: only used as class name for the default namedtuple, if none of the other parameters is given.

        """
        from inspect import signature, _ParameterKind as P

        def var_positional_sequence_wrapper(*data):
            return self._row_class(*data)

        def one_param_wrapper(*data):
            return self._row_class(data)

        def var_keyword_sequence_wrapper(*data):
            return self._row_class(**{key: value for key, value in zip(self.field_names, data)})

        def input_wrapper(*args, **kw):
            if args:
                return args
            return kw.values()
        self._row_input_wrapper = input_wrapper

        #def _row_factory_wrapper(input_wrapper, output_wrapper):
        def row_factory_wrapper(input_wrapper, output_wrapper):
            def processor(*args, **kw):
                args = input_wrapper(*args, **kw)
                return output_wrapper(*args)
            return processor
        self._row_factory_wrapper = row_factory_wrapper


        self._row_class = self._row_factory = None

        if not row_factory and not row_class: # default: lazily created namedtuple
            # Default
            def row_factory(field_names):
                if not getattr(self, "_row_cls_namedtuple", None):
                    self._row_cls_namedtuple = namedtuple(row_class_name, field_names)
                return self._row_cls_namedtuple
            self._row_factory = row_factory
            self._row_class_wrapper = var_positional_sequence_wrapper
        else:

            par1, nparams = _get_param_spec(row_class)

            if par1 is None and isinstance(row_class, type) and issubclass(row_class, Mapping):  #for example, dict
                self._row_class_wrapper = var_keyword_sequence_wrapper
                self._row_class = row_class

            elif par1 and par1.kind is P.VAR_POSITIONAL:  # ex. def myrow(*args): ...
                self._row_class_wrapper = var_positional_sequence_wrapper
                self._row_class = row_class

            elif par1 and par1.kind is P.VAR_KEYWORD:  # ex. def myrow(**kwargs): ...
                self._row_class_wrapper = var_keyword_sequence_wrapper
                self._row_class = row_class

            elif nparams == 1:
                self._row_class_wrapper = one_param_wrapper
                self._row_class = row_class

            elif row_factory and not row_class:
                self._row_factory = row_factory
                self._row_class_wrapper = var_positional_sequence_wrapper

            else:
                self._row_class_wrapper = var_positional_sequence_wrapper
                self._row_class = row_class

        super().__init__(**kwargs)



    @property
    def Row(self):
        """Build a new row data from internal table data, according
        to selected class.
        """
        if self._row_factory:
            self._row_class = row_class = self._row_factory(self.field_names)
        else:
            row_class= self._row_class
        if not self._row_class_wrapper:
            return row_class
        return self._row_factory_wrapper(self._row_input_wrapper, self._row_class_wrapper)

    @property
    def row_cls(self):
        try:
            type(self[0])
        except IndexError:
            raise ValueError("Due to lazy nature of row generation, table must have at least one row of data")
