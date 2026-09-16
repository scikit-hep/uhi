"""
Read and write whole histogram files in any supported format.

A file holds either a dict of named histograms or a single histogram. A spec
like ``file.h5:path`` selects a group, directory, or histogram inside the file.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

__all__ = ["file_format", "is_single", "load", "split_spec", "write"]


def __dir__() -> list[str]:
    return __all__


_SPEC_RE = re.compile(r"^(.+?\.(?:json|zip|h5|hdf5|hdf|root)):(.+)$", re.IGNORECASE)
_SUFFIXES = "expected .json, .zip, .h5/.hdf5/.hdf, or .root"


def split_spec(spec: str, /) -> tuple[str, str | None]:
    """Split ``file.root:dir/name`` into ``("file.root", "dir/name")``."""
    if match := _SPEC_RE.match(spec):
        return match[1], match[2]
    return spec, None


def file_format(path: Path, /) -> str:
    match path.suffix.lower():
        case ".json":
            return "json"
        case ".zip":
            return "zip"
        case ".h5" | ".hdf5" | ".hdf":
            return "hdf5"
        case ".root":
            return "root"
        case suffix:
            msg = f"Unknown file format {suffix!r}, {_SUFFIXES}"
            raise ValueError(msg)


def is_single(data: Any, /) -> bool:
    """True for a single histogram, False for a dict of named histograms."""
    return "uhi_schema" in data


def _load_json(path: Path, subpath: str | None) -> Any:
    from .json import object_hook  # noqa: PLC0415

    with path.open(encoding="utf-8") as f:
        data = json.load(f, object_hook=object_hook)
    if subpath is None:
        return data
    if is_single(data) or subpath not in data:
        msg = f"{subpath!r} not found in {path}"
        raise KeyError(msg)
    return data[subpath]


def _load_zip(path: Path, subpath: str | None) -> Any:
    from . import zip as uhi_zip  # noqa: PLC0415

    with zipfile.ZipFile(path) as zip_file:
        names = [n[:-5] for n in zip_file.namelist() if n.endswith(".json")]
        if subpath is None:
            return {name: uhi_zip.read(zip_file, name) for name in names}
        subpath = subpath.strip("/")
        if subpath in names:
            return uhi_zip.read(zip_file, subpath)
        prefix = f"{subpath}/"
        found = {
            n.removeprefix(prefix): uhi_zip.read(zip_file, n)
            for n in names
            if n.startswith(prefix)
        }
        if not found:
            msg = f"{subpath!r} not found in {path}"
            raise KeyError(msg)
        return found


def _load_hdf5(path: Path, subpath: str | None) -> Any:
    import h5py  # noqa: PLC0415

    from . import hdf5  # noqa: PLC0415

    hists: dict[str, Any] = {}

    def visit(name: str, obj: Any) -> None:
        if isinstance(obj, h5py.Group) and "uhi_schema" in obj.attrs:
            hists[name] = hdf5.read(obj)

    with h5py.File(path, "r") as h5_file:
        start = h5_file[subpath] if subpath else h5_file
        if "uhi_schema" in start.attrs:
            return hdf5.read(start)
        start.visititems(visit)
    return hists


def _load_root(path: Path, subpath: str | None) -> Any:
    import ROOT  # noqa: PLC0415

    from . import root  # noqa: PLC0415

    hists: dict[str, Any] = {}

    def visit(directory: Any, prefix: str) -> None:
        for key in directory.GetListOfKeys():
            name = key.GetName()
            match key.GetClassName():
                case "ROOT::RNTuple" | "ROOT::Experimental::RNTuple":
                    hists[f"{prefix}{name}"] = root.read(directory, name)
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
        return root.read(directory, name)


def load(file: str | Path, /, *, path: str | None = None) -> Any:
    """
    Load a file as a ``{name: histogram}`` dict, or as a single histogram
    if the file (or ``path`` inside it) holds only one. Arrays are NumPy
    arrays. The format is selected by suffix.
    """
    filepath = Path(file)
    match file_format(filepath):
        case "json":
            return _load_json(filepath, path)
        case "zip":
            return _load_zip(filepath, path)
        case "hdf5":
            return _load_hdf5(filepath, path)
        case _:
            return _load_root(filepath, path)


def write(file: str | Path, data: Any, /, *, path: str | None = None) -> None:
    """
    Write a ``{name: histogram}`` dict, or a single histogram, to a new file.
    ``path`` is a prefix for the names, or the name of a single histogram;
    it is required for a single histogram in the zip and ROOT formats.
    """
    filepath = Path(file)
    fmt = file_format(filepath)
    prefix = f"{path.strip('/')}/" if path else ""

    if is_single(data):
        if path:
            data = {path.strip("/"): data}
        elif fmt in {"zip", "root"}:
            msg = f"A name is needed to write a single histogram, use {filepath}:name"
            raise ValueError(msg)
    else:
        data = {f"{prefix}{name}": hist for name, hist in data.items()}

    match fmt:
        case "json":
            from .json import default  # noqa: PLC0415

            with filepath.open("w", encoding="utf-8") as f:
                json.dump(data, f, default=default, indent=2)
        case "zip":
            from . import zip as uhi_zip  # noqa: PLC0415

            with zipfile.ZipFile(filepath, "w") as zip_file:
                for name, hist in data.items():
                    uhi_zip.write(zip_file, name, hist)
        case "hdf5":
            import h5py  # noqa: PLC0415

            from . import hdf5  # noqa: PLC0415

            with h5py.File(filepath, "w") as h5_file:
                if is_single(data):
                    hdf5.write(h5_file, data)
                else:
                    for name, hist in data.items():
                        hdf5.write(h5_file.create_group(name), hist)
        case _:
            import ROOT  # noqa: PLC0415

            from . import root  # noqa: PLC0415

            with ROOT.TFile.Open(str(filepath), "RECREATE") as root_file:
                for name, hist in data.items():
                    directory, _, base = name.rpartition("/")
                    target = (
                        root_file.mkdir(directory, "", True) if directory else root_file
                    )
                    root.write(target, base, hist)
