from __future__ import annotations

import contextlib
import importlib.metadata
import sys
import sysconfig
from pathlib import Path

import pytest
from packaging.requirements import Requirement

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

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


def pytest_report_header() -> str:
    with DIR.parent.joinpath("pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)
    project = pyproject.get("project", {})

    pkgs = project.get("dependencies", [])
    pkgs += [p for ps in project.get("optional-dependencies", {}).values() for p in ps]
    pkgs += [
        p
        for ps in project.get("dependency-groups", {}).values()
        for p in ps
        if isinstance(p, str)
    ]
    if "name" in project:
        pkgs.append(project["name"])
    interesting_packages = {Requirement(p).name for p in pkgs}
    interesting_packages.add("pip")
    interesting_packages.add("numpy")

    valid = []
    for package in sorted(interesting_packages):
        with contextlib.suppress(ModuleNotFoundError):
            valid.append(f"{package}=={importlib.metadata.version(package)}")
    reqs = " ".join(valid)
    lines = [
        f"installed packages of interest: {reqs}",
    ]
    if sysconfig.get_config_var("Py_GIL_DISABLED"):
        lines.append("free-threaded Python build")
    return "\n".join(lines)
