# SPDX-License-Identifier: MIT
"""Command to create a DatumHook, plus document-restore reattachment.

Restore is critical: FeaturePython proxies are Python objects that do NOT
survive save/load. On document open, obj.Proxy / obj.ViewObject.Proxy are gone,
so double-click and execute() would break. A DocumentObserver reattaches them
(and re-syncs requirement properties, since the macro's REQUIREMENTS may have
changed since the object was saved).
"""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui as Gui

from .. import ICON_DIR
from ..param import datumhook, macros as macromod
from . import paths


class CreateDatumHookCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICON_DIR, "tools_for_print.svg"),
            "MenuText": "New 3D Print Hook",
            "ToolTip": "Create a parametric 3D print hook object in the document "
                       "(double-click it to choose a macro and fulfil its inputs).",
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        doc = FreeCAD.ActiveDocument
        doc.openTransaction("Create 3D Print Hook")
        obj = datumhook.create(doc)
        doc.commitTransaction()
        doc.recompute()
        # open the edit panel immediately
        from .datum_panel import DatumHookPanel
        DatumHookPanel(obj, parent=Gui.getMainWindow()).show()


def _reattach(obj):
    """Rebind proxies + re-sync requirement props for a restored DatumHook."""
    if getattr(obj, "TypeId", "") != "App::GeometryPython":
        return
    if not hasattr(obj, datumhook.MARKER_PROP):
        return
    if not isinstance(getattr(obj, "Proxy", None), datumhook.DatumHookProxy):
        obj.Proxy = datumhook.DatumHookProxy()
    vo = getattr(obj, "ViewObject", None)
    if vo is not None and not isinstance(getattr(vo, "Proxy", None),
                                         datumhook.DatumHookViewProxy):
        vo.Proxy = datumhook.DatumHookViewProxy()
    # re-sync in case the macro's REQUIREMENTS changed since save
    name = getattr(obj, datumhook.MACRO_PROP, "")
    if name:
        macro = macromod.find_by_name(paths.param_hook_dirs(), name)
        if macro is not None:
            from ..param import requirements as reqmod
            reqmod.sync_properties(obj, macro.requirements)
    # Detect macro-file edits made while the document was closed: refreshing the
    # hash auto-touches the object if the file changed, so the next recompute
    # re-runs execute() with the new compute() logic.
    datumhook._refresh_macro_hash(obj)


class _RestoreObserver:
    """Reattach proxies whenever a document finishes restoring."""

    def slotFinishRestoreDocument(self, doc):
        try:
            for obj in doc.Objects:
                _reattach(obj)
        except Exception as exc:
            FreeCAD.Console.PrintError(f"[DatumHook] restore reattach failed: {exc}\n")


_observer = None


def register():
    global _observer
    Gui.addCommand("ToolsForPrint_NewDatumHook", CreateDatumHookCommand())
    if _observer is None:
        _observer = _RestoreObserver()
        FreeCAD.addDocumentObserver(_observer)
    # reattach any hooks already present in already-open documents
    for doc in FreeCAD.listDocuments().values():
        for obj in doc.Objects:
            _reattach(obj)
