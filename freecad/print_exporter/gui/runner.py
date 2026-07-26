# SPDX-License-Identifier: MIT
"""Orchestrates one workflow run: export -> load -> hooks -> save.

Pipeline:
  1. Export the selected FreeCAD objects to a base .3mf (FreeCAD Mesh).
  2. Load it as a ThreeMFModel (lib3mf).
  3. Build a HookContext and run each chosen hook against it, in order.
  4. Save the modified model to the output path.
"""

from __future__ import annotations

import os
import tempfile

from ..core.model import ThreeMFModel
from . import mesh_export
from .context import HookContext


def run_workflow(objects, hook_callables, out_path, log=None):
    """Return (out_path, [hook results]). `hook_callables` are hook(ctx) fns."""
    log = log or (lambda m: print("[3mf]", m))
    if not objects:
        raise ValueError("No FreeCAD objects selected to export.")

    # 1. base 3mf from FreeCAD meshing (temp)
    fd, tmp3mf = tempfile.mkstemp(suffix=".3mf")
    os.close(fd)
    try:
        mesh_export.objects_to_3mf(objects, tmp3mf)
        log(f"Exported {len(objects)} object(s) to base 3MF.")

        # 2. load with lib3mf
        model = ThreeMFModel.load(tmp3mf)
        log(f"Loaded {len(model.build_items())} build item(s).")

        # 3. run hooks
        ctx = HookContext(model, log=log)
        results = []
        for fn in hook_callables:
            results.append(fn(ctx))

        # 4. save
        out_path = str(out_path)
        if not out_path.lower().endswith(".3mf"):
            out_path += ".3mf"
        model.save(out_path)
        log(f"Wrote {out_path}")
        return out_path, results
    finally:
        try:
            os.remove(tmp3mf)
        except OSError:
            pass
