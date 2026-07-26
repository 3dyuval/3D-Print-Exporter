# SPDX-License-Identifier: MIT
"""The workflow dialog: pick output, choose hooks, run.

Kept deliberately small — all real work lives in runner.py / core. The dialog:
  * shows the current selection (objects + any selected face),
  * lists discovered hooks (builtin + user) with checkboxes and order,
  * on Run: export -> load -> hooks -> save, streaming a log.
"""

from __future__ import annotations

import os
import traceback

import FreeCAD
import FreeCADGui as Gui
from PySide import QtCore, QtGui

from ..core import hooks as hookmod
from . import mesh_export, paths
from .runner import run_workflow


class WorkflowDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or Gui.getMainWindow())
        self.setWindowTitle("3D Print Export")
        self.resize(560, 560)
        self._hooks = hookmod.discover(paths.hook_dirs())
        self._build_ui()
        self._refresh_selection()

    # -- ui ---------------------------------------------------------------- #
    def _build_ui(self):
        lay = QtGui.QVBoxLayout(self)

        # selection summary
        self.sel_label = QtGui.QLabel()
        self.sel_label.setWordWrap(True)
        lay.addWidget(self.sel_label)

        btn_refresh = QtGui.QPushButton("Refresh selection")
        btn_refresh.clicked.connect(self._refresh_selection)
        lay.addWidget(btn_refresh)

        # output path
        row = QtGui.QHBoxLayout()
        row.addWidget(QtGui.QLabel("Output:"))
        self.out_edit = QtGui.QLineEdit(self._default_out())
        row.addWidget(self.out_edit, 1)
        browse = QtGui.QPushButton("...")
        browse.setMaximumWidth(32)
        browse.clicked.connect(self._browse_out)
        row.addWidget(browse)
        lay.addLayout(row)

        # hooks list
        lay.addWidget(QtGui.QLabel("Hooks (run top-to-bottom, checked only):"))
        self.hook_list = QtGui.QListWidget()
        self.hook_list.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.hook_list.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        for h in self._hooks:
            item = QtGui.QListWidgetItem(f"{h.name}   [{h.source}]")
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Unchecked)
            item.setData(QtCore.Qt.UserRole, h)
            self.hook_list.addItem(item)
        lay.addWidget(self.hook_list, 1)

        hook_btns = QtGui.QHBoxLayout()
        open_dir = QtGui.QPushButton("Open user hooks folder")
        open_dir.clicked.connect(self._open_hooks_dir)
        hook_btns.addWidget(open_dir)
        hook_btns.addStretch(1)
        lay.addLayout(hook_btns)

        # log
        self.log_view = QtGui.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(140)
        lay.addWidget(self.log_view)

        # actions
        btns = QtGui.QHBoxLayout()
        btns.addStretch(1)
        self.run_btn = QtGui.QPushButton("Run")
        self.run_btn.setDefault(True)
        self.run_btn.clicked.connect(self._run)
        close_btn = QtGui.QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        btns.addWidget(self.run_btn)
        btns.addWidget(close_btn)
        lay.addLayout(btns)

    # -- helpers ----------------------------------------------------------- #
    def _log(self, msg):
        self.log_view.appendPlainText(str(msg))
        QtGui.QApplication.processEvents()

    def _default_out(self):
        doc = FreeCAD.ActiveDocument
        base = "export"
        if doc and doc.FileName:
            base = os.path.splitext(os.path.basename(doc.FileName))[0]
            return os.path.join(os.path.dirname(doc.FileName), base + ".3mf")
        return os.path.join(os.path.expanduser("~"), base + ".3mf")

    def _browse_out(self):
        path, _ = QtGui.QFileDialog.getSaveFileName(
            self, "Save 3MF", self.out_edit.text(), "3MF (*.3mf)"
        )
        if path:
            self.out_edit.setText(path)

    def _open_hooks_dir(self):
        d = paths.user_hooks_dir()
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(d))

    def _refresh_selection(self):
        objs = mesh_export.selected_objects()
        from . import selection as sel

        face = sel.selected_face()
        names = ", ".join(o.Label for o in objs) or "(none)"
        face_txt = "yes" if face is not None else "no"
        self.sel_label.setText(
            f"Objects: {names}\nSelected face (for face→plate hooks): {face_txt}"
        )
        self._objs = objs

    def _checked_hooks(self):
        out = []
        for i in range(self.hook_list.count()):
            item = self.hook_list.item(i)
            if item.checkState() == QtCore.Qt.Checked:
                out.append(item.data(QtCore.Qt.UserRole))
        return out

    # -- run --------------------------------------------------------------- #
    def _run(self):
        self.log_view.clear()
        objs = getattr(self, "_objs", None) or mesh_export.selected_objects()
        if not objs:
            self._log("No objects selected — select at least one object.")
            return
        chosen = self._checked_hooks()
        try:
            callables = [h.load_callable() for h in chosen]
        except Exception as exc:  # bad hook file
            self._log(f"Failed to load a hook: {exc}")
            self._log(traceback.format_exc())
            return

        try:
            out_path, _ = run_workflow(
                objs, callables, self.out_edit.text(), log=self._log
            )
            self._log(f"Done → {out_path}")
        except Exception as exc:
            self._log(f"Error: {exc}")
            self._log(traceback.format_exc())


def open_dialog():
    # lib3mf presence check up front, with a friendly message.
    try:
        import lib3mf  # noqa: F401
    except Exception:
        QtGui.QMessageBox.critical(
            Gui.getMainWindow(),
            "3D Print Exporter",
            "lib3mf is not installed in FreeCAD's Python.\n\n"
            "Install it with FreeCAD's interpreter, e.g.:\n"
            "    pip install lib3mf\n\n"
            "then restart FreeCAD.",
        )
        return
    dlg = WorkflowDialog()
    dlg.show()
