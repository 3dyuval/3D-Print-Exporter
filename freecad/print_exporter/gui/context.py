# SPDX-License-Identifier: MIT
"""HookContext — the rich `ctx` object every hook receives.

Guided helpers on top, raw lib3mf/model handles reachable underneath:

    def hook(ctx):
        face = ctx.selected_face()
        t = ctx.transform_from_face(face)   # align that face to the plate
        ctx.set_build_transform(t)
        ctx.ensure_on_bed()
        # power users:
        for bi in ctx.model.build_items():
            ...                              # raw ThreeMFModel / lib3mf handles
"""

from __future__ import annotations

from ..core import operations as ops
from ..core import transform as tf
from . import selection as sel


class HookContext:
    def __init__(self, model, log=None):
        # raw handles ------------------------------------------------------ #
        self.model = model                 # core.model.ThreeMFModel
        self.lib3mf = model.lib3mf
        self.wrapper = model.wrapper
        self.raw_model = model.model        # the underlying lib3mf model
        self._log = log or (lambda m: print("[3mf-hook]", m))

        import FreeCAD
        import FreeCADGui
        self.FreeCAD = FreeCAD
        self.Gui = FreeCADGui
        self.doc = FreeCAD.ActiveDocument

    # -- logging ----------------------------------------------------------- #
    def log(self, msg):
        self._log(str(msg))

    # -- selection --------------------------------------------------------- #
    def selected_face(self):
        return sel.selected_face()

    def selected_plane_normal(self):
        face = sel.selected_face()
        return None if face is None else sel.face_normal(face)

    # -- transform builders (return core 3x4 matrices) --------------------- #
    def transform_from_face(self, face=None):
        face = face or sel.selected_face()
        if face is None:
            raise ValueError("No face selected — select a planar face first.")
        return sel.transform_align_face_down(face)

    def rotate_z(self, degrees):
        return sel.transform_rotate_z(degrees)

    def translate(self, dx, dy, dz):
        return tf.translation(dx, dy, dz)

    def identity(self):
        return tf.identity()

    # -- build-item manipulation ------------------------------------------ #
    def build_items(self):
        return self.model.build_items()

    def set_build_transform(self, m, item=None):
        """Replace transform on one item (or all if item is None)."""
        targets = [item] if item is not None else self.model.build_items()
        for bi in targets:
            self.model.set_transform(bi, m)

    def apply_build_transform(self, m, item=None):
        """Compose transform on top of existing (one item, or all)."""
        targets = [item] if item is not None else self.model.build_items()
        for bi in targets:
            self.model.compose_transform(bi, m)

    # -- high-level ops ---------------------------------------------------- #
    def ensure_on_bed(self, allow_negative_z=False, sink_threshold=0.05):
        n = ops.ensure_on_bed(self.model, allow_negative_z, sink_threshold)
        self.log(f"ensure_on_bed: adjusted {n} build item(s)")
        return n
