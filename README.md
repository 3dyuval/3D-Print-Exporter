# 3D Print Exporter (FreeCAD)

Export the current selection to **3MF** and apply build-plate operations through
[**lib3mf**](https://github.com/3MFConsortium/lib3mf) — driven by small **Python
hook scripts**. Instead of hand-writing `<vertices>`/`<triangles>` XML and
patching `transform="…"` strings with regex (as the original *3D Printer 3mf
Workflow* macro did), geometry goes through lib3mf's typed API, and hooks get a
rich context to script transforms — e.g. **align a selected face/plane to the
build plate** or **drop the part on the bed**.

## Install

1. This is a standard FreeCAD Mod package. It already lives in your `Mod/` dir.
2. It needs **lib3mf** in FreeCAD's Python. Install it into FreeCAD's
   interpreter:
   ```
   pip install lib3mf
   ```
   (The 2.5.0 `py3-none` wheel works with FreeCAD 1.1's Python 3.14.)
3. Restart FreeCAD. Add the **3D Print Export** command to a toolbar via
   *Tools → Customize → Commands*, or run it from where you place it.

## Use

1. Select one or more objects (and optionally one planar **face** if a hook
   needs it — e.g. *align_face_to_plate*).
2. Run **3D Print Export**.
3. Pick an output path, check the hooks to run (they run top-to-bottom), **Run**.

## Writing hooks

A hook is a `.py` file defining `hook(ctx)`. Put your own in the user hooks
folder (button in the dialog, or FreeCAD user dir `/print_exporter_hooks/`);
a user hook shadows a bundled one of the same name.

```python
def hook(ctx):
    face = ctx.selected_face()               # first selected planar face, or None
    t = ctx.transform_from_face(face)        # rotate that face's normal to -Z
    ctx.apply_build_transform(t)             # compose onto all build items
    ctx.ensure_on_bed()                      # drop min-Z to the plate
    ctx.log("aligned & bedded")
```

### `ctx` API

Guided helpers:

| Call | Does |
|------|------|
| `ctx.selected_face()` | first selected planar `Face`, or `None` |
| `ctx.selected_plane_normal()` | unit normal of that face |
| `ctx.transform_from_face(face=None)` | 3×4 transform laying the face's normal to −Z |
| `ctx.rotate_z(deg)` / `ctx.translate(dx,dy,dz)` / `ctx.identity()` | build transforms |
| `ctx.apply_build_transform(m, item=None)` | **compose** `m` onto item(s) |
| `ctx.set_build_transform(m, item=None)` | **replace** transform on item(s) |
| `ctx.build_items()` | list of lib3mf build items |
| `ctx.ensure_on_bed(allow_negative_z=False)` | drop each item so min-Z = 0 |
| `ctx.log(msg)` | write to the dialog log |

Raw handles (power users):

| Attribute | Is |
|-----------|-----|
| `ctx.model` | `core.model.ThreeMFModel` (build_items / get_transform / …) |
| `ctx.raw_model` | the underlying lib3mf model |
| `ctx.lib3mf`, `ctx.wrapper` | the lib3mf module and `Wrapper()` |
| `ctx.doc`, `ctx.Gui`, `ctx.FreeCAD` | FreeCAD handles |

Transforms are 3×4 row-major nested lists
(`[[r00,r01,r02,tx],[r10,r11,r12,ty],[r20,r21,r22,tz]]`), matching 3MF's XML
order. `core.transform` has `identity/translation/matmul/apply_to_point` plus the
lib3mf `to_lib3mf`/`from_lib3mf` bridges.

## Layout

```
3D-Print-Exporter/
  InitGui.py                      registers the single command
  package.xml  pyproject.toml  LICENSE  README.md
  Resources/icons/print_exporter.svg
  hooks/                          bundled hooks (ensure_on_bed, align_face_to_plate, rotate_z_45)
  freecad/print_exporter/
    core/                         FreeCAD-free, unit-tested
      transform.py  model.py  operations.py  hooks.py
    gui/                          FreeCAD/Qt glue
      commands.py  init_gui.py  dialog.py  runner.py
      context.py  selection.py  mesh_export.py  paths.py
  tests/                          pytest (no FreeCAD needed)
```

Run tests: `pip install pytest lib3mf && pytest` from the package root.
