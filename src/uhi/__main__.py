"""
Command line interface for uhi.

``uhi validate`` checks histogram files (JSON, zip, HDF5, or ROOT) against the
schema.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

__all__ = ["main"]


def __dir__() -> list[str]:
    return __all__


def _validate(args: argparse.Namespace) -> None:
    from uhi.schema import main as validate_main  # noqa: PLC0415

    validate_main(*args.files)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="uhi", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="validate histogram files (JSON, zip, HDF5, or ROOT) against the schema",
    )
    validate_parser.add_argument(
        "files",
        nargs="+",
        help="histogram files (.json, .zip, .h5, .root); use file.h5:group or "
        "file.root:dir to select a group or directory inside the file",
    )
    validate_parser.set_defaults(func=_validate)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])
