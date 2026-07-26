# SPDX-License-Identifier: MIT
"""Resolve hook directories: bundled defaults + a user-writable dir."""

from __future__ import annotations

import os

from .. import ADDON_ROOT, BUILTIN_HOOKS_DIR


def user_hooks_dir() -> str:
    """~/.../FreeCAD/<ver>/tools_for_print_hooks — created on demand.

    Uses FreeCAD's user data dir so it survives across the app but stays out of
    the addon (which the Addon Manager may overwrite on update).
    """
    import FreeCAD

    base = FreeCAD.getUserAppDataDir()
    d = os.path.join(base, "tools_for_print_hooks")
    os.makedirs(d, exist_ok=True)
    return d


def hook_dirs() -> list[tuple[str, str]]:
    """(dir, source) pairs, user last so it shadows builtins by name."""
    return [
        (BUILTIN_HOOKS_DIR, "builtin"),
        (user_hooks_dir(), "user"),
    ]


def user_param_hooks_dir() -> str:
    import FreeCAD

    d = os.path.join(FreeCAD.getUserAppDataDir(), "tools_for_print_param_hooks")
    os.makedirs(d, exist_ok=True)
    return d


def param_hook_dirs() -> list[tuple[str, str]]:
    """Dirs for parametric (DatumHook) macros: bundled param_hooks/ + user dir."""
    return [
        (os.path.join(ADDON_ROOT, "param_hooks"), "builtin"),
        (user_param_hooks_dir(), "user"),
    ]
