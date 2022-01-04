See the [Scikit-HEP Developer introduction][skhep-dev-intro] for a
detailed description of best practices for developing Scikit-HEP packages.

[skhep-dev-intro]: https://scikit-hep.org/developer/intro

# Quick run with Nox

If you have nox, this project supports nox. These are the supplied sessions:

```console
nox -s lint
nox -s tests
nox -s docs -- serve
nox -s build
```

# Setting up a development environment

You can set up a manual development environment by running:

```bash
pdm install
```

# Post setup

You should prepare pre-commit, which will help you by checking that commits
pass required checks:

```bash
pip install pre-commit # or brew install pre-commit on macOS
pre-commit install # Will install a pre-commit hook into the git repo
```

You can also/alternatively run `pre-commit run` (changes only) or `pre-commit
run --all-files` to check even without installing the hook.

# Testing

Use pytest to run the unit checks:

```bash
pytest
```

# Docs

Run the docs using nox or with:

```bash
pdm install --extras docs
pdm run sphinx-build -M html docs docs/_build
```

# Bumping the version

Use `nox -s bump -- <type>` to bump the version. Commit the result and push,
release on GitHub. Make sure to add some release notes to the GitHub release.
