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


def test_valid_single_histogram(valid: Path) -> None:
    with valid.open(encoding="utf-8") as f:
        data = json.load(f)
    for hist in data.values():
        uhi.schema.validate(hist)


def test_invalid_single_histogram(invalid: Path) -> None:
    with invalid.open(encoding="utf-8") as f:
        data = json.load(f)
    (name, hist), *_ = data.items()

    errmsg = invalid.with_suffix(".error.txt").read_text(encoding="utf-8").strip()
    errmsg = errmsg.replace(f"data.{name}", "data", 1)

    with pytest.raises(
        fastjsonschema.exceptions.JsonSchemaException, match=re.escape(errmsg)
    ):
        uhi.schema.validate(hist)


def test_invalid_mapping_names_entry(resources: Path) -> None:
    with resources.joinpath("valid/reg.json").open(encoding="utf-8") as f:
        data = json.load(f)
    del data["two"]["storage"]

    with pytest.raises(
        fastjsonschema.exceptions.JsonSchemaException,
        match=re.escape("data.two must contain ['storage'] properties"),
    ):
        uhi.schema.validate(data)


def test_missing_uhi_schema() -> None:
    with pytest.raises(
        fastjsonschema.exceptions.JsonSchemaException,
        match=re.escape("data.bad must contain ['uhi_schema'] properties"),
    ):
        uhi.schema.validate(
            {"bad": {"axes": [], "storage": {"type": "int", "values": [1]}}}
        )


def test_mapping_value_not_object() -> None:
    with pytest.raises(
        fastjsonschema.exceptions.JsonSchemaException,
        match=re.escape("data.bad must be object"),
    ):
        uhi.schema.validate({"bad": 1})
