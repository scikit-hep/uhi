"""
Command line interface for uhi.

``uhi add`` sums histograms from JSON, ZIP, HDF5, or ROOT files, like ROOT's
``hadd``. ``uhi validate`` checks histogram files (JSON, zip, HDF5, or ROOT)
against the schema.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import uhi.io.ops
from uhi.io import _files

__all__ = ["main"]


def __dir__() -> list[str]:
    return __all__


_ERRORS = (OSError, ValueError, KeyError, TypeError, ImportError)


def _read(spec: str, /) -> Any:
    """
    Read a ``file[:path]`` spec: a dict of named histograms or a single one.
    """
    try:
        file, path = _files.split_spec(spec)
        data = _files.load(file, path=path)
    except _ERRORS as e:
        msg = f"{spec}: {e}"
        raise SystemExit(msg) from None

    if not isinstance(data, Mapping):
        msg = f"{spec}: not a histogram or a dict of histograms"
        raise SystemExit(msg)
    if _files.is_single(data):
        return data
    if not data:
        msg = f"{spec}: no histograms found"
        raise SystemExit(msg)
    for name, hist in data.items():
        if not _files.is_single(hist):
            msg = f"{spec}: {name!r} is not a histogram"
            raise SystemExit(msg)
    return data


def _add(args: argparse.Namespace) -> None:
    try:
        target, target_path = _files.split_spec(args.target)
        _files.file_format(Path(target))  # Fail early on an unknown extension
    except ValueError as e:
        raise SystemExit(str(e)) from None
    if Path(target).exists() and not args.force:
        msg = f"{target} exists, use --force to overwrite"
        raise SystemExit(msg)

    inputs = [_read(spec) for spec in args.sources]
    singles = [_files.is_single(data) for data in inputs]
    if any(singles) and not all(singles):
        msg = "Cannot mix single histograms and files of named histograms"
        raise SystemExit(msg)

    try:
        if all(singles):
            result: Any = uhi.io.ops.add(*inputs)
        else:
            names = dict.fromkeys(name for hists in inputs for name in hists)
            result = {
                name: uhi.io.ops.add(*(h[name] for h in inputs if name in h))
                for name in names
            }
        _files.write(target, result, path=target_path)
    except _ERRORS as e:
        raise SystemExit(str(e)) from None


def _validate(args: argparse.Namespace) -> None:
    try:
        import fastjsonschema  # noqa: F401, PLC0415
    except ImportError:
        msg = "uhi validate needs fastjsonschema, install uhi[schema]"
        raise SystemExit(msg) from None

    from uhi.schema import main as validate_main  # noqa: PLC0415

    validate_main(*args.files)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="uhi", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser(
        "add",
        help="add histograms from several files (like ROOT's hadd)",
        description="Sum the histograms in SOURCE files, bin-by-bin, into TARGET. "
        "Histograms are matched by name. The file extension sets the format "
        "(.json, .zip, .h5/.hdf5/.hdf, .root). Use file:name to select one "
        "histogram (or file:dir for a group or directory) in a SOURCE, and "
        "TARGET:name to name the output. TARGET must not exist unless -f is given.",
    )
    add_parser.add_argument(
        "-f", "--force", action="store_true", help="overwrite TARGET if it exists"
    )
    add_parser.add_argument("target", help="output file, optionally file:name")
    add_parser.add_argument("sources", nargs="+", help="input files (file[:path])")
    add_parser.set_defaults(func=_add)

    validate_parser = subparsers.add_parser(
        "validate",
        help="validate histogram files (JSON, zip, HDF5, or ROOT) against the schema",
        description="Validate histogram files against the uhi JSON schema. The "
        "file extension sets the format. Needs the uhi[schema] extra.",
    )
    validate_parser.add_argument(
        "files",
        nargs="+",
        help="histogram files (.json, .zip, .h5/.hdf5/.hdf, .root); use file.h5:group or "
        "file.root:dir to select a group or directory inside the file",
    )
    validate_parser.set_defaults(func=_validate)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
