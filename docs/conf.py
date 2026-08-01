"""Configuration file for the Sphinx documentation builder."""

import importlib.metadata

project = "simplifiapi"
copyright = "2025, senderic"
author = "senderic"
try:
    release = importlib.metadata.version("simplifiapi")
except importlib.metadata.PackageNotFoundError:
    release = "0.0.1"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_title = "simplifiapi"
html_static_path = ["_static"]

autodoc_typehints = "description"
napoleon_google_docstring = True
napoleon_numpy_docstring = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
}
