# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'API Builder'
copyright = '2024, API Builder Contributors'
author = 'API Builder Contributors'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',           # Auto-generate docs from docstrings
    'sphinx.ext.viewcode',          # Add source code links
    'sphinx.ext.napoleon',          # Support for Google/NumPy style docstrings
    'sphinx.ext.intersphinx',       # Link to other projects' documentation
    'sphinx.ext.autosummary',       # Generate summary tables
    'sphinx.ext.coverage',          # Documentation coverage checking
    'sphinx.ext.todo',              # Support for todo items
    'sphinx.ext.ifconfig',          # Conditional documentation
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output ------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'  # Modern, clean theme
html_static_path = ['_static']
html_title = 'API Builder Documentation'

# Theme options
html_theme_options = {
    "sidebar_hide_name": True,
    "navigation_with_keys": True,
    "top_of_page_button": "edit",
    "source_repository": "https://github.com/cvanleer/api-builder/",
    "source_branch": "main",
    "source_directory": "docs/",
}

# -- Extension configuration -------------------------------------------------

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Intersphinx mappings
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'typer': ('https://typer.tiangolo.com', None),
    'rich': ('https://rich.readthedocs.io/en/stable', None),
    'pydantic': ('https://docs.pydantic.dev/latest', None),
}

# Autosummary settings
autosummary_generate = True
autosummary_generate_overwrite = False

# Todo extension
todo_include_todos = True
todo_emit_warnings = True

# Coverage options
coverage_show_missing_items = True