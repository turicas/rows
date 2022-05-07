import pytest

#from rows.utils.query import Field
from rows.utils import query
from rows import Table, FlexibleTable, SQLiteTable
import rows


def test_tokenize_works_for_plain_word():
    a = query.tokenize("cidade")
    assert len(a) == 1
    token = a[0]
    assert isinstance(token, query.Token)
    # NB: the specific tokens may be wrapped in a separate object per plugin soon
    # so, "FieldNameToken" will likely not be a top-level name in any file.
    assert isinstance(token, query.FieldNameToken)


@pytest.mark.parametrize("expression", [
    "cidade='São Paulo'",
    "cidade = 'São Paulo'",
    "cidade = \"São Paulo\"",
])
def test_tokenize_works_for_short_expression(expression):
    a = query.tokenize(expression)
    assert len(a) == 3
    assert isinstance(a[0], query.FieldNameToken)
    assert isinstance(a[1], query.BinOpToken)
    assert isinstance(a[2], query.LiteralStrToken)

    assert a[2].value == "São Paulo"


def test_ensure_query_builds_tree_for_simple_expression():
    tree = query.ensure_query("2 + 3")
    assert tree.value == 5

def test_ensure_query_builds_tree_for_2ops_expression():
    tree = query.ensure_query("2 + 3 + 5")
    assert tree.value == 10

@pytest.mark.parametrize("expression,expected", [
    ("2 + 3 * 3", 11),
    ("2 * 3 + 3", 9),
    ("2 * (3 + 3)", 12),
    ("(2 + 2) * 3 + (3 * 3)", 21),
    ("(2 + 2) * 3 = 3 * 3 + 3", True),
    ("20 > 10", True),
    ("20 >= 10", True),
    ("20 < 10", False),
    ("20 <= 10", False),
    ("1 or 0", True),
    ("1 and 0", False),
    ("1 and 0 or 1", True),
    ("1 or 0 and 1", True),
    ("2 + 3 = 5 and 3 * 3 = 9", True),
    ("'estado'='estado'", True),
    ("'state'='state' and 6000>5000", True),
    ("'banana' ^ 'b.n.n.'", True), #regexp "match" operator (actually re.search)
])

def test_ensure_query_tree_for_expression_observes_precedence(expression, expected):
    tree = query.ensure_query(expression)
    assert tree.value == expected

@pytest.mark.parametrize(("input, expected"), [
    ([42], [42]),
    ([23, 42], [23,42]),
    ([5, 23, 42], [5, 23,42]),
    ((23, 42), [23,42]),
    ((23, 42), [23,42]),
    (bytearray((23, 42)), [23,42]),
    ("42,", [42,]),
    ("23, 42", [23,42]),
    ("23, 42, 55", [23, 42, 55]),
    ("5, 23, 42, 55", [5, 23, 42, 55]),
    ("(23, 42)", [23,42]),
    ("5, 23 + 42, 55", [5, 65, 55]),
    ]
)
def test_sequence_token_creation(input, expected):
    if isinstance(input, str):
        token = query.ensure_query(input).root
    else:
        token = query.Token(input)
    assert token == expected


def test_query_tree_is_deepcopiable():
    from copy import deepcopy

    t = query.ensure_query("2 + 3")
    t1 = deepcopy(t)
    assert t.value == t1.value
    t.root.left.value = 10
    assert t.value != t1.value


@pytest.mark.parametrize("TokenCls",[
    query.Token,
    query.LiteralIntToken,
    ]
)
@pytest.mark.parametrize("in_value", [
    "10",
    "0x0a",
    "0b1010",
    "0o12",
    10,
    ]
)
def test_literalinttoken_is_built_from_proper_values(TokenCls, in_value):
    t = TokenCls(in_value)
    assert t.__class__ == query.LiteralIntToken
    assert t.value == 10


@pytest.mark.parametrize("TokenCls",[
    query.Token,
    query.LiteralFloatToken,
    ]
)
@pytest.mark.parametrize("in_value", [
    "0.1",
    "10e-2",
    "0.100",
    0.1,
    ]
)
def test_literalinttoken_is_built_from_proper_values(TokenCls, in_value):
    t = TokenCls(in_value)
    assert t.__class__ == query.LiteralFloatToken
    assert t.value == 0.1


@pytest.fixture
def city_table_data():
    fields={ "state": rows.fields.TextField, "city": rows.fields.TextField, "inhabitants": rows.fields.IntegerField, "area": rows.fields.FloatField}
    data = [
        ['SP', 'Buritizal', 4053, 266.42],
        ['SP', 'Campina do Monte Alegre', 5567, 185.03],
        ['SP', 'Canas', 4385, 53.26],
        ['SP', 'Dolcinópolis', 2096, 78.34],
        ['SP', 'Dracena', 43258, 488.04],
        ['SP', 'Garça', 43115, 555.63],
        ['SP', 'Guarulhos', 1221979, 318.68],
        ['SP', 'Irapuru', 7789, 214.9],
        ['SP', 'Quatá', 12799, 650.37],
        ['SP', 'Rosana', 19691, 742.87],
        ['SP', 'Santa Albertina', 5723, 272.77],
        ['SP', 'São João do Pau d`Alho', 2103, 117.72],
        ['SP', 'Torrinha', 9330, 315.27],
        ['SP', 'Valinhos', 106793, 148.59]
    ]

    return fields, data

@pytest.fixture
def city_table(city_table_data):
    t = Table(city_table_data[0])
    t.extend(city_table_data[1])
    return t

@pytest.mark.parametrize("table_class", [Table, FlexibleTable, SQLiteTable])
def test_table_is_filterable_by_query(table_class, city_table_data):
    city_table = table_class(city_table_data[0])
    city_table.extend(city_table_data[1])
    assert len(city_table) > 1
    city_table.filter = query.ensure_query("inhabitants=5723")
    assert len(city_table) == 1


def test_filtered_table_is_iterable(city_table):
    city_table.filter = query.ensure_query("inhabitants=5723")
    assert len(list(city_table)) == 1


def test_can_build_query_programatically(city_table):
    from rows.utils.query import F, Query
    query = F("inhabitants") > 1_000_000
    assert isinstance(query, Query)

    city_table.filter = query
    assert len(city_table) == 1


# [WIP]
def test_programatic_query_works_with_reversed_ops(city_table):
    from rows.utils.query import F, Query
    query = 1_000_000 < F("inhabitants")
    assert isinstance(query, Query)

    city_table.filter = query
    assert len(city_table) == 1

@pytest.mark.parametrize("kwarg,value,expected_rows", [
    ("inhabitants", 5723, 1),
    ("inhabitants", 12341234, 0),
    ("inhabitants__eq", 5723, 1),
    ("inhabitants__gt", 1_000_000, 1),
    ("inhabitants__lt", 1_000_000, 13),
    ("inhabitants__ge", 1_221_979, 1),
    ("inhabitants__le", 1_221_979, 14),
    ("city", "Guarulhos", 1),
    ("city__match", "r[iu]", 4)
    ]
)
def test_kwarg_query_works_with_single_filter(kwarg, value, expected_rows, city_table):
    from rows.utils.query import Query
    query = Query(**{kwarg: value})
    city_table.filter = query
    assert len(city_table) == expected_rows


def test_kwarg_query_works_with_combining_filters(city_table):
    from rows.utils.query import Query
    city_table.filter = Query(inhabitants__ge = 100_000, inhabitants__le = 200_000)
    assert len(city_table) == 1



