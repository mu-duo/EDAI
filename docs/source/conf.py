# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from __future__ import annotations

import os

# ── Language ----------------------------------------------------------------
# Set EDAI_LANG=en or EDAI_LANG=zh before building.
_lang: str = os.environ.get("EDAI_LANG", "en").strip().lower()
language = _lang

# ── Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "EDAI"
copyright = "2026, tanlinfeng"
author = "tanlinfeng"
release = "0.1.0"

# ── General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.intersphinx",
]

autosectionlabel_prefix_document = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

templates_path = ["_templates"]
exclude_patterns = [
    "feaeture.md",
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "en",
    "zh",
]

# ── Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]
html_css_files = ["custom.css"]

if _lang == "zh":
    html_theme_options = {
        "description": "AI 驱动的 EDA 工作流 CLI 工具包",
        "github_button": True,
        "github_user": "tanlinfeng",
        "github_repo": "EDAI",
        "fixed_sidebar": True,
        "sidebar_collapse": True,
    }
else:
    html_theme_options = {
        "description": "AI-powered CLI toolkit for EDA workflows",
        "github_button": True,
        "github_user": "tanlinfeng",
        "github_repo": "EDAI",
        "fixed_sidebar": True,
        "sidebar_collapse": True,
    }

html_context = {
    "display_language": _lang,
}
