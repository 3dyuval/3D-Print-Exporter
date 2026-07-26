"""Rotate every build item 45 degrees about Z (a simple example hook).

Copy this into your user hooks folder and tweak the angle, or use it as a
template for your own transforms.
"""


def hook(ctx):
    t = ctx.rotate_z(45.0)
    ctx.apply_build_transform(t)
    ctx.log("Rotated build items 45 degrees about Z.")
