# SPDX-License-Identifier: MIT
"""DatumHook: a parametric, tree-resident hook backed by an App::GeometryPython.

Phase A (interactive, panel): pick the macro + fulfill its requirements; results
    are written as native properties (via requirements.sync_properties).
Phase B (deterministic, execute): read resolved properties -> macro.compute() ->
    store the transform as obj.Placement. Runs inside doc.recompute(): NO UI,
    deterministic given only property values (undo/redo/restore/headless safe).

We use App::GeometryPython (= FeaturePythonT<GeoFeature> in FreeCAD's source):
it carries a Placement natively (from GeoFeature) AND accepts a Python Proxy
(unlike plain App::GeometryPython, which rejects obj.Proxy). The export panel reads
obj.Placement to compose the datum transform into the build.
"""

from __future__ import annotations

import hashlib
import os

from .. import ICON_DIR
from . import macros as macromod
from . import requirements as reqmod

MARKER_PROP = "IsToolsForPrintDatumHook"
MACRO_PROP = "MacroName"
MACRO_HASH_PROP = "MacroHash"   # hidden: content hash of the macro file on disk
AUTO_LABEL_PROP = "AutoLabel"   # hidden: last label we auto-set (rename detection)
BASE_NAME = "DatumHook"
DEFAULT_LABEL = "3D Print Hook"


def _display_name(macro_name: str) -> str:
    """'align_to_datum' -> 'Align To Datum' (Title Case, underscores -> spaces)."""
    return " ".join(w.capitalize() for w in macro_name.replace("-", "_").split("_"))


def _unique_label(doc, base: str) -> str:
    """Suffix duplicates so two hooks of the same macro don't look identical."""
    existing = {o.Label for o in doc.Objects} if doc else set()
    if base not in existing:
        return base
    n = 2
    while f"{base} ({n})" in existing:
        n += 1
    return f"{base} ({n})"


def _macro_file_hash(path) -> str:
    """SHA1 of the macro file's contents, or '' if unreadable.

    The dependency graph can't see the .py file change; storing this hash as a
    property means editing the macro (and refreshing the hash) auto-touches the
    object, so execute() re-runs. See _refresh_macro_hash().
    """
    try:
        with open(path, "rb") as fh:
            return hashlib.sha1(fh.read()).hexdigest()
    except Exception:
        return ""


def _param_dirs():
    # Defer to gui.paths so builtin + user param folders resolve the same way.
    from ..gui import paths
    return paths.param_hook_dirs()


class DatumHookProxy:
    """Data proxy: holds MacroName + synced Input props; execute -> Placement."""

    def execute(self, obj):
        # Phase B — deterministic, UI-free.
        name = getattr(obj, MACRO_PROP, "")
        if not name:
            return
        macro = macromod.find_by_name(_param_dirs(), name)
        if macro is None:
            return
        # Skip silently if requirements aren't fulfilled yet (no prompting!).
        if reqmod.missing_requirements(obj, macro.requirements):
            return
        try:
            compute = macro.load_compute()
            inputs = macromod.resolve_inputs(obj, macro.requirements)
            transform = compute(inputs)  # 3x4 list (core.transform convention)
        except Exception as exc:
            import FreeCAD
            FreeCAD.Console.PrintError(f"[DatumHook] {obj.Label}: {exc}\n")
            return
        _apply_transform(obj, transform)

    # Persist nothing custom; Proxy is re-instantiated on restore.
    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def dumps(self):
        return None

    def loads(self, state):
        return None


def _apply_transform(obj, transform):
    """3x4 core transform -> obj.Placement."""
    import FreeCAD
    from ..core import transform as tf  # noqa: F401  (kept for symmetry)

    m = FreeCAD.Matrix()
    r = transform
    m.A11, m.A12, m.A13, m.A14 = r[0][0], r[0][1], r[0][2], r[0][3]
    m.A21, m.A22, m.A23, m.A24 = r[1][0], r[1][1], r[1][2], r[1][3]
    m.A31, m.A32, m.A33, m.A34 = r[2][0], r[2][1], r[2][2], r[2][3]
    obj.Placement = FreeCAD.Placement(m)


