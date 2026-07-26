# SPDX-License-Identifier: MIT
"""Self-install the addon's Python dependency (lib3mf) into FreeCAD's Python.

FreeCAD 1.1 ships its own interpreter (Python 3.14). lib3mf is a pure `py3-none`
wheel, so `pip install --user lib3mf` drops it on FreeCAD's sys.path with no
compiled-extension mismatch. We run pip *from inside FreeCAD* so the user never
needs a terminal — call ensure_lib3mf() and it's idempotent (no-op once present).

We deliberately install to the user site (--user): it's writable without root,
survives FreeCAD updates, and is already on sys.path.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys


def _python_exe() -> str:
    """Best guess at a real python interpreter for FreeCAD's environment.

    sys.executable is sometimes the FreeCAD binary (e.g. /usr/bin/freecad),
    which is NOT a python entry point. Prefer a versioned python3.X matching the
    running interpreter, falling back to plain python3, then sys.executable.
    """
    major, minor = sys.version_info[:2]
    prefix = getattr(sys, "base_prefix", sys.prefix)
    candidates = [
        os.path.join(prefix, "bin", f"python{major}.{minor}"),
        os.path.join(prefix, "bin", "python3"),
        f"/usr/bin/python{major}.{minor}",
        "/usr/bin/python3",
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return sys.executable


def is_installed() -> bool:
    try:
        importlib.import_module("lib3mf")
        return True
    except Exception:
        return False


def install(log=print) -> bool:
    """pip install --user lib3mf into FreeCAD's Python. Returns True on success."""
    if is_installed():
        return True
    exe = _python_exe()
    log(f"Installing lib3mf via {exe} ...")
    try:
        proc = subprocess.run(
            [exe, "-m", "pip", "install", "--user", "--disable-pip-version-check", "lib3mf"],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception as exc:  # subprocess itself failed to launch
        log(f"pip launch failed: {exc}")
        return False

    if proc.returncode != 0:
        log("pip install failed:\n" + (proc.stderr or proc.stdout)[-800:])
        return False

    # Make the freshly-installed package importable in THIS session without a
    # restart: ensure user-site is on sys.path and drop any negative import cache.
    import site
    usp = site.getusersitepackages()
    if usp not in sys.path and os.path.isdir(usp):
        sys.path.append(usp)
    importlib.invalidate_caches()
    ok = is_installed()
    log("lib3mf installed and importable." if ok else "installed but still not importable (restart FreeCAD).")
    return ok


def ensure_lib3mf(log=print) -> bool:
    """Idempotent: import if present, else install. Safe to call at startup."""
    return is_installed() or install(log=log)
