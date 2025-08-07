from __future__ import annotations

import functools
import json
import sys
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any

histogram_file = resources.files("uhi") / "resources/histogram.schema.json"

__all__ = ["histogram_file", "validate"]


def __dir__() -> list[str]:
    return __all__


@functools.cache
def _histogram_schema() -> Callable[[dict[str, Any]], None]:
    import fastjsonschema  # noqa: PLC0415

    with histogram_file.open(encoding="utf-8") as f:
        return fastjsonschema.compile(json.load(f))  # type: ignore[no-any-return]


def validate(data: dict[str, Any]) -> None:
    """Validate a histogram object against the schema."""
    validate = _histogram_schema()
    validate(data)


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
