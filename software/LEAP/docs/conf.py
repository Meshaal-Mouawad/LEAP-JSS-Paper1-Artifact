# Configuration file for the Sphinx documentation builder.
import os
import sys

sys.path.insert(0, os.path.abspath(".."))  # To find project modules if needed

# -- Project information -----------------------------------------------------
project = "KPI Intelligence Workspace"
copyright = "2025, Meshaal Mouawad"
author = "Meshaal Mouawad"

# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.mathjax",  # required to render .. math:: blocks
]
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Force MathJax v3 (works regardless of Sphinx default)
mathjax_path = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"

# MathJax v3 config (used by modern Sphinx)
mathjax3_config = {
    "tex": {
        "inlineMath": [["$", "$"], ["\\(", "\\)"]],
        "displayMath": [["$$", "$$"], ["\\[", "\\]"]],
        "processEscapes": True,
    },
    "chtml": {
        "mtextInheritFont": True,
        "displayAlign": "left",
    },
    "options": {
        # Process formal and annotated formula containers, including nested dynamic blocks.
        "processHtmlClass": "formula-panel|leap-annotated-equation|leap-annotated-formula-wrapper|leap-business-formula-math|math-equation",
        "ignoreHtmlClass": "tex2jax_ignore",
    },
}

# MathJax v2 fallback (used by older Sphinx)
mathjax_config = {
    "tex2jax": {
        "inlineMath": [["$", "$"], ["\\(", "\\)"]],
        "displayMath": [["$$", "$$"], ["\\[", "\\]"]],
        "processClass": "math-equation|leap-business-formula-math",
        "ignoreClass": "tex2jax_ignore",
    },
    "HTML-CSS": {
        "mtextFontInherit": True,
    },
}

# -- Options for HTML output -------------------------------------------------
html_theme = "basic"
html_static_path = ["_static"]
html_title = "KPI Intelligence Workspace"
html_short_title = "KPI Intelligence"


def setup(app):
    app.add_js_file(
        None,
        body=(
            "window.MathJax = {"
            "tex: {"
            "inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], "
            "displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']], "
            "processEscapes: true"
            "}, "
            "options: {"
            "processHtmlClass: 'formula-panel|leap-annotated-equation|leap-annotated-formula-wrapper|leap-business-formula-math|math-equation', "
            "ignoreHtmlClass: 'tex2jax_ignore'"
            "}, "
            "chtml: {"
            "linebreaks: {automatic: true, width: 'container'}, "
            "mtextInheritFont: true, "
            "displayAlign: 'left'"
            "}, "
            "startup: {"
            "pageReady: function () {"
            "return MathJax.startup.defaultPageReady().then(function () {"
            "if (window.MathJax && window.MathJax.typeset) { window.MathJax.typeset(); }"
            "});"
            "}"
            "}"
            "};"
        ),
    )
    app.add_js_file(
        "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js",
        loading_method="defer",
    )
    app.add_css_file("custom.css")
    app.add_css_file("leap/ECDS_TOKENS.css")
