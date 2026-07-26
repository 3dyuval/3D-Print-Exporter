# SPDX-License-Identifier: MIT
"""Reusable build-plate operations, expressed against ThreeMFModel.

These are the FreeCAD-free primitives that both the built-in actions and the
user hooks build on. Kept pure so they can be unit-tested with a fake model.
"""

from __future__ import annotations

from . import transform as tf


def ensure_on_bed(model, allow_negative_z: bool = False, sink_threshold: float = 0.05) -> int:
    """Drop every build item so its lowest point sits on z=0.

    Port of OrcaSlicer's ModelObject::ensure_on_bed(). Composes a +Z translation
    onto each item's existing transform. Returns the number of items moved.
    """
    moved = 0
    for bi in model.build_items():
        min_z = model.item_min_z(bi)
        if min_z is None:
            continue
        if allow_negative_z and -sink_threshold < min_z < sink_threshold:
            z_off = 0.0
        else:
            z_off = -min_z
        if abs(z_off) > 1e-9:
            model.compose_transform(bi, tf.translation(0.0, 0.0, z_off))
            moved += 1
    return moved


def apply_to_all(model, m: list[list[float]]) -> int:
    """Compose transform `m` onto every build item. Returns count."""
    items = model.build_items()
    for bi in items:
        model.compose_transform(bi, m)
    return len(items)


def set_on_all(model, m: list[list[float]]) -> int:
    """Replace every build item's transform with `m`. Returns count."""
    items = model.build_items()
    for bi in items:
        model.set_transform(bi, m)
    return len(items)
