"""A fake ThreeMFModel + build items for testing core operations without lib3mf.

The core operations only use this surface of ThreeMFModel:
  build_items(), get_transform(bi), set_transform(bi, m),
  compose_transform(bi, m), item_min_z(bi), item_vertices(bi).
"""

from freecad.tools_for_print.core import transform as tf


class FakeBuildItem:
    def __init__(self, vertices, transform=None):
        self.vertices = vertices           # list of (x,y,z) local coords
        self.transform = transform or tf.identity()


class FakeModel:
    """Mimics core.model.ThreeMFModel for the operations under test."""

    def __init__(self, items):
        self._items = items

    def build_items(self):
        return list(self._items)

    def get_transform(self, bi):
        return [row[:] for row in bi.transform]

    def set_transform(self, bi, m):
        bi.transform = [row[:] for row in m]

    def compose_transform(self, bi, m):
        bi.transform = tf.matmul(m, bi.transform)

    def item_vertices(self, bi):
        return list(bi.vertices)

    def item_min_z(self, bi):
        if not bi.vertices:
            return None
        return min(tf.transformed_z(bi.transform, p) for p in bi.vertices)
