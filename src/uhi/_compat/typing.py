from __future__ import annotations

import sys

if sys.version_info >= (3, 11):
    from typing import NotRequired, Required
else:
    from typing_extensions import NotRequired, Required

__all__ = ["NotRequired", "Required"]


def __dir__() -> list[str]:
    return __all__
