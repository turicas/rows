from rows.utils.query import Field

def test_field_retrieve_local_class():
    class A:
        b: int

    assert Field("A.b").cls is A


class B:
    b: int

def test_field_retrieve_global_class():
    assert Field("B.b").cls is B


def test_field_retrieve_dotted_class():
    import rows
    class C:
        b: int

    try:
        rows.plugins.dicts._monkey_patched_class = C
        assert Field("rows.plugins.dicts._monkey_patched_class.b").cls is C
    finally:
        del rows.plugins.dicts._monkey_patched_class




