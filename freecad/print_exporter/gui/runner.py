# SPDX-License-Identifier: MIT
"""Orchestrates one workflow run: export -> load -> hooks -> save -> slice.

Pipeline:
  1. Export the selected FreeCAD objects to a base .3mf (FreeCAD Mesh).
  2. Load it as a ThreeMFModel (lib3mf).
  3. Build a HookContext and run each chosen hook against it, in order.
  4. Save the modified model to the output path.
  5. Optionally open the .3mf in a slicer (default OrcaSlicer).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

from ..core.model import ThreeMFModel
from . import mesh_export
from .context import HookContext

# Default slicer to hand the exported 3MF to (matches the reference macro's
# auto-workflow-to-slicer behaviour). Overridable in the dialog.
DEFAULT_SLICER = "/usr/bin/orca-slicer"


def open_in_slicer(path, slicer=DEFAULT_SLICER, log=None):
    """Launch the slicer with the 3MF file (detached). Returns True if started.

    Mirrors the reference macro: subprocess.Popen([slicer, file]) guarded by an
    existence check. Falls back to xdg-open if the slicer path is missing.
    """
    log = log or (lambda m: print("[3mf]", m))
    path = str(path)
    if slicer and os.path.exists(slicer):
        try:
            subprocess.Popen([slicer, path])
            log(f"Opened in slicer: {slicer}")
            return True
        except Exception as exc:
            log(f"Failed to launch slicer '{slicer}': {exc}")
            return False
    # No valid slicer path — let the desktop pick a handler.
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif os.name == "nt":
            os.startfile(path)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", path])
        log(f"Slicer '{slicer}' not found; opened via desktop handler.")
        return True
    except Exception as exc:
        log(f"Could not open {path}: {exc}")
        return False


def run_workflow(objects, hook_callables, out_path, log=None,
                 slicer=None, launch_slicer=False, fuse=False,
                 datum_transforms=None):
    """Return (out_path, [hook results]). `hook_callables` are hook(ctx) fns.

    If fuse is True, the selected solids are boolean-fused into one manifold
    before meshing. datum_transforms is an optional list of 3x4 transforms
    (from DatumHook objects' Placements) composed onto every build item before
    the stateless hooks run. If launch_slicer is True, opens the saved 3MF in
    `slicer` (default OrcaSlicer).
    """
    log = log or (lambda m: print("[3mf]", m))
    if not objects:
        raise ValueError("No FreeCAD objects selected to export.")

    # 1. base 3mf from FreeCAD meshing (temp)
    fd, tmp3mf = tempfile.mkstemp(suffix=".3mf")
    os.close(fd)
    try:
        mesh_export.objects_to_3mf(objects, tmp3mf, fuse=fuse)
        log(f"Exported {len(objects)} object(s) to base 3MF"
            + (" (fused)." if fuse else "."))

        # 2. load with lib3mf
        model = ThreeMFModel.load(tmp3mf)
        log(f"Loaded {len(model.build_items())} build item(s).")

        # 2b. apply DatumHook transforms (parametric hooks resolved in the tree)
        if datum_transforms:
            from ..core import operations as ops
            for t in datum_transforms:
                ops.apply_to_all(model, t)
            log(f"Applied {len(datum_transforms)} datum transform(s).")

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

        # 5. hand off to the slicer
        if launch_slicer:
            open_in_slicer(out_path, slicer or DEFAULT_SLICER, log=log)

        return out_path, results
    finally:
        try:
            os.remove(tmp3mf)
        except OSError:
            pass
