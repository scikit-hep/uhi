from __future__ import annotations

import importlib.metadata

from uhi import __version__


def test_version() -> None:
    assert __version__ == importlib.metadata.version("uhi")
