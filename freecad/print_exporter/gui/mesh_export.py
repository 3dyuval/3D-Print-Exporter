# SPDX-License-Identifier: MIT
"""Export selected FreeCAD objects to a base .3mf that the workflow then edits.

We let FreeCAD's Mesh module produce the initial 3MF (it handles tessellation,
placement baking, multi-object), then reopen it with lib3mf to apply transforms
and hooks. This avoids re-implementing meshing and matches how the reference
macro and Parametric-Export produce their 3MF.
"""

from __future__ import annotations


def objects_to_3mf(objects, out_path: str) -> str:
    """Export FreeCAD objects to out_path (.3mf). Returns the path written."""
    import Mesh

    out_path = str(out_path)
    if not out_path.lower().endswith(".3mf"):
        out_path += ".3mf"

    if hasattr(Mesh, "exportOptions"):
        options = Mesh.exportOptions(out_path)
        Mesh.export(objects, out_path, options)
    else:
        Mesh.export(objects, out_path)
    return out_path


def selected_objects():
    """Distinct top-level document objects in the current selection."""
    import FreeCADGui as Gui

    seen, out = set(), []
    for s in Gui.Selection.getSelectionEx():
        obj = s.Object
        if obj is not None and obj.Name not in seen:
            seen.add(obj.Name)
            out.append(obj)
    return out
