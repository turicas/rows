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
import random
import sys

from collections.abc import Mapping

def ensure_query(query):
    if isinstance(query, str):
        tokens = tokenize(query)
        return Query.from_tokens(tokens)
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

_sentinel = object()

class Token:
    # these are not just "tokens": they will also be structured as Query tree nodes, and perform ops.
    literal_registry = {}
    match_registry = []
    literal = None

    def __new__(cls, value=_sentinel):
        """Specialized __new__ acts as a factory for whatever subclass best matches
        what is given as "value". Inheritance of subclasses, though, work as usual:
        it is just class instantiation for all subclasses that is centralized here.

        (I wonder if there is a "gang of four name" for this)
        """
        if cls is not __class__:
            # subclass is being instantiated directly
            # (may be a unpickle or deepcopy operation)
            return super().__new__(cls)

        if value.upper() in __class__.literal_registry:
            instance = super().__new__(__class__.literal_registry[value.upper()])
        else:
            for subcls in __class__.match_registry:
                if subcls._match(value):
                    instance = super().__new__(subcls)
                    break
            else:
                raise ValueError(f"No registered token type matches {value!r}")
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

    def exec(self):
        return self.value

    def __repr__(self):
        return f"{self.__class__.__name__}({getattr(self, 'literal_value', None) or self.value!r})"


class OpenBracketToken(Token):
    literal = "("


class CloseBracketToken(Token):
    literal = ")"


class BinOpToken(Token):
    right: Token = None
    left: Token = None

    def __init__(self, value):
        self.literal_value = value

    @property
    def value(self):
        return self.exec()

    def exec(self):
        return self.op(self.left.value, self.right.value)


class EqualToken(BinOpToken):
    precedence = 0
    literal = "=="
    op = operator.eq

class GreaterToken(BinOpToken):
    precedence = 0
    literal = ">"
    op = operator.gt

class LessToken(BinOpToken):
    precedence = 0
    literal = "<"
    op = operator.lt

class GreaterEqualToken(BinOpToken):
    precedence = 0
    literal = ">="
    op = operator.ge

class LessEqualToken(BinOpToken):
    precedence = 0
    literal = "<="
    op = operator.le

class AddToken(BinOpToken):
    precedence = 2
    literal = "+"
    op = operator.add

class SubToken(BinOpToken):
    precedence = 2
    literal = "-"
    op = operator.sub

class MulToken(BinOpToken):
    precedence = 3
    literal = "*"
    op = operator.mul

class DivToken(BinOpToken):
    precedence = 3
    literal = "/"
    op = operator.truediv

class ModToken(BinOpToken):
    precedence = 3
    literal = "%"
    op = operator.mod

class AndToken(BinOpToken):
    precedence = -1
    literal = "AND"
    op = staticmethod(lambda a, b: a and b)

class OrToken(BinOpToken):
    precedence = -2
    literal = "OR"
    op = staticmethod(lambda a, b: a or b)


class FunctionToken(Token):
    """Pre-defined function literals
    that may work with as unary operators
    (if taking a single parameter) -
    or can consume nparams of the token stream.
    Consumed parameters are kept in a linear order and skipped
    from being folded in the operations tree
    """

    nparams = 1
    literal: str
    params: "Sequence[Token]" = ()

    def __init__(self, value):
        pass

    @property
    def value(self):
        if not self.params:
            return f"{self.__class__.__name__}()"
        return self.op(*(param.value for param in self.params))

# TODO: find a way for Function Tokens to "self document".
# An ordianry function can yield all valid fixed-literal tokens
# by inspecting the Token class registries
class NotToken(FunctionToken):
    """1 ARG, inverts the boolean value of its argument"""
    literal = "NOT"
    def op(self, value):
        return not value

class SampleToken(FunctionToken):
    """1 ARG: chance of any given row being selected. SAMPLE 0.1 ~= roughly 10% of rows returned, at random"""
    literal = "SAMPLE"
    def op(self, value):
        return random.random() < value


# IMPORTANT: Do not change declaration order of classes that do not declare a "literal" field:
# textual token match is done in-order, so, if messed up, all numbers could finish up
# as string-literals, for example.

class LiteralToken(Token):
    pass


class FieldNameToken(Token):
    boundable = True  # this attribute is used in Query.bind

    @property
    def value(self):
        if getattr(self, "parent", None) is None:
            return self.name
        return self.parent.current_record.get(self.name)

    @value.setter
    def value(self, value):
        if getattr(self, "parent", None):
            raise RuntimeError("Node value can't be changed after it is bound to a Queryable instance")
        self.name = value

    @classmethod
    def _match(cls, value):
        return re.match(r"\w+", value) and not value[0].isdigit()

