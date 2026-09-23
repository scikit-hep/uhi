from __future__ import annotations

import functools
import json
import sys
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any

from .io import _files

_resources = resources.files("uhi") / "resources"
histogram_file = _resources / "histogram.schema.json"
histograms_file = _resources / "histograms.schema.json"

__all__ = [
    "histogram_file",
    "histograms_file",
    "load",
    "validate",
    "validate_histogram",
]


def __dir__() -> list[str]:
    return __all__


_BASE_URI = "https://raw.githubusercontent.com/scikit-hep/uhi/main/src/uhi/resources/"


def _load_local(uri: str) -> dict[str, Any]:
    """
    Resolve a ``$ref`` to a schema shipped in ``resources``. The ``$id`` makes
    refs absolute URLs; they are read from the package, never the network.
    """
    name = uri.removeprefix(_BASE_URI)
    if "/" in name or ":" in name:
        msg = f"Cannot resolve {uri!r} without network access"
        raise ValueError(msg)
    with (_resources / name).open(encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


@functools.cache
def _compile(name: str) -> Callable[[dict[str, Any]], None]:
    import fastjsonschema  # noqa: PLC0415

    with (_resources / name).open(encoding="utf-8") as f:
        return fastjsonschema.compile(  # type: ignore[no-any-return]
            json.load(f), handlers={"": _load_local, "https": _load_local}
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


def _to_json_compatible(data: dict[str, Any]) -> dict[str, Any]:
    """Convert NumPy arrays and scalars so the schema validator can check them."""
    from uhi.io.json import default  # noqa: PLC0415

    result: dict[str, Any] = json.loads(json.dumps(data, default=default))
    return result


def load(file: str | Path, /, *, path: str | None = None) -> dict[str, Any]:
    """
    Load all histograms from a file as a ``{name: histogram}`` dict with
    JSON-compatible values. The format is selected by suffix: ``.json``,
    ``.zip``, ``.h5``/``.hdf5``/``.hdf``, or ``.root``.

    ``path`` restricts the search to a group or directory inside the file, or
    to a single histogram by name. If the file or ``path`` holds a single
    histogram, that histogram is returned instead of a dict.
    """
    return _to_json_compatible(_files.load(file, path=path, raw=True))


def main(*files: str) -> None:
    """Validate histogram files."""
    import fastjsonschema  # noqa: PLC0415

    retval = 0

    for file in files:
        filename, path = _files.split_spec(file)
        try:
            validate(load(filename, path=path))
        except fastjsonschema.JsonSchemaValueException as e:
            print(f"ERROR {file}: {e.message}")  # noqa: T201
            retval = 1
        except (OSError, ValueError, TypeError, KeyError, ImportError) as e:
            print(f"ERROR {file}: {e}")  # noqa: T201
            retval = 1
        else:
            print(f"OK {file}")  # noqa: T201

    if retval:
        raise SystemExit(retval)


if __name__ == "__main__":
    main(*sys.argv[1:])
