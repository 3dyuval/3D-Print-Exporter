"""DatumHook tree-label naming: Title Case from the macro, unique suffixing, and
respecting manual renames. Pure logic (FreeCAD stubbed)."""

import sys
import types

sys.modules.setdefault("FreeCAD", types.ModuleType("FreeCAD"))
sys.modules.setdefault("FreeCADGui", types.ModuleType("FreeCADGui"))

from freecad.tools_for_print.param import datumhook as dh  # noqa: E402


def test_display_name_title_case():
    assert dh._display_name("align_to_datum") == "Align To Datum"
    assert dh._display_name("mirror-x") == "Mirror X"
    assert dh._display_name("ensure_on_bed") == "Ensure On Bed"


class _Doc:
    def __init__(self, labels):
        self.Objects = [types.SimpleNamespace(Label=l) for l in labels]


def test_unique_label_suffixes_duplicates():
    doc = _Doc(["Align To Datum"])
    assert dh._unique_label(doc, "Align To Datum") == "Align To Datum (2)"
    doc = _Doc(["Align To Datum", "Align To Datum (2)"])
    assert dh._unique_label(doc, "Align To Datum") == "Align To Datum (3)"
    assert dh._unique_label(_Doc([]), "Base") == "Base"


class _FakeObj:
    """Minimal object for _auto_label: Label, Document, props."""

    def __init__(self, doc, label="Datum Hook"):
        self.Label = label
        self.Document = doc
        self._props = {dh.AUTO_LABEL_PROP: label}

    @property
    def PropertiesList(self):
        return list(self._props.keys())

    def __getattr__(self, n):
        p = self.__dict__.get("_props", {})
        if n in p:
            return p[n]
        raise AttributeError(n)

    def __setattr__(self, n, v):
        if n in ("Label", "Document", "_props"):
            super().__setattr__(n, v)
        elif n in self.__dict__.get("_props", {}):
            self._props[n] = v
        else:
            super().__setattr__(n, v)


def _macro(name):
    return types.SimpleNamespace(name=name)


def test_auto_label_follows_macro_until_renamed():
    doc = _Doc([])
    obj = _FakeObj(doc, label="Datum Hook")
    dh._auto_label(obj, _macro("align_to_datum"))
    assert obj.Label == "Align To Datum"           # auto-followed

    dh._auto_label(obj, _macro("rotate_z_45"))
    assert obj.Label == "Rotate Z 45"              # still following (unedited)

    # user renames in the tree
    obj.Label = "Base Plate"
    dh._auto_label(obj, _macro("mirror_x"))
    assert obj.Label == "Base Plate"               # rename respected
