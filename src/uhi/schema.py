from __future__ import annotations

import json
import sys

import fastjsonschema

if sys.version_info < (3, 9):
    import importlib_resources as resources
else:
    from importlib import resources

histogram_file = resources.files("uhi") / "resources/histogram.json"

with histogram_file.open(encoding="utf-8") as f:
    histogram_schema = fastjsonschema.compile(json.load(f))


def validate(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        example = json.load(f)

    histogram_schema(example)


if __name__ == "__main__":
    validate(*sys.argv[1:])
