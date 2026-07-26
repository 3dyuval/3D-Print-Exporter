# SPDX-License-Identifier: MIT
"""FreeCAD selection helpers -> geometry the core layer can consume.

Isolated here so the pure core stays FreeCAD-free. These turn the current GUI
selection (a face / plane) into a 3x4 transform expressed in core's convention.
"""

from __future__ import annotations

from ..core import transform as tf


def selected_face():
    """First selected planar-ish Face SubObject across the selection, or None."""
    import FreeCADGui as Gui

    for s in Gui.Selection.getSelectionEx():
        for sub in getattr(s, "SubObjects", []):
            if getattr(sub, "ShapeType", "") == "Face":
                return sub
    return None


def face_normal(face):
    """Unit outward normal (FreeCAD.Vector) at the face's parametric centre."""
    u0, u1, v0, v1 = face.ParameterRange
    n = face.normalAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
    n.normalize()
    return n


def transform_align_face_down(face) -> list[list[float]]:
    """3x4 transform rotating `face`'s normal to point down (-Z).

    This is the "make this face the base" operation. Translation is left at
    zero; pair with ensure_on_bed() to drop onto the plate.
    """
    import FreeCAD

    n = face_normal(face)
    rot = FreeCAD.Rotation(n, FreeCAD.Vector(0, 0, -1))
    return _rotation_to_matrix(rot)


def transform_rotate_z(degrees: float) -> list[list[float]]:
    import FreeCAD

    rot = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), degrees)
    return _rotation_to_matrix(rot)


def _rotation_to_matrix(rot) -> list[list[float]]:
    """FreeCAD.Rotation -> core 3x4 row-major matrix (no translation)."""
    import FreeCAD

    m = FreeCAD.Placement(FreeCAD.Vector(0, 0, 0), rot).toMatrix()
    return [
        [m.A11, m.A12, m.A13, m.A14],
        [m.A21, m.A22, m.A23, m.A24],
        [m.A31, m.A32, m.A33, m.A34],
    ]
