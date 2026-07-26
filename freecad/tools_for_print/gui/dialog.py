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


class HookEditor(QtGui.QDialog):
    """View/edit a hook's source. Builtin hooks are saved as a user-folder copy
    (so addon updates don't clobber edits); user hooks are saved in place."""

    def __init__(self, hook, parent=None):
        super().__init__(parent or Gui.getMainWindow())
        self._hook = hook
        self.setWindowTitle(f"Hook: {hook.name}  [{hook.source}]")
        self.resize(640, 480)

        lay = QtGui.QVBoxLayout(self)
        self.info = QtGui.QLabel()
        self.info.setWordWrap(True)
        lay.addWidget(self.info)

        self.editor = QtGui.QPlainTextEdit()
        mono = QtGui.QFont("monospace")
        mono.setStyleHint(QtGui.QFont.TypeWriter)
        self.editor.setFont(mono)
        try:
            with open(hook.path, "r", encoding="utf-8") as fh:
                self.editor.setPlainText(fh.read())
        except Exception as exc:
            self.editor.setPlainText(f"# could not read {hook.path}:\n# {exc}")
        lay.addWidget(self.editor, 1)

        if hook.source == "builtin":
            self.info.setText(
                "Builtin hook. Saving writes a copy to your user hooks folder "
                "(which shadows the builtin), so it survives addon updates."
            )
        else:
            self.info.setText(f"Editing user hook in place:\n{hook.path}")

        btns = QtGui.QHBoxLayout()
        btns.addStretch(1)
        save = QtGui.QPushButton("Save")
        save.setDefault(True)
        save.clicked.connect(self._save)
        close = QtGui.QPushButton("Close")
        close.clicked.connect(self.reject)
        btns.addWidget(save)
        btns.addWidget(close)
        lay.addLayout(btns)

    def _save(self):
        text = self.editor.toPlainText()
        if self._hook.source == "builtin":
            dest = os.path.join(paths.user_hooks_dir(), f"{self._hook.name}.py")
        else:
            dest = self._hook.path
        try:
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write(text)
        except Exception as exc:
            QtGui.QMessageBox.critical(self, "Save failed", str(exc))
            return
        QtGui.QMessageBox.information(
            self, "Saved", f"Saved to:\n{dest}\n\nReopen the panel to pick it up."
        )
        self.accept()


