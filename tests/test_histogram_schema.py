from __future__ import annotations

import json
import re
from pathlib import Path

import fastjsonschema
import pytest

import uhi.schema

DIR = Path(__file__).parent.resolve()

VALID_FILES = DIR.glob("resources/valid/*.json")
INVALID_FILES = DIR.glob("resources/invalid/*.json")


@pytest.mark.parametrize("filename", VALID_FILES, ids=lambda p: p.name)
def test_valid_schemas(filename: Path) -> None:
    with filename.open(encoding="utf-8") as f:
        data = json.load(f)
    uhi.schema.validate(data)


@pytest.mark.parametrize("filename", INVALID_FILES, ids=lambda p: p.name)
def test_invalid_schemas(filename: Path) -> None:
    with filename.open(encoding="utf-8") as f:
        data = json.load(f)

    try:
        errmsg = filename.with_suffix(".error.txt").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        errmsg = "NO ERROR MESSAGE FILE FOUND"

    with pytest.raises(
        fastjsonschema.exceptions.JsonSchemaException, match=re.escape(errmsg)
    ):
        uhi.schema.validate(data)
