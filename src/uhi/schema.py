from __future__ import annotations

import functools
import json
import sys
import zipfile
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any

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


def _to_json_compatible(data: dict[str, Any]) -> dict[str, Any]:
    """Convert NumPy arrays and scalars so the schema validator can check them."""
    from uhi.io.json import default  # noqa: PLC0415

    result: dict[str, Any] = json.loads(json.dumps(data, default=default))
    return result


def _load_zip(path: Path) -> dict[str, Any]:
    import uhi.io.zip  # noqa: PLC0415

    with zipfile.ZipFile(path) as zip_file:
        names = [n[:-5] for n in zip_file.namelist() if n.endswith(".json")]
        return {name: uhi.io.zip.read(zip_file, name) for name in names}


def _load_hdf5(path: Path) -> dict[str, Any]:
    import h5py  # noqa: PLC0415

    import uhi.io.hdf5  # noqa: PLC0415

    hists: dict[str, Any] = {}

    def visit(name: str, obj: Any) -> None:
        if isinstance(obj, h5py.Group) and "uhi_schema" in obj.attrs:
            hists[name] = uhi.io.hdf5.read(obj)

    with h5py.File(path, "r") as h5_file:
        h5_file.visititems(visit)
    return hists


def _load_root(path: Path) -> dict[str, Any]:
    import ROOT  # noqa: PLC0415

    import uhi.io.root  # noqa: PLC0415

    hists: dict[str, Any] = {}

    def visit(directory: Any, prefix: str) -> None:
        for key in directory.GetListOfKeys():
            name = key.GetName()
            match key.GetClassName():
                case "ROOT::RNTuple" | "ROOT::Experimental::RNTuple":
                    hists[f"{prefix}{name}"] = uhi.io.root.read(directory, name)
                case "TDirectory" | "TDirectoryFile":
                    visit(directory.Get(name), f"{prefix}{name}/")

    root_file = ROOT.TFile.Open(str(path))
    if not root_file:
        msg = f"Could not open {path} as a ROOT file"
        raise OSError(msg)
    with root_file:
        visit(root_file, "")
    return hists


def load(file: str | Path, /) -> dict[str, Any]:
    """
    Load all histograms from a file as a ``{name: histogram}`` dict with
    JSON-compatible values. The format is selected by suffix: ``.json``,
    ``.zip``, ``.h5``/``.hdf5``/``.hdf``, or ``.root``.
    """
    path = Path(file)
    match path.suffix.lower():
        case ".json":
            with path.open(encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
        case ".zip":
            data = _load_zip(path)
        case ".h5" | ".hdf5" | ".hdf":
            data = _load_hdf5(path)
        case ".root":
            data = _load_root(path)
        case suffix:
            msg = f"Unknown file format {suffix!r}, expected .json, .zip, .h5, or .root"
            raise ValueError(msg)
    return _to_json_compatible(data)


def main(*files: str) -> None:
    """Validate histogram files."""
    import fastjsonschema  # noqa: PLC0415

    retval = 0

    for file in files:
        try:
            validate(load(file))
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
