from __future__ import annotations

import functools
import json
import re
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


def _load_hdf5(path: Path, subpath: str | None) -> dict[str, Any]:
    import h5py  # noqa: PLC0415

    import uhi.io.hdf5  # noqa: PLC0415

    hists: dict[str, Any] = {}

    def visit(name: str, obj: Any) -> None:
        if isinstance(obj, h5py.Group) and "uhi_schema" in obj.attrs:
            hists[name] = uhi.io.hdf5.read(obj)

    with h5py.File(path, "r") as h5_file:
        start = h5_file[subpath] if subpath else h5_file
        if "uhi_schema" in start.attrs:
            return dict(uhi.io.hdf5.read(start))
        start.visititems(visit)
    return hists


def _load_root(path: Path, subpath: str | None) -> dict[str, Any]:
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
        if not subpath:
            visit(root_file, "")
            return hists
        parent, _, name = subpath.rstrip("/").rpartition("/")
        directory = root_file.Get(parent) if parent else root_file
        key = directory.GetKey(name) if directory else None
        if not key:
            msg = f"{subpath!r} not found in {path}"
            raise KeyError(msg)
        if key.GetClassName() in {"TDirectory", "TDirectoryFile"}:
            visit(directory.Get(name), "")
            return hists
        # A single RNTuple
        return uhi.io.root.read(directory, name)


_SPEC_RE = re.compile(r"^(.+?\.(?:json|zip|h5|hdf5|hdf|root)):(.+)$", re.IGNORECASE)


def _split_spec(spec: str) -> tuple[str, str | None]:
    """Split ``file.root:dir/name`` into ``("file.root", "dir/name")``."""
    if match := _SPEC_RE.match(spec):
        return match[1], match[2]
    return spec, None


def load(file: str | Path, /, *, path: str | None = None) -> dict[str, Any]:
    """
    Load all histograms from a file as a ``{name: histogram}`` dict with
    JSON-compatible values. The format is selected by suffix: ``.json``,
    ``.zip``, ``.h5``/``.hdf5``/``.hdf``, or ``.root``.

    For HDF5 and ROOT files, ``path`` restricts the search to a group or
    directory inside the file. If it names a single histogram, that histogram
    is returned instead of a dict.
    """
    filepath = Path(file)
    match filepath.suffix.lower():
        case ".h5" | ".hdf5" | ".hdf":
            data = _load_hdf5(filepath, path)
        case ".root":
            data = _load_root(filepath, path)
        case _ if path:
            msg = (
                f"An in-file path ({path!r}) is only supported for HDF5 and ROOT files"
            )
            raise ValueError(msg)
        case ".json":
            with filepath.open(encoding="utf-8") as f:
                data = json.load(f)
        case ".zip":
            data = _load_zip(filepath)
        case suffix:
            msg = f"Unknown file format {suffix!r}, expected .json, .zip, .h5, or .root"
            raise ValueError(msg)
    return _to_json_compatible(data)


def main(*files: str) -> None:
    """Validate histogram files."""
    import fastjsonschema  # noqa: PLC0415

    retval = 0

    for file in files:
        filename, path = _split_spec(file)
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
