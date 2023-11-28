from __future__ import annotations

import json
import sys
from pathlib import Path

import fastjsonschema

if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources

histogram_file = resources.files("uhi") / "resources/histogram.schema.json"

with histogram_file.open(encoding="utf-8") as f:
    histogram_schema = fastjsonschema.compile(json.load(f))


def validate(path: str | Path) -> None:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        example = json.load(f)

    histogram_schema(example)


if __name__ == "__main__":
    validate(*sys.argv[1:])
