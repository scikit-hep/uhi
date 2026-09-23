# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from __future__ import annotations

import importlib.metadata
import os
from typing import Any

import sphinx_github_changelog.changelog

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
    "sphinx_llm.txt",
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

# -- Options for LLM-friendly output -----------------------------------------

# The default is the full README, which is too long for the summary block
llms_txt_description = (
    "Documentation of histogram indexing, the PlottableHistogram Protocol, and"
    " the histogram serialization format, with tools for library authors."
)


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "furo"

html_theme_options = {
    "source_repository": "https://github.com/scikit-hep/uhi",
    "source_branch": "main",
    "source_directory": "docs/",
}


# -- Changelog builder -------------------------------------------------------

# GitHub release notes start at H2. The changelog extension parses them with
# default docutils settings, so suppress_warnings in this file has no effect.
_changelog_default_settings = sphinx_github_changelog.changelog.get_default_settings


def _changelog_settings(*components: Any) -> Any:
    settings = _changelog_default_settings(*components)
    settings.myst_suppress_warnings = ["myst.header"]
    return settings


sphinx_github_changelog.changelog.get_default_settings = _changelog_settings

if "GITHUB_API_TOKEN" in os.environ:
    sphinx_github_changelog_token = os.environ["GITHUB_API_TOKEN"]

commit = os.environ.get("READTHEDOCS_GIT_COMMIT_HASH", "main")
code_url = "https://github.com/scikit-hep/uhi/blob"
