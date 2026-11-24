"""Sphinx configuration for Stocky Chess documentation."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("../../src"))

project = "Stocky Chess"
copyright = "2023-2026, Stocky Chess Contributors"
author = "Stocky Chess Contributors"

version_file = Path(__file__).resolve().parents[2] / "VERSION"
release = version_file.read_text(encoding="utf-8").strip() if version_file.exists() else "1.0.0"
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
]

autodoc_mock_imports = ["PyQt6"]
autodoc_member_order = "bysource"

templates_path = ["_templates"]
exclude_patterns = []

html_theme = "sphinx_rtd_theme"
