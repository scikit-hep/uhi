#!/usr/bin/env -S uv run -q

# /// script
# dependencies = ["nox>=2025.2.9"]
# ///

from __future__ import annotations

import argparse
from pathlib import Path

import nox

nox.needs_version = ">=2025.2.9"
nox.options.default_venv_backend = "uv|virtualenv"

PYPROJECT = nox.project.load_toml()
ALL_PYTHONS = nox.project.python_versions(PYPROJECT)

DIR = Path(__file__).parent.resolve()


@nox.session
def lint(session):
    """
    Run the linter.
    """
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files", *session.posargs)


@nox.session(python=ALL_PYTHONS)
def tests(session):
    """
    Run the unit and regular tests.
    """
    session.install("-e.[schema]", *nox.project.dependency_groups(PYPROJECT, "test"))
    session.run("pytest", *session.posargs)


@nox.session(reuse_venv=True, default=False)
def docs(session: nox.Session) -> None:
    """
    Build the docs. Use "--non-interactive" to avoid serving. Pass "-b linkcheck" to check links.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-b", dest="builder", default="html", help="Build target (default: html)"
    )
    args, posargs = parser.parse_known_args(session.posargs)

    serve = args.builder == "html" and session.interactive
    extra_installs = ["sphinx-autobuild"] if serve else []
    session.install(
        "-e.", *extra_installs, *nox.project.dependency_groups(PYPROJECT, "docs")
    )

    session.chdir("docs")

    shared_args = (
        "-n",  # nitpicky mode
        "-T",  # full tracebacks
        f"-b={args.builder}",
        ".",
        f"_build/{args.builder}",
        *posargs,
    )

    if serve:
        session.run("sphinx-autobuild", "--open-browser", *shared_args)
    else:
        session.run("sphinx-build", "--keep-going", *shared_args)


@nox.session(default=False)
def build(session):
    """
    Build an SDist and wheel.
    """

    if session.venv_backend == "uv":
        session.run("uv", "build")
    else:
        session.install("build")
        session.run("python", "-m", "build")


@nox.session(venv_backend="conda", default=False)
def root_tests(session):
    """
    Test against ROOT.
    """

    session.conda_install("--channel=conda-forge", "ROOT", "pytest", "boost-histogram")
    session.install("-e.")
    session.run("pytest", "tests/test_root.py")


if __name__ == "__main__":
    nox.run()
