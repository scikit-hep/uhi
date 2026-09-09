"""
Command line interface for uhi.

``uhi add`` sums histograms from JSON, ZIP, HDF5, or ROOT files, like ROOT's
``hadd``. ``uhi validate`` checks JSON files against the schema.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import uhi.io.json
import uhi.io.ops
import uhi.io.zip

__all__ = ["main"]


def __dir__() -> list[str]:
    return __all__


def _format(path: Path, /) -> str:
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
            msg = f"Unknown file extension {suffix!r} for {path}"
            raise SystemExit(msg)


def _hdf5_groups(grp: Any, prefix: str = "") -> dict[str, Any]:
    """
    Recursively find every HDF5 group holding a histogram.
    """
    import h5py  # noqa: PLC0415

    found: dict[str, Any] = {}
    for name, item in grp.items():
        if not isinstance(item, h5py.Group):
            continue
        full_name = f"{prefix}{name}"
        if "uhi_schema" in item.attrs:
            found[full_name] = item
        else:
            found |= _hdf5_groups(item, f"{full_name}/")
    return found


def _root_ntuples(directory: Any, prefix: str = "") -> dict[str, Any]:
    """
    Recursively read every RNTuple in a ROOT directory, keyed by path.
    """
    from uhi.io import root  # noqa: PLC0415

    found: dict[str, Any] = {}
    for key in directory.GetListOfKeys():
        name = key.GetName()
        match key.GetClassName():
            case "ROOT::RNTuple" | "ROOT::Experimental::RNTuple":
                found[f"{prefix}{name}"] = root.read(directory, name)
            case "TDirectory" | "TDirectoryFile":
                found |= _root_ntuples(directory.Get(name), f"{prefix}{name}/")
    return found


def _read(path: Path, /) -> dict[str, Any]:
    """
    Read all histograms from a file, keyed by name.
    """
    match _format(path):
        case "json":
            with path.open(encoding="utf-8") as f:
                return json.load(f, object_hook=uhi.io.json.object_hook)  # type: ignore[no-any-return]
        case "zip":
            with zipfile.ZipFile(path) as zf:
                names = [
                    n.removesuffix(".json")
                    for n in zf.namelist()
                    if n.endswith(".json")
                ]
                return {name: uhi.io.zip.read(zf, name) for name in names}
        case "hdf5":
            import h5py  # noqa: PLC0415

            from uhi.io import hdf5  # noqa: PLC0415

            with h5py.File(path, "r") as f:
                return {n: hdf5.read(g) for n, g in _hdf5_groups(f).items()}
        case _:
            import ROOT  # noqa: PLC0415

            root_file = ROOT.TFile.Open(str(path))
            if not root_file:
                msg = f"Could not open {path} as a ROOT file"
                raise SystemExit(msg)
            with root_file:
                return _root_ntuples(root_file)


def _write(path: Path, hists: dict[str, Any], /) -> None:
    match _format(path):
        case "json":
            with path.open("w", encoding="utf-8") as f:
                json.dump(hists, f, default=uhi.io.json.default, indent=2)
        case "zip":
            with zipfile.ZipFile(path, "w") as zf:
                for name, hist in hists.items():
                    uhi.io.zip.write(zf, name, hist)
        case "hdf5":
            import h5py  # noqa: PLC0415

            from uhi.io import hdf5  # noqa: PLC0415

            with h5py.File(path, "w") as f:
                for name, hist in hists.items():
                    hdf5.write(f.create_group(name), hist)
        case _:
            import ROOT  # noqa: PLC0415

            from uhi.io import root  # noqa: PLC0415

            with ROOT.TFile.Open(str(path), "RECREATE") as f:
                for name, hist in hists.items():
                    directory, _, base = name.rpartition("/")
                    root.write(
                        f.mkdir(directory, "", True) if directory else f, base, hist
                    )


def _add(args: argparse.Namespace) -> None:
    target = Path(args.target)
    _format(target)  # Fail early on an unknown output extension
    if target.exists() and not args.force:
        msg = f"{target} exists, use --force to overwrite"
        raise SystemExit(msg)

    inputs = [_read(Path(p)) for p in args.sources]
    names = dict.fromkeys(name for hists in inputs for name in hists)
    result = {
        name: uhi.io.ops.add(*(hists[name] for hists in inputs if name in hists))
        for name in names
    }
    _write(target, result)


def _validate(args: argparse.Namespace) -> None:
    from uhi.schema import main as validate_main  # noqa: PLC0415

    validate_main(*args.files)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="uhi", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser(
        "add",
        help="add histograms from several files (like ROOT's hadd)",
        description="Sum the histograms in SOURCE files, bin-by-bin, into TARGET. "
        "Histograms are matched by name; the file format is chosen by extension "
        "(.json, .zip, .h5/.hdf5, .root).",
    )
    add_parser.add_argument(
        "-f", "--force", action="store_true", help="overwrite TARGET"
    )
    add_parser.add_argument("target", help="output file")
    add_parser.add_argument("sources", nargs="+", help="input files")
    add_parser.set_defaults(func=_add)

    validate_parser = subparsers.add_parser(
        "validate", help="validate JSON histogram files against the schema"
    )
    validate_parser.add_argument("files", nargs="+", help="JSON files")
    validate_parser.set_defaults(func=_validate)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
