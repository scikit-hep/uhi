from uhi import __version__
import sys

if sys.version_info < (3, 8):
    import importlib_metadata as metadata
else:
    from importlib import metadata


def test_version() -> None:
    assert __version__ == metadata.version("uhi")
