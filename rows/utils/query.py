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

from collections.abc import Mapping, Sequence, MutableSequence
from copy import deepcopy

import enum
import numbers
import operator
import random
import re
import sys

class _sentinels(enum.Enum):
    sequence = enum.auto()
    record_not_set = enum.auto()

def ensure_query(query):
    if query is None:
        return None
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
    kwarg_registry = {}
    literal = None
    _tree_strategy = "lazy"

    def __new__(cls, value=_sentinel, **kwargs):
        """Specialized __new__ acts as a factory for whatever subclass best matches
        what is given as "value". Inheritance of subclasses, though, work as usual:
        it is just class instantiation for all subclasses that is centralized here.

        (I wonder if there is a "gang of four name" for this)
        """
        if cls is not __class__:
            # subclass is being instantiated directly
            # (may be a unpickle or deepcopy operation)
            return super().__new__(cls)

        if isinstance(value, str) and value.upper() in __class__.literal_registry:
            instance = super().__new__(__class__.literal_registry[value.upper()])
        else:
            for subcls in __class__.match_registry:
                if isinstance(value, getattr(subcls, "_accept_classes", str)) and subcls._match(value):
                    instance = super().__new__(subcls)
                    break
            else:
                raise ValueError(f"No registered token type matches {value!r}")
        # Python won't call __init__ if what __new__ returns is not an strict instance of __class__:
        instance.__init__(value, **kwargs)
        return instance

    def __init__(self, value):
        self.value = value

    def __init_subclass__(cls, *args, **kw):
        super().__init_subclass__(*args, **kw)
        if cls.literal:
            __class__.literal_registry[cls.literal.upper()] = cls
        elif "_match" in cls.__dict__:
            __class__.match_registry.append(cls)

        if "_kwarg_name" in cls.__dict__:
            __class__.kwarg_registry[cls._kwarg_name] = cls

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

    dunder_registry = {}

    right: Token = None
    left: Token = None
    boundable = False
    #bound = False

    _dunder_equiv = None

    def __init__(self, value=None):
        self.literal_value = value if value is not None else self.literal

    def __init_subclass__(cls, **kwargs):
        dunder_equiv = getattr(cls, "_dunder_equiv")
        if dunder_equiv:
            if dunder_equiv in __class__.dunder_registry:
                # TBD: add a mechanism for BinOps to be able to register subclasses
                # of themselves that can work for differnt types of binding-classes
                raise NotImplementedError(f"More than one class trying to register as {dunder_equiv}. Class {cls.__qualname__}!")
            else:
                __class__.dunder_registry[dunder_equiv] = cls
        super().__init_subclass__(**kwargs)

    @property
    def value(self):
        return self.exec()

    def exec(self):
        if self.bound == 'literal' or not self.bound:
            # used when recreating a textual representation - for example: SQL Queries
            return f"{self.left.value} {self.literal} {self.right.value}"
        return self.op(self.left.value, self.right.value)

    def __bool__(self):
        return bool(self.value)

    @property
    def bound(self):
        bright = getattr(self.right, "bound", None)
        bleft = getattr(self.left, "bound", None)
        # in each hyerachy of bound tokens, there should be just one bounding type
        # differing from falsey values and from "True", which used for literals.
        if bright and bleft:
            return bright if not isinstance(bright, bool) else bleft
        return False

class EqualToken(BinOpToken):
    precedence = 0
    literal = "="
    op = operator.eq
    _dunder_equiv = "__eq__"
    _kwarg_name = "eq"

class GreaterToken(BinOpToken):
    precedence = 0
    literal = ">"
    op = operator.gt
    _dunder_equiv = "__gt__"
    _kwarg_name = "gt"

class LessToken(BinOpToken):
    precedence = 0
    literal = "<"
    op = operator.lt
    _dunder_equiv = "__lt__"
    _kwarg_name = "lt"

class GreaterEqualToken(BinOpToken):
    precedence = 0
    literal = ">="
    op = operator.ge
    _dunder_equiv = "__ge__"
    _kwarg_name = "ge"

