# SPDX-License-Identifier: MIT
"""Discovery and loading of user hook scripts.

Hooks are plain .py files in a hooks/ directory (bundled defaults + a
user-writable dir). Each must define `hook(ctx)`. Discovery is FreeCAD-free and
testable; execution needs a HookContext (built in gui/context.py).
"""

from __future__ import annotations

import importlib.util
import os
import ast
from dataclasses import dataclass


def _read_docstring(path: str) -> str:
    """Return a file's module docstring WITHOUT executing it (ast parse)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return (ast.get_docstring(ast.parse(fh.read())) or "").strip()
    except Exception:
        return ""


@dataclass
class HookScript:
    name: str          # display name (filename without .py)
    path: str          # absolute path
    source: str        # "builtin" | "user"
    description: str = ""   # module docstring (declared description)

    @property
    def summary(self) -> str:
        """First non-empty line of the description, for compact tooltips."""
        for line in self.description.splitlines():
            if line.strip():
                return line.strip()
        return ""

    def load_callable(self):
        """Import the module in isolation and return its hook(ctx) callable."""
        spec = importlib.util.spec_from_file_location(
            f"threemf_hook_{self.name}", self.path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fn = getattr(module, "hook", None)
        if not callable(fn):
            raise AttributeError(
                f"Hook '{self.name}' ({self.path}) has no callable hook(ctx)."
            )
        return fn


def discover(dirs: list[tuple[str, str]]) -> list[HookScript]:
    """Find hooks across (dir, source) pairs. Later dirs override earlier ones
    by name, so a user hook shadows a bundled one of the same name.
    """
    found: dict[str, HookScript] = {}
    for d, source in dirs:
        if not d or not os.path.isdir(d):
            continue
        for entry in sorted(os.listdir(d)):
            if not entry.endswith(".py") or entry.startswith("_"):
                continue
            name = entry[:-3]
            full = os.path.join(d, entry)
            found[name] = HookScript(
                name=name, path=full, source=source,
                description=_read_docstring(full),
            )
    return sorted(found.values(), key=lambda h: h.name)
