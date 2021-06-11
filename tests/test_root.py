import pytest

ROOT = pytest.importorskip("ROOT")


def test_root_imported() -> None:
    assert ROOT.TString("hi") == "hi"
