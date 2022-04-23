import pytest

#from rows.utils.query import Field
from rows.utils import query


def test_tokenize_works_for_plain_word():
    a = query.tokenize("cidade")
    assert len(a) == 1
    token = a[0]
    assert isinstance(token, query.Token)
    # NB: the specific tokens may be wrapped in a separate object per plugin soon
    # so, "FieldNameToken" will likely not be a top-level name in any file.
    assert isinstance(token, query.FieldNameToken)

@pytest.mark.parametrize("expression", [
    "cidade=='São Paulo'",
    "cidade == 'São Paulo'",
    "cidade == \"São Paulo\"",
])
def test_tokenize_works_for_short_expression(expression):
    a = query.tokenize(expression)
    assert len(a) == 3
    assert isinstance(a[0], query.FieldNameToken)
    assert isinstance(a[1], query.BinOpToken)
    assert isinstance(a[2], query.LiteralStrToken)

    assert a[2].value == "São Paulo"




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