class DatumHookViewProxy:
    """Tree behaviour: double-click to edit, context menu to edit/run."""

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def getIcon(self):
        return os.path.join(ICON_DIR, "tools_for_print.svg")

    def doubleClicked(self, vobj):
        _edit(vobj.Object)
        return True

    def setupContextMenu(self, vobj, menu):
        a = menu.addAction("Edit 3D print hook...")
        a.triggered.connect(lambda: _edit(vobj.Object))

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def dumps(self):
        return None

    def loads(self, state):
        return None


def _edit(obj):
    from ..gui.datum_panel import DatumHookPanel
    import FreeCADGui as Gui
    DatumHookPanel(obj, parent=Gui.getMainWindow()).show()


# --- lifecycle ------------------------------------------------------------- #

def is_datum_hook(obj):
    return (
        obj is not None
        and getattr(obj, "TypeId", "") == "App::GeometryPython"
        and hasattr(obj, MARKER_PROP)
        and hasattr(obj, MACRO_PROP)
    )


def list_datum_hooks(doc):
    return [o for o in doc.Objects if is_datum_hook(o)]


def create(doc, label=None):
    obj = doc.addObject("App::GeometryPython", BASE_NAME)
    obj.Proxy = DatumHookProxy()
    obj.addProperty("App::PropertyString", MACRO_PROP, "DatumHook",
                    "Parametric macro this hook runs")
    obj.addProperty("App::PropertyBool", MARKER_PROP, "DatumHook",
                    "Internal marker; do not edit", read_only=True, hidden=True)
    setattr(obj, MARKER_PROP, True)
    obj.addProperty("App::PropertyString", MACRO_HASH_PROP, "DatumHook",
                    "Content hash of the macro file (staleness tracking)",
                    read_only=True, hidden=True)
    obj.addProperty("App::PropertyString", AUTO_LABEL_PROP, "DatumHook",
                    "Last auto-assigned label (to detect manual renames)",
                    read_only=True, hidden=True)
    obj.Label = label or DEFAULT_LABEL
    setattr(obj, AUTO_LABEL_PROP, obj.Label)
    if obj.ViewObject is not None:
        obj.ViewObject.Proxy = DatumHookViewProxy()
    return obj


def _refresh_macro_hash(obj):
    """Update MacroHash to the current macro file's hash.

    Assigning a changed value auto-touches the object (property change), so a
    subsequent recompute re-runs execute(). No-op if unchanged (avoids spurious
    touches / recompute loops).
    """
    name = getattr(obj, MACRO_PROP, "")
    if not name or MACRO_HASH_PROP not in obj.PropertiesList:
        return
    macro = macromod.find_by_name(_param_dirs(), name)
    new_hash = _macro_file_hash(macro.path) if macro else ""
    if getattr(obj, MACRO_HASH_PROP, "") != new_hash:
        setattr(obj, MACRO_HASH_PROP, new_hash)


def _auto_label(obj, macro):
    """Set the tree Label from the macro (Title Case), UNTIL manually renamed.

    We consider the label 'unedited' if it still equals whatever we last set
    (tracked in AUTO_LABEL_PROP) or the default. Once the user renames it in the
    tree, current label != AUTO_LABEL_PROP, and we leave it alone.
    """
    if AUTO_LABEL_PROP not in obj.PropertiesList:
        return
    last_auto = getattr(obj, AUTO_LABEL_PROP, "")
    if obj.Label not in (last_auto, DEFAULT_LABEL, ""):
        return  # user renamed it — respect that
    new_label = _unique_label(obj.Document, _display_name(macro.name))
    obj.Label = new_label
    setattr(obj, AUTO_LABEL_PROP, new_label)


def set_macro(obj, macro):
    """Assign a macro to the object and sync its requirement properties."""
    setattr(obj, MACRO_PROP, macro.name)
    reqmod.sync_properties(obj, macro.requirements)
    _refresh_macro_hash(obj)
    _auto_label(obj, macro)
