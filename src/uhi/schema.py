from __future__ import annotations

import functools
import json
import sys
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any

_resources = resources.files("uhi") / "resources"
histogram_file = _resources / "histogram.schema.json"
histograms_file = _resources / "histograms.schema.json"

__all__ = ["histogram_file", "histograms_file", "validate", "validate_histogram"]


def __dir__() -> list[str]:
    return __all__


def _load_local(uri: str) -> dict[str, Any]:
    """Resolve a relative ``$ref`` to a schema shipped in ``resources``."""
    with (_resources / uri).open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


@functools.cache
def _compile(name: str) -> Callable[[dict[str, Any]], None]:
    import fastjsonschema  # noqa: PLC0415

    with (_resources / name).open(encoding="utf-8") as f:
        return fastjsonschema.compile(  # type: ignore[no-any-return]
            json.load(f), handlers={"": _load_local}
        )


def validate(data: dict[str, Any]) -> None:
    """
    Validate a JSON file object against the schema.

    This accepts a dictionary of named histograms or a single histogram.
    """
    _compile("histograms.schema.json")(data)


def validate_histogram(data: dict[str, Any]) -> None:
    """Validate a single histogram (the IR) against the schema."""
    _compile("histogram.schema.json")(data)


def main(*files: str) -> None:
    """Validate histogram files."""
    import fastjsonschema  # noqa: PLC0415

    retval = 0

    for file in files:
        with Path(file).open(encoding="utf-8") as f:
            data = json.load(f)
        try:
            validate(data)
        except fastjsonschema.JsonSchemaValueException as e:
            print(f"ERROR {file}: {e.message}")  # noqa: T201
            retval = 1
        else:
            print(f"OK {file}")  # noqa: T201

    if retval:
        raise SystemExit(retval)


if __name__ == "__main__":
    main(*sys.argv[1:])
