# SPDX-License-Identifier: MIT
"""Thin, FreeCAD-free wrapper over lib3mf model I/O and build-item transforms.

Everything that touches the lib3mf API surface lives here so the rest of the
codebase (and hooks) talk to a small, stable interface. Import of lib3mf is
lazy so this module can be imported for its type hints even where lib3mf is
absent; the actual calls require it.
"""

from __future__ import annotations

from . import transform as tf


def load_wrapper():
    import lib3mf

    return lib3mf, lib3mf.Wrapper()


class ThreeMFModel:
    """A loaded (or new) 3MF model plus convenience over its build items."""

    def __init__(self, lib3mf, wrapper, model):
        self.lib3mf = lib3mf
        self.wrapper = wrapper
        self.model = model

    # -- construction ------------------------------------------------------ #
    @classmethod
    def load(cls, path: str) -> "ThreeMFModel":
        lib3mf, wrapper = load_wrapper()
        model = wrapper.CreateModel()
        reader = model.QueryReader("3mf")
        reader.ReadFromFile(str(path))
        return cls(lib3mf, wrapper, model)

    @classmethod
    def new(cls) -> "ThreeMFModel":
        lib3mf, wrapper = load_wrapper()
        return cls(lib3mf, wrapper, wrapper.CreateModel())

    def save(self, path: str) -> None:
        writer = self.model.QueryWriter("3mf")
        writer.WriteToFile(str(path))

    # -- build items ------------------------------------------------------- #
    def build_items(self) -> list:
        items = []
        it = self.model.GetBuildItems()
        while it.MoveNext():
            items.append(it.GetCurrent())
        return items

    def get_transform(self, build_item) -> list[list[float]]:
        if build_item.HasObjectTransform():
            return tf.from_lib3mf(build_item.GetObjectTransform())
        return tf.identity()

    def set_transform(self, build_item, m: list[list[float]]) -> None:
        build_item.SetObjectTransform(tf.to_lib3mf(self.wrapper, m))

    def compose_transform(self, build_item, m: list[list[float]]) -> None:
        """Apply `m` on top of the item's existing transform (m then current)."""
        cur = self.get_transform(build_item)
        self.set_transform(build_item, tf.matmul(m, cur))

    # -- geometry ---------------------------------------------------------- #
    def item_vertices(self, build_item):
        """Yield (x, y, z) tuples of the item's object mesh in local coords.

        Handles the common single-mesh object. Component assemblies are skipped
        (return empty) — extend here if you need nested components.
        """
        obj = build_item.GetObjectResource()
        get_verts = getattr(obj, "GetVertices", None)
        if get_verts is None:
            return []
        verts = get_verts()
        out = []
        for v in verts:
            c = v.Coordinates
            out.append((c[0], c[1], c[2]))
        return out

    def item_min_z(self, build_item) -> float | None:
        m = self.get_transform(build_item)
        verts = self.item_vertices(build_item)
        if not verts:
            return None
        return min(tf.transformed_z(m, p) for p in verts)
