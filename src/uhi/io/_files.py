"""
Read and write whole histogram files in any supported format.

A file holds either a dict of named histograms or a single histogram. A spec
like ``file.h5:path`` selects a group, directory, or histogram inside the file.
"""

from __future__ import annotations

import functools
import importlib.metadata
import json
import re
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

__all__ = ["file_format", "is_single", "load", "split_spec", "write"]


def __dir__() -> list[str]:
    return __all__


_SPEC_RE = re.compile(r"^(.+?\.(?:json|zip|h5|hdf5|hdf|root)):(.*)$", re.IGNORECASE)
_RNTUPLE_CLASSES = frozenset(["ROOT::RNTuple", "ROOT::Experimental::RNTuple"])
_DIRECTORY_CLASSES = frozenset(["TDirectory", "TDirectoryFile"])
_SUFFIXES = "expected .json, .zip, .h5/.hdf5/.hdf, or .root"


def split_spec(spec: str, /) -> tuple[str, str | None]:
    """Split ``file.root:dir/name`` into ``("file.root", "dir/name")``."""
    if match := _SPEC_RE.match(spec):
        if not match[2]:
            msg = f"Empty name after ':' in {spec!r}"
            raise ValueError(msg)
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
        case "":
            msg = f"No file extension in {str(path)!r}, {_SUFFIXES}"
            raise ValueError(msg)
        case suffix:
            msg = f"Unknown file format {suffix!r}, {_SUFFIXES}"
            raise ValueError(msg)


def is_single(data: Any, /) -> bool:
    """True for a single histogram, False for a dict of named histograms."""
    return isinstance(data, Mapping) and "uhi_schema" in data


def _load_json(path: Path, subpath: str | None, *, raw: bool = False) -> Any:
    from .json import object_hook  # noqa: PLC0415

    with path.open(encoding="utf-8") as f:
        data = json.load(f, object_hook=None if raw else object_hook)
    if subpath is None:
        return data
    subpath = subpath.strip("/")
    if isinstance(data, Mapping) and not is_single(data):
        if subpath in data:
            return data[subpath]
        # Flat "dir/name" keys, as written by write(..., path="dir")
        prefix = f"{subpath}/"
        found = {
            k.removeprefix(prefix): v for k, v in data.items() if k.startswith(prefix)
        }
        if found:
            return found
    msg = f"{subpath!r} not found in {path}"
    raise KeyError(msg)


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
        try:
            start = h5_file[subpath] if subpath else h5_file
        except KeyError:
            msg = f"{subpath!r} not found in {path}"
            raise KeyError(msg) from None
        if not isinstance(start, h5py.Group):
            msg = f"{subpath!r} in {path} is not a histogram or group"
            raise ValueError(msg)  # noqa: TRY004
        if "uhi_schema" in start.attrs:
            return hdf5.read(start)
        start.visititems(visit)
    return hists


@functools.cache
def _uproot_available() -> bool:
    """Uproot 5.7+ is preferred for ROOT files; PyROOT is the fallback."""
    try:
        version = importlib.metadata.version("uproot")
    except importlib.metadata.PackageNotFoundError:
        return False
    return tuple(int(v) for v in re.findall(r"\d+", version)[:2]) >= (5, 7)


def _load_uproot(path: Path, subpath: str | None) -> Any:
    import uproot  # noqa: PLC0415

    from . import uproot as uhi_uproot  # noqa: PLC0415

    def visit(directory: Any) -> dict[str, Any]:
        return {
            name: uhi_uproot.read(directory, name)
            for name in directory.keys(
                recursive=True, cycle=False, filter_classname=_RNTUPLE_CLASSES
            )
        }

    with uproot.open(path) as root_file:
        if not subpath:
            return visit(root_file)
        subpath = subpath.strip("/")
        if subpath not in root_file:
            msg = f"{subpath!r} not found in {path}"
            raise KeyError(msg)
        classname = root_file.classname_of(subpath)
        if classname in _RNTUPLE_CLASSES:
            return uhi_uproot.read(root_file, subpath)
        if classname not in _DIRECTORY_CLASSES:
            msg = f"{subpath!r} in {path} is not a histogram or directory"
            raise ValueError(msg)
        return visit(root_file[subpath])


def _load_root(path: Path, subpath: str | None) -> Any:
    if _uproot_available():
        return _load_uproot(path, subpath)

    import ROOT  # noqa: PLC0415

    from . import root  # noqa: PLC0415

    hists: dict[str, Any] = {}

    def visit(directory: Any, prefix: str) -> None:
        for key in directory.GetListOfKeys():
            name = key.GetName()
            class_name = key.GetClassName()
            if class_name in _RNTUPLE_CLASSES:
                hists[f"{prefix}{name}"] = root.read(directory, name)
            elif class_name in _DIRECTORY_CLASSES:
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
        class_name = key.GetClassName()
        if class_name in _DIRECTORY_CLASSES:
            visit(directory.Get(name), "")
            return hists
        if class_name not in _RNTUPLE_CLASSES:
            msg = f"{subpath!r} in {path} is not a histogram or directory"
            raise ValueError(msg)
        return root.read(directory, name)


def load(file: str | Path, /, *, path: str | None = None, raw: bool = False) -> Any:
    """
    Load a file as a ``{name: histogram}`` dict, or as a single histogram
    if the file (or ``path`` inside it) holds only one. Arrays are NumPy
    arrays, except that ``raw`` keeps JSON files exactly as written so that
    validation sees the original types. The format is selected by suffix.
    """
    filepath = Path(file)
    match file_format(filepath):
        case "json":
            return _load_json(filepath, path, raw=raw)
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
        case _ if _uproot_available():
            import uproot  # noqa: PLC0415

            from . import uproot as uhi_uproot  # noqa: PLC0415

            with uproot.recreate(filepath) as root_file:
                for name, hist in data.items():
                    uhi_uproot.write(root_file, name, hist)
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
