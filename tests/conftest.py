from __future__ import annotations

from pathlib import Path

import pytest

DIR = Path(__file__).parent.resolve()
VALID_FILES = DIR.glob("resources/valid/*.json")
INVALID_FILES = DIR.glob("resources/invalid/*.json")


@pytest.fixture(scope="session")
def resources() -> Path:
    return DIR / "resources"


@pytest.fixture(params=VALID_FILES, ids=lambda p: p.name)
def valid(request: pytest.FixtureRequest) -> Path:
    return request.param  # type: ignore[no-any-return]


@pytest.fixture(params=INVALID_FILES, ids=lambda p: p.name)
def invalid(request: pytest.FixtureRequest) -> Path:
    return request.param  # type: ignore[no-any-return]


@pytest.fixture(params=[False, True], ids=["dense", "sparse"])
def sparse(request: pytest.FixtureRequest) -> bool:
    return request.param  # type: ignore[no-any-return]
