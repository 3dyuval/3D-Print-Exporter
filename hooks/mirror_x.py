"""Mirror every build item across the YZ plane (negate X), then drop to bed.

Useful for producing the opposite-hand version of a part. Mirroring flips
triangle winding, but per the 3MF spec consumers fill 'model' volumes with a
positive fill rule, so slicers (OrcaSlicer) handle it correctly. Edit the axis
below to mirror in Y or Z instead.
"""


def hook(ctx):
    ctx.apply_build_transform(ctx.mirror("x"))
    ctx.ensure_on_bed()
    ctx.log("Mirrored across X and dropped to bed.")
