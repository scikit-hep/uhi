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
def _histogram_schema() -> Callable[[Any], None]:
    """
    Compile a validator for a single histogram.

    The schema file accepts either one histogram or a mapping of names to
    histograms. The mapping form is handled in :func:`validate` so that errors
    name the failing entry instead of the whole ``oneOf``.
    """
    import fastjsonschema  # noqa: PLC0415

    with histogram_file.open(encoding="utf-8") as f:
        schema = json.load(f)

    single = {"$ref": "#/$defs/histogram", "$defs": schema["$defs"]}
    return fastjsonschema.compile(single)  # type: ignore[no-any-return]


def validate(data: dict[str, Any]) -> None:
    """
    Validate a histogram object against the schema.

    ``data`` is either a single histogram (has a ``uhi_schema`` key) or an
    object mapping names to histograms.
    """
    import fastjsonschema  # noqa: PLC0415

    validator = _histogram_schema()

    # Loaded JSON can be any type; let the validator report a non-object.
    if not isinstance(data, dict) or "uhi_schema" in data:  # type: ignore[redundant-expr]
        validator(data)
        return

    for name, hist in data.items():
        try:
            validator(hist)
        except fastjsonschema.JsonSchemaValueException as e:
            path = f"data.{name}{e.name.removeprefix('data')}"
            raise fastjsonschema.JsonSchemaValueException(
                e.message.replace(e.name, path, 1),
                value=e.value,
                name=path,
                definition=e.definition,
                rule=e.rule,
            ) from None


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
