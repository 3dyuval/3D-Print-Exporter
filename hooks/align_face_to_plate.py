"""Lay a selected face flat on the build plate.

Select one planar face in FreeCAD before running the workflow, then check this
hook. It rotates the part so the face's normal points down (-Z), then drops the
part onto z=0 — ready to slice.
"""


def hook(ctx):
    face = ctx.selected_face()
    if face is None:
        ctx.log("No face selected — select a planar face and re-run.")
        return
    t = ctx.transform_from_face(face)   # rotate face normal -> -Z
    ctx.apply_build_transform(t)        # compose onto all build items
    ctx.ensure_on_bed()                 # then sit it on the bed
    ctx.log("Aligned selected face to plate.")