class LessEqualToken(BinOpToken):
    precedence = 0
    literal = "<="
    op = operator.le
    _dunder_equiv = "__le__"
    _kwarg_name = "le"

class AddToken(BinOpToken):
    precedence = 2
    literal = "+"
    op = operator.add
    _dunder_equiv = "__add__"

class SubToken(BinOpToken):
    precedence = 2
    literal = "-"
    op = operator.sub
    _dunder_equiv = "__sub__"

class MulToken(BinOpToken):
    precedence = 3
    literal = "*"
    op = operator.mul
    _dunder_equiv = "__mul__"

class DivToken(BinOpToken):
    precedence = 3
    literal = "/"
    op = operator.truediv
    _dunder_equiv = "__truediv__"

class ModToken(BinOpToken):
    precedence = 3
    literal = "%"
    op = operator.mod
    _dunder_equiv = "__mod__"

class MatchToken(BinOpToken):
    precedence = 3
    literal = "^"
    op = staticmethod(lambda string, regexp: bool(re.search(regexp, string)))  # Order is reversed so that kwarg form works out of the box
    _dunder_equiv = "__xor__"
    _kwarg_name = "match"


class SequenceAssembler(BinOpToken):
    _tree_strategy = "eager"
    precedence = -0.5
    literal = ","
    op = staticmethod(lambda left, right: (left if isinstance(left, SequenceToken) else SequenceToken([left])).curry_append(right))
    @property
    def right(self):
        return getattr(self, "_right", _sentinels.sequence)
    @right.setter
    def right(self, value):
        self._right = value
    @right.deleter
    def right(self):
        del self._right

class AndToken(BinOpToken):
    precedence = -1
    literal = "AND"
    op = staticmethod(lambda a, b: a and b)
    _dunder_equiv = "__and__"  # not quite. TBD: double check implementation

class OrToken(BinOpToken):
    precedence = -2
    literal = "OR"
    op = staticmethod(lambda a, b: a or b)
    _dunder_equiv = "__or__"  # not quite. TBD: double check implementation



class SequenceToken(Token, MutableSequence):
    _accept_classes = Sequence
    def __init__(self, value=_sentinels.sequence):
        self.data = []
        self.extend(value)

    @classmethod
    def _match(cls, value):
        return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))

    def curry_append(self, item):
        if item is _sentinels.sequence:
            return self
        if not isinstance(item, Token):
            item = Token(item)
        self.data.append(item)
        return self

    def __getitem__(self, index):
        return self.data[index]

    def _check_and_convert(self, item, index=None):
        if item is _sentinels.sequence or isinstance(index, slice) and isinstance(item, Sequence) and any(element is _sentinels.sequence for element in item):
            raise ValueError("Can't add special sentinel object to sequence")
        if not isinstance(item, Token):
            item = Token(item)
        return item

    def __setitem__(self, index, item):
        item = self._check_and_convert(item, index)
        self.data[index] = item

    def __delitem__(self, index):
        del self.data[index]

    def insert(self, index, item):
        item = self._check_and_convert(item, index)
        self.data.insert(index, item)

    def __len__(self):
        return len(self.data)

    @property
    def value(self):
        return self

    def __repr__(self):
        return f"{self.__class__.__name__}([{', '.join(repr(item) for item in self)}])"


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
        # TODO: check if all params are bound or return string form.
        return self.op(*(param.value for param in self.params))

# TODO: find a way for Function Tokens to "self document".
# An ordinary function can yield all valid fixed-literal tokens
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


