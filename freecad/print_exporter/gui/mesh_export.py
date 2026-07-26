# SPDX-License-Identifier: MIT
"""Export selected FreeCAD objects to a base .3mf that the workflow then edits.

We let FreeCAD's Mesh module produce the initial 3MF (it handles tessellation,
placement baking, multi-object), then reopen it with lib3mf to apply transforms
and hooks. This avoids re-implementing meshing and matches how the reference
macro and Parametric-Export produce their 3MF.
"""

from __future__ import annotations


def _fuse_shapes(objects):
    """Boolean-fuse the objects' solids into one Part::Feature (temporary).

    Returns (feature, is_temporary). Per the 3MF spec, producers SHOULD NOT emit
    overlapping geometry, so we build a single watertight solid here rather than
    relying on the consumer's MUST-unite behaviour. Objects without a .Shape
    (meshes, sketches) are skipped; if fewer than two solids remain, the input
    is returned unchanged.
    """
    import FreeCAD

    shaped = [o for o in objects if getattr(o, "Shape", None) is not None
              and not o.Shape.isNull()]
    if len(shaped) < 2:
        return None, False

    base = shaped[0].Shape
    fused = base.fuse([o.Shape for o in shaped[1:]])
    fused = fused.removeSplitter()  # merge coplanar faces from the boolean

    doc = FreeCAD.ActiveDocument
    feat = doc.addObject("Part::Feature", "PrintExporter_Fused")
    feat.Shape = fused
    doc.recompute()
    return feat, True


def objects_to_3mf(objects, out_path: str, fuse: bool = False) -> str:
    """Export FreeCAD objects to out_path (.3mf). Returns the path written.

    If fuse=True, boolean-fuse the selected solids into one manifold before
    meshing (spec-clean single solid instead of overlapping build items).
    """
    import Mesh

    out_path = str(out_path)
    if not out_path.lower().endswith(".3mf"):
        out_path += ".3mf"

    temp_feat = None
    try:
        export_objs = list(objects)
        if fuse:
            temp_feat, is_temp = _fuse_shapes(objects)
            if temp_feat is not None:
                export_objs = [temp_feat]

        if hasattr(Mesh, "exportOptions"):
            options = Mesh.exportOptions(out_path)
            Mesh.export(export_objs, out_path, options)
        else:
            Mesh.export(export_objs, out_path)
        return out_path
    finally:
        if temp_feat is not None:
            import FreeCAD
            try:
                FreeCAD.ActiveDocument.removeObject(temp_feat.Name)
            except Exception:
                pass


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
