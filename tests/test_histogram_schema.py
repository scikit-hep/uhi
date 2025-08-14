from __future__ import annotations

import json
import re
from pathlib import Path

import fastjsonschema
import pytest

import uhi.schema


def test_valid_schemas(valid: Path) -> None:
    with valid.open(encoding="utf-8") as f:
        data = json.load(f)
    uhi.schema.validate(data)


def test_invalid_schemas(invalid: Path) -> None:
    with invalid.open(encoding="utf-8") as f:
        data = json.load(f)

    try:
        errmsg = invalid.with_suffix(".error.txt").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        errmsg = "NO ERROR MESSAGE FILE FOUND"

    with pytest.raises(
        fastjsonschema.exceptions.JsonSchemaException, match=re.escape(errmsg)
    ):
        uhi.schema.validate(data)