class WorkflowDialog(QtGui.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or Gui.getMainWindow())
        self.setWindowTitle("3D Tools For Print")
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

        # pre-export CSG fuse (one watertight solid instead of overlapping items)
        self.fuse_check = QtGui.QCheckBox(
            "Fuse selection into one solid before export (boolean union)"
        )
        self.fuse_check.setToolTip(
            "Runs Part.fuse() on the selected solids before meshing, producing a "
            "single manifold. Spec-clean (3MF producers should not overlap). "
            "Needs 2+ objects that actually touch."
        )
        lay.addWidget(self.fuse_check)

        # hooks list — each row: [x] name [source]            [Edit]
        lay.addWidget(QtGui.QLabel("Hooks (run top-to-bottom, checked only):"))
        self.hook_list = QtGui.QListWidget()
        self.hook_list.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self._hook_rows = []  # list of (hook, checkbox) so we can read state/order
        for h in self._hooks:
            item = QtGui.QListWidgetItem(self.hook_list)
            roww = QtGui.QWidget()
            rl = QtGui.QHBoxLayout(roww)
            rl.setContentsMargins(4, 2, 4, 2)
            chk = QtGui.QCheckBox(f"{h.name}   [{h.source}]")
            tip = h.description or "(no description — add a module docstring)"
            chk.setToolTip(tip)
            roww.setToolTip(tip)
            rl.addWidget(chk, 1)
            # inline summary so the description is visible without hovering
            if h.summary:
                summ = QtGui.QLabel(h.summary)
                summ.setStyleSheet("color: gray;")
                summ.setToolTip(tip)
                rl.addWidget(summ)
            edit = QtGui.QPushButton("Edit")
            edit.setMaximumWidth(56)
            edit.setToolTip(f"View/edit {h.name}.py")
            edit.clicked.connect(lambda _=False, hook=h: self._edit_hook(hook))
            rl.addWidget(edit)
            item.setSizeHint(roww.sizeHint())
            self.hook_list.setItemWidget(item, roww)
            self._hook_rows.append((h, chk))
        lay.addWidget(self.hook_list, 1)

        hook_btns = QtGui.QHBoxLayout()
        open_dir = QtGui.QPushButton("Open user hooks folder")
        open_dir.clicked.connect(self._open_hooks_dir)
        hook_btns.addWidget(open_dir)
        hook_btns.addStretch(1)
        lay.addLayout(hook_btns)

        # DatumHook objects in the document (parametric hooks) — apply their
        # computed Placement on export. Current hooks above are untouched.
        self._datum_rows = []
        datum_objs = self._list_datum_hooks()
        if datum_objs:
            lay.addWidget(QtGui.QLabel("3D Print hooks (parametric, from tree):"))
            for o in datum_objs:
                chk = QtGui.QCheckBox(f"{o.Label}")
                chk.setChecked(True)
                chk.setToolTip("Apply this DatumHook's computed placement on export.")
                lay.addWidget(chk)
                self._datum_rows.append((o, chk))

        # slicer hand-off
        from .runner import DEFAULT_SLICER
        srow = QtGui.QHBoxLayout()
        self.slicer_check = QtGui.QCheckBox("Open in slicer:")
        self.slicer_check.setChecked(os.path.exists(DEFAULT_SLICER))
        srow.addWidget(self.slicer_check)
        self.slicer_edit = QtGui.QLineEdit(DEFAULT_SLICER)
        srow.addWidget(self.slicer_edit, 1)
        sbrowse = QtGui.QPushButton("...")
        sbrowse.setMaximumWidth(32)
        sbrowse.clicked.connect(self._browse_slicer)
        srow.addWidget(sbrowse)
        lay.addLayout(srow)

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

    def _browse_slicer(self):
        start = self.slicer_edit.text() or "/usr/bin"
        path, _ = QtGui.QFileDialog.getOpenFileName(self, "Select slicer", start)
        if path:
            self.slicer_edit.setText(path)
            self.slicer_check.setChecked(True)

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
        return [h for (h, chk) in self._hook_rows if chk.isChecked()]

    def _list_datum_hooks(self):
        doc = FreeCAD.ActiveDocument
        if doc is None:
            return []
        from ..param import datumhook
        return datumhook.list_datum_hooks(doc)

    def _datum_transforms(self):
        """3x4 transforms from checked DatumHook objects' Placements."""
        out = []
        for o, chk in getattr(self, "_datum_rows", []):
            if not chk.isChecked():
                continue
            m = o.Placement.toMatrix()
            out.append([
                [m.A11, m.A12, m.A13, m.A14],
                [m.A21, m.A22, m.A23, m.A24],
                [m.A31, m.A32, m.A33, m.A34],
            ])
        return out

    def _edit_hook(self, hook):
        """View/edit a hook's source in an in-app editor.

        Builtin hooks live inside the addon (may be overwritten on update), so
        editing one offers to save a copy into the user hooks folder instead;
        user hooks are edited in place.
        """
        HookEditor(hook, self).exec_()

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
                objs, callables, self.out_edit.text(), log=self._log,
                slicer=self.slicer_edit.text().strip(),
                launch_slicer=self.slicer_check.isChecked(),
                fuse=self.fuse_check.isChecked(),
                datum_transforms=self._datum_transforms(),
            )
            self._log(f"Done → {out_path}")
        except Exception as exc:
            self._log(f"Error: {exc}")
            self._log(traceback.format_exc())


# Module-level reference so a modeless dialog opened from a hotkey/console is
# NOT garbage-collected the instant open_dialog() returns (the classic "script
# ran but no panel appeared" bug). We keep the panel modeless on purpose so the
# 3D view stays interactive — you can select a face while it's open.
_dialog = None


def open_dialog():
    global _dialog

    # lib3mf presence check up front; offer to auto-install if missing.
    from . import bootstrap

    if not bootstrap.is_installed():
        resp = QtGui.QMessageBox.question(
            Gui.getMainWindow(),
            "3D Tools For Print",
            "lib3mf (required for 3MF export) isn't installed in FreeCAD's "
            "Python.\n\nInstall it now? (pip install --user lib3mf)",
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.Yes,
        )
        if resp != QtGui.QMessageBox.Yes:
            return
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            ok = bootstrap.install(log=lambda m: FreeCAD.Console.PrintMessage(f"[3MF] {m}\n"))
        finally:
            QtGui.QApplication.restoreOverrideCursor()
        if not ok:
            QtGui.QMessageBox.critical(
                Gui.getMainWindow(),
                "3D Tools For Print",
                "Automatic install failed. Install manually with FreeCAD's "
                "interpreter:\n    python3 -m pip install --user lib3mf\n"
                "then restart FreeCAD. (See the Report view for details.)",
            )
            return

    # Reuse an already-open panel instead of stacking duplicates on repeat presses.
    if _dialog is not None:
        try:
            _dialog.raise_()
            _dialog.activateWindow()
            _dialog._refresh_selection()
            return
        except RuntimeError:
            _dialog = None  # underlying C++ dialog was destroyed; recreate

    _dialog = WorkflowDialog()
    _dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
    _dialog.finished.connect(_on_closed)
    _dialog.show()
    _dialog.raise_()
    _dialog.activateWindow()


def _on_closed(*_):
    global _dialog
    _dialog = None
