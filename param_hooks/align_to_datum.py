"""Align a chosen datum face to the build plate (parametric DatumHook).

Unlike the stateless 'align_face_to_plate' hook (which uses the live 3D
selection at run time), this parametric version stores the chosen face as a
link on the DatumHook object, so it recomputes deterministically whenever the
geometry changes — no interactive selection during recompute.

Phase A (panel): the user fulfils PlateFace by picking a planar face.
Phase B (execute): compute() reads that resolved face and returns the transform
that rotates its normal to point down (-Z), laying it on the plate.
"""

REQUIREMENTS = [
    {
        "id": "PlateFace",
        "type": "selection",
        "label": "Planar face to lay on the build plate",
    },
]


def compute(inputs):
    """Deterministic: face -> 3x4 transform rotating its normal to -Z.

    Returns the core.transform 3x4 row-major convention. UI-free.
    """
    import FreeCAD
    from freecad.print_exporter.gui import selection as sel

    face = inputs.get("PlateFace")
    if face is None or getattr(face, "ShapeType", "") != "Face":
        # Not fulfilled / wrong kind -> identity (execute() also guards on this).
        from freecad.print_exporter.core import transform as tf
        return tf.identity()

    # Reuse the same normal->-Z math the stateless hook uses.
    return sel.transform_align_face_down(face)
