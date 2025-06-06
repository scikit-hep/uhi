from __future__ import annotations

import json
from pathlib import Path

import pytest

import uhi.io.json

DIR = Path(__file__).parent.resolve()

VALID_FILES = DIR.glob("resources/valid/*.json")


@pytest.mark.parametrize("filename", VALID_FILES, ids=lambda p: p.name)
def test_valid_json(filename: Path) -> None:
    data = filename.read_text(encoding="utf-8")
    hist = json.loads(data, object_hook=uhi.io.json.object_hook)
    redata = json.dumps(hist, default=uhi.io.json.default)

    rehist = json.loads(redata, object_hook=uhi.io.json.object_hook)
    assert redata.replace(" ", "").replace("\n", "") == data.replace(" ", "").replace(
        "\n", ""
    )

    assert hist.keys() == rehist.keys()


def test_reg_load() -> None:
    data = DIR / "resources/valid/reg.json"
    hists = json.loads(
        data.read_text(encoding="utf-8"), object_hook=uhi.io.json.object_hook
    )
    one = hists["one"]
    two = hists["two"]

    assert one["metadata"] == {"one": True, "two": 2, "three": "three"}

    assert len(one["axes"]) == 1
    assert one["axes"][0]["type"] == "regular"
    assert one["axes"][0]["lower"] == pytest.approx(0)
    assert one["axes"][0]["upper"] == pytest.approx(5)
    assert one["axes"][0]["bins"] == 3
    assert one["axes"][0]["underflow"]
    assert one["axes"][0]["overflow"]
    assert not one["axes"][0]["circular"]

    assert one["storage"]["type"] == "int"
    assert one["storage"]["values"] == pytest.approx([1, 2, 3, 4, 5])

    assert len(two["axes"]) == 1
    assert two["axes"][0]["type"] == "regular"
    assert two["axes"][0]["lower"] == pytest.approx(0)
    assert two["axes"][0]["upper"] == pytest.approx(5)
    assert two["axes"][0]["bins"] == 5
    assert two["axes"][0]["underflow"]
    assert two["axes"][0]["overflow"]
    assert not two["axes"][0]["circular"]

    assert two["storage"]["type"] == "double"
    assert two["storage"]["values"] == pytest.approx([1, 2, 3, 4, 5, 6, 7])
