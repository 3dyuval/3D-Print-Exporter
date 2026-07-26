"""Drop every build item onto the print bed (min Z -> 0).

Port of OrcaSlicer's ModelObject::ensure_on_bed(). The logic lives in
ctx.ensure_on_bed(); this hook is the thin wrapper the dialog runs.

Every hook defines `hook(ctx)`. See gui/context.py (HookContext) for the API.
"""


def hook(ctx):
    ctx.ensure_on_bed(allow_negative_z=False)
