"""Meta-test: every backend module under app/ must import cleanly.

This is the first line of defense against silent breakage — a single bad
import (typo, missing dep, circular import) breaks a module without ever
showing up in unit tests that don't import it. Parametrizing over the
entire app tree catches this universally.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

import app

# Modules that legitimately can't be imported in isolation (e.g. require
# special env, or are scripts that execute on import).
_SKIP_PREFIXES: tuple[str, ...] = (
    # Alembic migration env runs at import time
    "app.migrations.env",
)


def _walk_modules() -> list[str]:
    out: list[str] = []
    pkg_path = Path(app.__file__).parent
    for mod in pkgutil.walk_packages([str(pkg_path)], prefix="app."):
        name = mod.name
        if any(name.startswith(p) for p in _SKIP_PREFIXES):
            continue
        out.append(name)
    return sorted(out)


_MODULES = _walk_modules()


@pytest.mark.parametrize("module_name", _MODULES, ids=_MODULES)
def test_module_imports(module_name: str):
    """Every app.* module must import without error."""
    importlib.import_module(module_name)


def test_meta_module_count_sane():
    assert len(_MODULES) >= 100, f"only discovered {len(_MODULES)} modules"
