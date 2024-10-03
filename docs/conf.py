# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from __future__ import annotations

import importlib.metadata
import os

# -- Project information -----------------------------------------------------

project = "uhi"
copyright = "2021, Henry Schreiner, Hans Dembinski, Jim Pivarski"
author = "Henry Schreiner, Hans Dembinski, Jim Pivarski"

# The full version, including alpha/beta/rc tags
version = release = importlib.metadata.version("uhi")


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx-jsonschema",
    "sphinx.ext.napoleon",
    "sphinx_copybutton",
    "sphinx_github_changelog",
]

source_suffix = [".rst", ".md"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

myst_enable_extensions = [
    "colon_fence",
]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "furo"


# -- Changelog builder -------------------------------------------------------
if "GITHUB_API_TOKEN" in os.environ:
    sphinx_github_changelog_token = os.environ["GITHUB_API_TOKEN"]

commit = os.environ.get("READTHEDOCS_GIT_COMMIT_HASH", "main")
code_url = "https://github.com/scikit-hep/uhi/blob"
