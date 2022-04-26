import pytest

#from rows.utils.query import Field
from rows.utils import query
from rows import Table, FlexibleTable
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
    ("estado='estado'", True),
    ("state='state' and 6000>5000", True)
])

def test_ensure_query_tree_for_expression_observes_precedence(expression, expected):
    tree = query.ensure_query(expression)
    assert tree.value == expected


def test_query_tree_is_deepcopiable():
    from copy import deepcopy

    t = query.ensure_query("2 + 3")
    t1 = deepcopy(t)
    assert t.value == t1.value
    t.root.left.value = 10
    assert t.value != t1.value


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

@pytest.mark.parametrize("table_class", [Table, FlexibleTable])
def test_table_is_filterable_by_query(table_class, city_table_data):
    city_table = table_class(city_table_data[0])
    city_table.extend(city_table_data[1])
    assert len(city_table) > 1
    city_table.filter = query.ensure_query("inhabitants=5723")
    assert len(city_table) == 1


def test_filtered_table_is_iterable(city_table):
    city_table.filter = query.ensure_query("inhabitants=5723")
    assert len(list(city_table)) == 1


#######################
# maybe these will be ressurected when coding for programatic queries
# most likely they are just garbage now:

@pytest.mark.skip
def test_field_retrieve_local_class():
    class A:
        b: int

    assert Field("A.b").cls is A


class B:
    b: int

@pytest.mark.skip
def test_field_retrieve_global_class():
    assert Field("B.b").cls is B


@pytest.mark.skip
def test_field_retrieve_dotted_class():
    import rows
    class C:
        b: int

    try:
        rows.plugins.dicts._monkey_patched_class = C
        assert Field("rows.plugins.dicts._monkey_patched_class.b").cls is C
    finally:
        del rows.plugins.dicts._monkey_patched_class




