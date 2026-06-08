"""Минимальный setup.py для совместимости со старыми версиями pip (editable install)."""

import re
from pathlib import Path

from setuptools import setup


def _read_version() -> str:
    text = (Path(__file__).parent / "release_parameters.yml").read_text()
    m = re.search(r'^version:\s*["\']?([^"\'\s]+)', text, re.MULTILINE)
    if not m:
        raise RuntimeError("version not found in release_parameters.yml")
    return m.group(1)


setup(version=_read_version())