class LiteralIntToken(LiteralToken):
    def __init__(self, value):
        self.value = self._parse(value)

    @classmethod
    def _parse(self, value):
         # may raise ValueError: will be catched on "_match"
        base = 10
        value = value.lower()
        if len(value) > 2 and value[0] == "0":
            base = 16 if value[1] == "x" else 2 if value[1] == "b" else 8 if value[1] == "o" else 10
            if base == 10:
                value = value.lstrip("0")
            else:
                value = value[2:]
        return int(value, base)


    @classmethod
    def _match(cls, value):
        try:
            cls._parse(value)
        except ValueError:
            return False
        return True
        # return re.match(r"^-?[0-9_]+$", value)


class LiteralFloatToken(LiteralToken):
    def __init__(self, value):
        self.value = float(value)

    @classmethod
    def _match(cls, value):
        # Do not accept alphanumeric only tokens as numbers,
        # even though they are valid floats
        if value.lower().strip("-") in ("nan", "inf"):
            return False
        try:
            float(value)
        except ValueError:
            return False
        return True

class LiteralStrToken(Token):
    def __init__(self, value):
        self.value = value[1:-1]

    @classmethod
    def _match(cls, value):
        return re.match(r"""(?P<quote>['"]).*?(?P=quote)""", value)


def tokenize(query:str) -> "list[Token]":
    tokens =  [Token(g[0]) for g in re.findall(
        r"""(OR|AND|-?[0-9]+\.[0-9]*(e-?[0-9]+)?|0[xob][0-9a-f_]+|-?[0-9_]+|[a-z]\w+|((?P<quote>['"]).*?(?P=quote))|==|<|>|>=|<=|\+|\*|\(|\)|/|-)""",
        query, flags=re.IGNORECASE)]
    return tokens


class TokenTree:

    @classmethod
    def node_tree_from_tokens(cls, tokens: "list[Token]") -> Token:

        # identify and collapse subtrees recursively
        depth = 0
        subtree = None
        new_tokens = []
        for token in tokens:
            if isinstance(token, OpenBracketToken):
                depth += 1
                if depth == 1:
                    subtree = []
                    continue
            elif isinstance(token, CloseBracketToken):
                if depth == 0:
                    raise ValueError(f"Unbalanced parentheses in token sequence {tokens}")
                depth -= 1
                if depth == 0:
                    new_tokens.append(TokenTree.node_tree_from_tokens(subtree))
                    subtree = None
                    continue
            if depth == 0:
                new_tokens.append(token)
            else:
                subtree.append(token)
        if subtree:
            raise ValueError(f"Unbalanced parentheses in token sequence {tokens}")
        tokens = new_tokens

        # Feed function tokens:
        new_tokens = []
        last_function = []
        chomping = 0
        for token in tokens:
            if chomping:
                last_function[-1][0].params.append(token)
                chomping -= 1
                if chomping == 0:
                    _, chomping = last_function.pop()
            else:
                new_tokens.append(token)
            if isinstance(token, FunctionToken):
                last_function.append((token, chomping))
                token.params = []
                chomping = token.nparams
        if chomping:
            raise ValueError(f"Missing parameters in {last_function[-1].literal} function call in token sequence {tokens}")

        tokens = new_tokens

        # Fold binary operators for remaining tokens into a tree:

        if len(tokens) == 1:
            root = tokens[0]
        elif len(tokens) > 1:
            if not all(isinstance(token, BinOpToken) for token in tokens[1::2]):
                raise ValueError(f"Malformed token stream {tokens}")
            while len(tokens) > 3:
                if tokens[1].precedence >= tokens[3].precedence:
                    tokens = [TokenTree.node_tree_from_tokens(tokens[0:3]), *tokens[3:]]
                else:
                    tokens = [*tokens[0:2], TokenTree.node_tree_from_tokens(tokens[2:])]

            root = tokens[1]
            root.left = tokens[0]
            root.right = tokens[2]
        return root


    @classmethod
    def from_tokens(cls, tokens: "list[Token]")-> "TokenTree":
        self = cls.__new__(cls)
        root = cls.node_tree_from_tokens(tokens)
        self.root = root
        return self


    @property
    def value(self):
        return self.root.value

    def exec(self):
        return self.root.value


class QueryBase(TokenTree):
    def bind(self, parent):
        self = deepcopy(self)
        self.parent = parent
        self._bind_nodes(self.root)
        return self

    def _bind_nodes(self, node):
        if getattr(node, "boundable", False):
            node.parent = self.parent
        if getattr(node, "left", None):
            self._bind_nodes(node.left)
        if getattr(node, "right", None):
            self._bind_nodes(node.right)
        if getattr(node, "params", ()):
            for child_node in node.params:
                self._bind_nodes(child_node)

class Query(QueryBase):
    pass


class QueryableMixin:
    @property
    def current_record(self):
        """Property used in eager, per-record filtering strategy (i.e. in memory list of sequences Tables)

        its value should be set, inside a __getitem__ loop for rows,
        for a mapping for the current row.
        """
        return self._current_record

    @current_record.setter
    def current_record(self, value):
        self._current_record = value
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

