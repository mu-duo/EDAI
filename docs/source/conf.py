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
themes = [
    "alabaster",     # 0
    "classic",       # 1
    "sphinxdoc",     # 2
    "scrolls",       # 3
    "agogo",         # 4
    "traditional",   # 5
    "nature",        # 6
    "haiku",         # 7
    "pyramid",       # 8
    "bizstyle",      # 9
]
# Recommended 4, 6, 8
html_theme = themes[6]
html_static_path = ["_static"]
html_css_files = ["custom.css"]

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
