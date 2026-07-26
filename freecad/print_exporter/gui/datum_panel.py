# SPDX-License-Identifier: MIT
"""Phase A panel for a DatumHook object: choose macro + fulfill requirements.

This is the ONLY place interactive resolution happens. It writes concrete values
onto the object's native properties, then recomputes (which triggers the
object's deterministic Phase-B execute()). It never runs geometry itself.

For 'selection' requirements it offers pick-in-3D-view: click the button, then
click a face in the view; the (object, [sub]) goes into the PropertyLinkSub.
"""

from __future__ import annotations

import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui

from ..param import datumhook, macros as macromod, requirements as reqmod
from . import paths


class DatumHookPanel(QtGui.QDialog):
    def __init__(self, obj, parent=None):
        super().__init__(parent or Gui.getMainWindow())
        self._obj = obj
        self._macros = macromod.discover(paths.param_hook_dirs())
        self.setWindowTitle(f"Datum Hook: {obj.Label}")
        self.resize(460, 360)
        self._req_widgets = {}  # req id -> (widget, getter)
        self._build()
        self._load_current()

    # -- ui ---------------------------------------------------------------- #
    def _build(self):
        self.lay = QtGui.QVBoxLayout(self)

        row = QtGui.QHBoxLayout()
        row.addWidget(QtGui.QLabel("Macro:"))
        self.macro_combo = QtGui.QComboBox()
        for m in self._macros:
            self.macro_combo.addItem(m.name, m)
            idx = self.macro_combo.count() - 1
            self.macro_combo.setItemData(idx, m.description, QtCore.Qt.ToolTipRole)
        self.macro_combo.currentIndexChanged.connect(self._on_macro_changed)
        row.addWidget(self.macro_combo, 1)
        self.lay.addLayout(row)

        self.desc = QtGui.QLabel()
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet("color: gray;")
        self.lay.addWidget(self.desc)

        self.lay.addWidget(QtGui.QLabel("Requirements:"))
        self.req_area = QtGui.QFormLayout()
        self.lay.addLayout(self.req_area)
        self.lay.addStretch(1)

        btns = QtGui.QHBoxLayout()
        btns.addStretch(1)
        ok = QtGui.QPushButton("OK")
        ok.setDefault(True)
        ok.clicked.connect(self._apply_and_close)
        cancel = QtGui.QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        self.lay.addLayout(btns)

    def _load_current(self):
        cur = getattr(self._obj, datumhook.MACRO_PROP, "")
        if cur:
            for i in range(self.macro_combo.count()):
                if self.macro_combo.itemData(i).name == cur:
                    self.macro_combo.setCurrentIndex(i)
                    break
        self._on_macro_changed()

    def _current_macro(self):
        return self.macro_combo.currentData()

    def _on_macro_changed(self):
        macro = self._current_macro()
        self.desc.setText(macro.description if macro else "")
        # Sync properties on the object so requirement fields map to real props.
        if macro is not None:
            datumhook.set_macro(self._obj, macro)
        self._rebuild_req_fields(macro)

    def _rebuild_req_fields(self, macro):
        # clear
        while self.req_area.count():
            item = self.req_area.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._req_widgets = {}
        if macro is None:
            return
        for req in macro.requirements:
            label = req.get("label", req["id"])
            w, getter = self._make_req_widget(req)
            self.req_area.addRow(label, w)
            self._req_widgets[req["id"]] = (req, getter)

    def _make_req_widget(self, req):
        rtype = req["type"]
        if rtype in ("selection", "object"):
            container = QtGui.QWidget()
            hl = QtGui.QHBoxLayout(container)
            hl.setContentsMargins(0, 0, 0, 0)
            lbl = QtGui.QLineEdit()
            lbl.setReadOnly(True)
            lbl.setText(self._describe_link(getattr(self._obj, req["id"], None)))
            pick = QtGui.QPushButton("Pick")
            pick.setMaximumWidth(56)
            pick.clicked.connect(lambda _=False, r=req, e=lbl: self._pick(r, e))
            hl.addWidget(lbl, 1)
            hl.addWidget(pick)
            return container, (lambda e=lbl: None)  # value already written on pick
        if rtype == "choice":
            cb = QtGui.QComboBox()
            cb.addItems([str(o) for o in req.get("options", [])])
            cur = getattr(self._obj, req["id"], "")
            if cur:
                cb.setCurrentText(str(cur))
            return cb, (lambda w=cb: w.currentText())
        if rtype == "bool":
            chk = QtGui.QCheckBox()
            chk.setChecked(bool(getattr(self._obj, req["id"], False)))
            return chk, (lambda w=chk: w.isChecked())
        # quantity / value -> numeric line edit
        le = QtGui.QLineEdit(str(getattr(self._obj, req["id"], "") or ""))
        return le, (lambda w=le: w.text())

    # -- selection picking (interactive; Phase A only) --------------------- #
    def _describe_link(self, val):
        if not val:
            return ""
        if isinstance(val, tuple):
            obj, subs = val
            return f"{obj.Label}:{','.join(subs)}" if obj else ""
        return getattr(val, "Label", "")

    def _pick(self, req, line_edit):
        sel = Gui.Selection.getSelectionEx()
        if not sel:
            QtGui.QMessageBox.information(
                self, "Pick", "Select a face (or object) in the 3D view, then Pick."
            )
            return
        s = sel[0]
        if req["type"] == "selection":
            subs = list(s.SubElementNames) or []
            setattr(self._obj, req["id"], (s.Object, subs))
        else:  # object
            setattr(self._obj, req["id"], s.Object)
        line_edit.setText(self._describe_link(getattr(self._obj, req["id"], None)))

    # -- commit ------------------------------------------------------------ #
    def _apply_and_close(self):
        macro = self._current_macro()
        if macro is not None:
            datumhook.set_macro(self._obj, macro)  # also refreshes MacroHash
            # write non-link requirement values
            for rid, (req, getter) in self._req_widgets.items():
                if req["type"] in ("selection", "object"):
                    continue  # already written by _pick
                val = getter()
                try:
                    setattr(self._obj, rid, val)
                except Exception:
                    pass
        # The macro FILE contents are invisible to the dependency graph, so a
        # macro edit wouldn't otherwise re-run execute(). set_macro() refreshed
        # the hash (auto-touch on change); touch() forces a recompute anyway so
        # re-editing always yields a fresh Placement.
        self._obj.touch()
        if self._obj.Document is not None:
            self._obj.Document.recompute()
        self.accept()