class OperableToken(Token):
    # ATTENTION: this class body must be run only after all BinOps Tokens had been defined
    # TBD: mechanism to allow other dunder methods to be registered late for extra operators
    # TBD: Some FunctionTokens should really work as operators (e.g. "NotToken"). Implementation missing.

    # Generate programatically methods which allow use of this class with operators
    # to create lazily boundable and calculatable Query objects!

    def _multi_dunder(self, TokenCls, other):
        if not isinstance(other, Token):
            other = Token(other)
        return Query.from_tokens([self, TokenCls(TokenCls.literal), other])

    def _bind(cls_namespace, dunder_name, multi_dunder, TokenCls):
        # We need an extra closure, because the class body namespace is not
        # captured as a closure for functions defined here. So, method
        # created to actually perform the operation would not be able to "see"
        # the "_multi_dunder" function
        cls_namespace[dunder_name] = lambda self, other: multi_dunder(self, TokenCls, other)


    for dunder_name, TokenCls in BinOpToken.dunder_registry.items():
        _bind(locals(), dunder_name, _multi_dunder, TokenCls)

    # TBD: bind reverse methods for the bin-ops. (__rsub__ and so on)

    del _bind  # _multi_dunder is considered as possibly usefull and will not be deleted.


# IMPORTANT: Do not change declaration order of classes that do not declare a "literal" field:
# textual token match is done in-order, so, if messed up, all numbers could finish up
# as string-literals, for example.
class LiteralToken(OperableToken):
    bound = True

class FieldNameToken(OperableToken):
    boundable = True  # this attribute is used in Query.bind
    _bound = False

    @property
    def value(self):
        if not self.bound or self.bound == "literal":
            return self.name
        container = self.parent.filtering_strategy
        if container is _sentinels.record_not_set:
            return self.name
        return container.get(self.name)

    @value.setter
    def value(self, value):
        if getattr(self, "parent", None):
            raise RuntimeError("Node value can't be changed after it is bound to a Queryable instance")
        self.name = value

    @classmethod
    def _match(cls, value):
        return re.match(r"\w+", value) and not value[0].isdigit()

    @property
    def bound(self):
        if hasattr(self, "parent"):
            strategy = getattr(self.parent, "filtering_strategy", _sentinels.record_not_set)
            return (strategy is not _sentinels.record_not_set) and self._bound
        return False

    @bound.setter
    def bound(self, value):
        self._bound = value



# alias for building expressions
F = FieldNameToken  # NoQA


class LiteralIntToken(LiteralToken):
    _accept_classes = (str, numbers.Integral)
    def __init__(self, value):
        self.value = self._parse(value)

    @classmethod
    def _parse(self, value):
        # may raise ValueError or AttributeError: will be catched on "_match"
        if isinstance(value, numbers.Integral):
            return value
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
        except (ValueError, AttributeError):
            return False
        return True
        # return re.match(r"^-?[0-9_]+$", value)


class LiteralFloatToken(LiteralToken):
    _accept_classes = (str, numbers.Real)
    def __init__(self, value):
        self.value = float(value) if not isinstance(value, numbers.Real) else value

    @classmethod
    def _match(cls, value):
        # Do not accept alphanumeric only tokens as numbers,
        # even though they are valid floats
        if isinstance(value, numbers.Real):
            return value
        if value.lower().strip("-") in ("nan", "inf"):
            return False
        try:
            float(value)
        except ValueError:
            return False
        return True


class LiteralStrToken(LiteralToken):
    boundable = True

    def __init__(self, value, strip=True):

        # Sometimes this will be called by Token.__new__ after matching a quoted string.
        # sometimes it may be called directly, with nothing to strip
        if strip and value and value[0] not in "\"'" and value[-1] not in "\"'":
            strip = False
        self._value = value[1:-1] if strip else value

    @classmethod
    def _match(cls, value):
        return re.match(r"""(?P<quote>['"]).*?(?P=quote)""", value)

    @property
    def value(self):
        if self.bound == "literal":
            return repr(self._value)
        return self._value


def tokenize(query:str) -> "list[Token]":
    tokens =  [Token(g[0]) for g in re.findall(
        r"""(OR|AND|-?[0-9]+\.[0-9]*(e-?[0-9]+)?|0[xob][0-9a-f_]+|-?[0-9_]+|[a-z]\w+|((?P<quote>['"]).*?(?P=quote))|(?<=[^!><])=|<|>|>=|<=|\+|\*|\(|\)|/|-|\^|,)""",
        query, flags=re.IGNORECASE)]
    return tokens


