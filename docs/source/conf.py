# Configuration file for the Sphinx documentation builder.

from __future__ import annotations

# ── Project information -----------------------------------------------------
project = "EDAI"
copyright = "2026, tanlinfeng"
author = "tanlinfeng"
release = "0.1.0"

# ── Language ----------------------------------------------------------------
language = "en"

# ── General configuration ---------------------------------------------------
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
]

# ── Options for HTML output -------------------------------------------------
html_theme = "alabaster"
html_static_path = ["_static"]
html_css_files = ["custom.css"]

html_theme_options = {
    "description": "AI-powered CLI toolkit for EDA workflows",
    "github_button": True,
    "github_user": "tanlinfeng",
    "github_repo": "EDAI",
    "fixed_sidebar": True,
    "sidebar_collapse": True,
}

# ── Language-specific single-file builds ------------------------------------
# Controlled by -t <tag> on the sphinx-build command line.
#   make singlehtml_en   → passes -t language_en
#   make singlehtml_zh   → passes -t language_zh
if tags.has("language_en"):  # type: ignore[name-defined]
    exclude_patterns.extend([
        "zh/overview.rst",
        "zh/usage.rst",
        "zh/architecture.rst",
        "zh/index.rst",
    ])
elif tags.has("language_zh"):  # type: ignore[name-defined]
    exclude_patterns.extend([
        "overview.rst",
        "usage.rst",
        "architecture.rst",
    ])
