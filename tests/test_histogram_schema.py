from __future__ import annotations

from pathlib import Path

import uhi.schema

DIR = Path(__file__).parent.resolve()


def test_example_1() -> None:
    uhi.schema.validate(DIR / "resources/reg.json")
