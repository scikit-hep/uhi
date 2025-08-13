from __future__ import annotations

from uhi.io import remove_writer_info


def test_remove_writer_info() -> None:
    d = {"uhi_schema": 1, "writer_info": {"a": {"foo": "bar"}, "b": {"FOO": "BAR"}}}

    assert remove_writer_info(d, library=None) == {"uhi_schema": 1}
    assert remove_writer_info(d, library="a") == {
        "uhi_schema": 1,
        "writer_info": {"b": {"FOO": "BAR"}},
    }
    assert remove_writer_info(d, library="b") == {
        "uhi_schema": 1,
        "writer_info": {"a": {"foo": "bar"}},
    }
    assert remove_writer_info(d, library="c") == d
