import re
from pathlib import Path

import nox

ALL_PYTHONS = ["3.6", "3.7", "3.8", "3.9", "3.10"]

nox.options.sessions = ["lint", "tests"]


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
    session.install(".[test]")
    session.run("pytest", *session.posargs)


@nox.session
def docs(session):
    """
    Build the docs. Pass "serve" to serve.
    """

    session.install(".[docs]")
    session.chdir("docs")
    session.run("sphinx-build", "-M", "html", ".", "_build")

    if session.posargs:
        if "serve" in session.posargs:
            print("Launching docs at http://localhost:8000/ - use Ctrl-C to quit")
            session.run("python", "-m", "http.server", "8000", "-d", "_build/html")
        else:
            print("Unsupported argument to docs")


@nox.session
def build(session):
    """
    Build an SDist and wheel.
    """

    session.install("build")
    session.run("python", "-m", "build")


@nox.session(venv_backend="conda")
def root_tests(session):
    """
    Test against ROOT.
    """

    session.conda_install("--channel=conda-forge", "ROOT", "pytest", "boost-histogram")
    session.install(".")
    session.run("pytest", "tests/test_root.py")


@nox.session(reuse_venv=True)
def bump(session: nox.Session) -> None:
    """
    Bump the major/minor/patch version (if nothing given, just shows the version).
    """

    session.install("tomli")
    output = session.run(
        "python",
        "-c",
        "import tomli, pathlib; p = pathlib.Path('pyproject.toml'); print(tomli.loads(p.read_text())['project']['version'])",
        silent=True,
    )
    current_version = output.strip()

    if not session.posargs:
        session.log(f"Current version: {current_version}")
        return

    new_version = session.posargs[0]
    session.log(f"Bumping from {current_version} to {new_version}")

    replace_version(
        Path("src/uhi/__init__.py"),
        '__version__ = "{version}"',
        current_version,
        new_version,
    )
    replace_version(
        Path("pyproject.toml"), 'version = "{version}"', current_version, new_version
    )

    print(f"git switch -c chore/bump/{new_version}")
    print("git add -u src/uhi/__init__.py pyproject.toml")
    print(f"git commit -m 'chore: bump version to {new_version}'")
    print("gh pr create --fill")


def replace_version(file: Path, fmt: str, in_version: str, out_version: str) -> None:

    in_fmt = fmt.format(version=in_version)
    out_fmt = fmt.format(version=out_version)

    with file.open("r") as f:
        txt = f.read()

    txt = re.sub(in_fmt, out_fmt, txt)

    with file.open("w") as f:
        f.write(txt)
