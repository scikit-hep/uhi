# UHI (Universal Histogram Interface) development

## Purpose

UHI is a package for documenting histogram indexing and the PlottableHistogram
Protocol, along with tools to support library authors working with histograms.
It provides type-checking support and testing utilities for libraries that want
to conform to the Universal Histogram Interface standard. It also documents
cross-library histogram standards and best practices.

## Project layout

Some key files:

- `pyproject.toml`: Most configuration
- `docs/`: Sphinx documentation
- `docs/conf.py`: Sphinx configuration
- `docs/index.rst`: Main documentation
- `.pre-commit-config.yaml`: `prek` (pre-commit) configuration
- `src/uhi/`: Core package code
- `src/uhi/__init__.py`: Main package
- `src/uhi/schema.py`: Histogram schema definitions
- `src/uhi/tag.py`: Tag implementations
- `src/uhi/numpy_plottable.py`: NumPy histogram compatibility
- `src/uhi/typing/`: Protocol definitions for type checking
- `src/uhi/io/`: Serialization and I/O utilities
- `src/uhi/testing/`: Testing utilities and helpers
- `tests/`: Test suite

## Dev environment

The CLI tools `uv`, `prek`, and `nox` should be pre-installed as Python tools.

- `uv sync` (along with all the run commands) will ensure a `.venv` folder with
  an environment is created and populated.
- `uv run <command>` is a good way to run things like `pytest`. It will
  automatically make the `.venv` folder if it doesn't exist yet.
- `prek -a` will check the formatting and style.
- `nox -s pylint` will run pylint, a little slower (few seconds) but can report
  issues the faster checks can't.
- Docs are built with `nox -s docs --non-interactive`, which uses Sphinx to
  generate documentation from `.rst` files in the `docs/` directory.

## Testing instructions

- `uv run pytest` is a good way to run tests. Args can be easily added, like for
  a specific test.
- You can request a Python 3.15 alpha with `uv run --python 3.15 pytest`,
  remember it is "sticky", the `.venv` will be made with 3.15.
- Always add/update tests.
- Run `prek -a` to fixup style and look for linting issues.
- When running `prek -a` or `nox -s pylint`, the linting rules are _very_
  strict, so adding a local or global skip for a troublesome rule is fine if it
  makes the code better.

## Working on code

- Update the `README.md` and documentation files in `docs/` if rules or options
  change.
- Code is Python 3.10+, modern coding practices (like pattern matching)
  encouraged.
- Readability is important. Feel free to comment blocks and docstrings to
  explain what is happening.
- This is still a new project, feel free to refactor or change things to improve
  it.

## PR instructions

- Titles follow Conventional Commits (like `feat: ...`)
- Always run `prek -a` and `nox -s pylint` before committing.