def build_tokens_from_kwargs(kwargs):
    """Convert a dict with keys composed of "fieldnames__operator" into a token sequence

    Given a dictionary containing django-like operations for fields return
    a token sequence ready to be transformed into a Tree by TokenTree.from_tokens

    Used internaly from Query.__init__
    """
    token_dict = Token.kwarg_registry
    expression_seq = []
    for full_name, value in kwargs.items():
        if "__" in full_name:
            field_name, operator = full_name.rsplit("__", 1)
        else:
            field_name = full_name
            operator = "eq"
        field_token = Token(field_name)
        op_token = token_dict[operator]()
        literal_token = Token(value) if not isinstance(value, str) else LiteralStrToken(value, strip=False)
        expression_seq.extend((field_token, op_token, literal_token, AndToken()))
    expression_seq.pop()
    return expression_seq



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
            if root._tree_strategy == "eager":
                root = root.value
        return root


    @classmethod
    def from_tokens(cls, tokens: "list[Token]") -> "TokenTree":
        if not tokens:
            return None
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

    bound = False

    def __init__(self, **kwargs):
        """A new query can be created from keyword-style operation specifictions:

        The first part of a keywoerd argumend will match a column name (or other lazily
        evaluable target) on the class the query will eventually be bound to.
        If passed as "=" it means that it will filter for that exact mach for that attribute.

        Otherwise, separated from the column name by two underscores, an operator name can be
        given - and that operator will be used to filter the records, using the argument assigned
        in the keyword parameter as the other operand,.

        Example:  `mytable.filter = Query(inhabitants__ge = 1_000_000)" will filter mytable
        making only the rows where the inhabitants colums is greater or equal than 1 million visible.

        Valid operators are:
            ge, gt, le, lt, eq (same as no suffix).

        Given keyword parameters are combined as an "and" clause.

        Queries can also be created by creating first a "Filter" object
        (rows.utils.query.F) with a column name, and then using normal Python
        expressions where the F instance is an operand.

        A third way: one may call rows.utils.ensure_query with a string
        representing the Query. Literal strings should be enclosed in single quotes
        inside such a string, and unquoted names are taken as column names.

        "ensure_query" is called automatically in all (or most) places a Query
        can be bound to a Table or other objectr, so one might just do:
        `mytable.filter = "inhabitants > 1_000_000" `
        for the same effect as above.
        """
        token_seq = build_tokens_from_kwargs(kwargs)
        self.root = self.node_tree_from_tokens(token_seq)


    def bind(self, parent):
        binding_type = getattr(parent, "filter_binding_type", True)
        self = deepcopy(self)
        self.parent = parent
        self.bound = binding_type
        self._bind_nodes(self.root)
        return self

    def _bind_nodes(self, node):
        if getattr(node, "boundable", False):
            node.parent = self.parent
            node.bound = self.bound
        if getattr(node, "left", None):
            self._bind_nodes(node.left)
        if getattr(node, "right", None):
            self._bind_nodes(node.right)
        if getattr(node, "params", ()):
            for child_node in node.params:
                self._bind_nodes(child_node)

    def __bool__(self):
        return bool(self.root)

# Why do we need "QueryBase"?
# something is just telling me we might want to hook
# some stuff here, or specialize Queries in a
# different way.

class Query(QueryBase):
    pass


Q = Query


class QueryableMixin:

    # @abstractmethod
    @property
    def filtering_strategy(self):
        """ concrete mixins must implement this as a property
        that returns an object with a "get" that will take the column
        name as sole parameter.

        The default, per record implementation, just returns "current_record",
        which must be set in raw "__iter__".
        """
        return self.current_record

    @property
    def current_record(self):
        """Property used in eager, per-record filtering strategy (i.e. in memory list of sequences Tables)

        its value should be set, inside  __iter__'s  loop for unfiltered rows, to
        an object featuring a "get" method for column names in each record.
        """
        return getattr(self, "_current_record",  _sentinels.record_not_set)


    @current_record.setter
    def current_record(self, value):
        self._current_record = value
