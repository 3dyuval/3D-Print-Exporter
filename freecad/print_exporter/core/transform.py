# SPDX-License-Identifier: MIT
"""Affine-transform helpers bridging plain 3x4 matrices and lib3mf Transforms.

Kept FreeCAD-free so it is unit-testable without a running FreeCAD (see tests/).
The only external type is lib3mf's Transform; callers pass a wrapper in.

3MF / lib3mf conventions (verified against lib3mf 2.5.0):
  * lib3mf Transform.Fields is a ctypes [4][3] array, COLUMN-MAJOR: Fields[col][row].
    Column 3 (Fields[3]) is the translation vector.
  * The 3MF XML serialises the same matrix as 12 numbers, row-major 3x3 then
    translation: "r00 r01 r02  r10 r11 r12  r20 r21 r22  tx ty tz".

We represent a transform internally as a 3x4 row-major nested list `M`:
    M = [[r00, r01, r02, tx],
         [r10, r11, r12, ty],
         [r20, r21, r22, tz]]
which matches the 3MF XML order and is easy to reason about / test.
"""

from __future__ import annotations


def identity() -> list[list[float]]:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
    ]


def translation(dx: float, dy: float, dz: float) -> list[list[float]]:
    m = identity()
    m[0][3], m[1][3], m[2][3] = float(dx), float(dy), float(dz)
    return m


def mirror(axis: str) -> list[list[float]]:
    """Mirror across the plane normal to `axis` ('x'|'y'|'z'), through origin.

    Implemented as a negative scale on that axis. Note this flips triangle
    winding; per the 3MF spec consumers treat model volumes with a positive fill
    rule, so slicers handle it, but pair with ensure_on_bed() since mirroring
    across an origin plane moves the part.
    """
    i = {"x": 0, "y": 1, "z": 2}[axis.lower()]
    m = identity()
    m[i][i] = -1.0
    return m


def matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    """Compose two 3x4 affine transforms: result applies `b` then `a`.

    Treats each as a 4x4 with implicit bottom row [0,0,0,1].
    """
    out = identity()
    for r in range(3):
        for c in range(4):
            s = a[r][0] * b[0][c] + a[r][1] * b[1][c] + a[r][2] * b[2][c]
            if c == 3:
                s += a[r][3]  # + translation column of `a`
            out[r][c] = s
    return out


def apply_to_point(m: list[list[float]], p) -> tuple[float, float, float]:
    x, y, z = p[0], p[1], p[2]
    return (
        m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3],
        m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3],
        m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3],
    )


def transformed_z(m: list[list[float]], p) -> float:
    """World Z of point p after transform m (cheap; used by ensure_on_bed)."""
    return m[2][0] * p[0] + m[2][1] * p[1] + m[2][2] * p[2] + m[2][3]


# --- lib3mf bridging (thin; the ctypes shape lives here, nowhere else) ------ #

def to_lib3mf(wrapper, m: list[list[float]]):
    """3x4 row-major list -> lib3mf Transform ([4][3] column-major)."""
    t = wrapper.GetIdentityTransform()
    F = t.Fields
    for col in range(4):
        for row in range(3):
            F[col][row] = float(m[row][col])
    t.Fields = F
    return t


def from_lib3mf(t) -> list[list[float]]:
    """lib3mf Transform -> 3x4 row-major list."""
    F = t.Fields
    return [[float(F[col][row]) for col in range(4)] for row in range(3)]
