from __future__ import annotations

import argparse
from pathlib import Path

import nox

nox.needs_version = ">=2024.4.15"
nox.options.default_venv_backend = "uv|virtualenv"

ALL_PYTHONS = [
    c.split()[-1]
    for c in nox.project.load_toml("pyproject.toml")["project"]["classifiers"]
    if c.startswith("Programming Language :: Python :: 3.")
]


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
    session.install("-e.[test,schema]")
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
    session.install("-e.[docs]", *extra_installs)

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

    session.install("build")
    session.run("python", "-m", "build")


@nox.session(venv_backend="conda", default=False)
def root_tests(session):
    """
    Test against ROOT.
    """

    session.conda_install("--channel=conda-forge", "ROOT", "pytest", "boost-histogram")
    session.install(".")
    session.run("pytest", "tests/test_root.py")
