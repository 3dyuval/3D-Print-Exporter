# SPDX-License-Identifier: MIT
"""Register the command, add a menu entry, and bind Ctrl+Shift+P — no workbench.

Source rationale (FreeCAD src/Gui/Command.cpp:288-306, Workbench.cpp:1176):
  * A command's Accelerator is only bound inside Command::initAction(), which is
    called ONLY from Command::addTo()/addToGroup() — i.e. when the command is
    placed into a widget. The single Python API that triggers that path is
    Workbench.appendMenu(), which requires a workbench.
  * We deliberately avoid a workbench. So the command's built-in Accelerator
    won't self-bind; instead we bind Ctrl+Shift+P ourselves with a QShortcut on
    the main window (ApplicationShortcut context -> fires regardless of focus or
    active workbench), and add a visible menu entry that runs the same command.

Qt note: FreeCAD 1.1 uses PySide6 / Qt6, where QShortcut and QAction live in
QtWidgets (they were in QtGui under Qt5). We import from QtWidgets with a QtGui
fallback so this keeps working across bindings.
"""

from __future__ import annotations

import FreeCADGui as Gui
from PySide import QtCore

# NOTE: this FreeCAD's PySide shim exposes QShortcut/QAction/QKeySequence from
# QtGui (verified at runtime via the FreeCAD MCP), NOT QtWidgets as canonical
# Qt6 would. Import from QtGui first; fall back to QtWidgets for other builds.
try:
    from PySide.QtGui import QAction, QKeySequence, QMenu, QShortcut
except Exception:  # pragma: no cover - other PySide layouts
    from PySide.QtWidgets import QAction, QMenu, QShortcut
    from PySide.QtGui import QKeySequence

from . import commands

_MENU_TITLE = "3D Print"
_COMMAND = "PrintExporter"
_SHORTCUT = "Ctrl+Alt+P"


def _run():
    Gui.runCommand(_COMMAND, 0)


def _add_menu(attempts: int = 40):
    """Add a persistent top-level menu holding the command (visible entry)."""
    mw = Gui.getMainWindow()
    if mw is None:
        if attempts > 0:
            QtCore.QTimer.singleShot(250, lambda: _add_menu(attempts - 1))
        return

    menubar = mw.menuBar()
    for act in menubar.actions():
        if act.menu() and act.menu().objectName() == "PrintExporterMenu":
            return  # already added (InitGui may be re-imported)

    menu = menubar.addMenu(_MENU_TITLE)
    menu.setObjectName("PrintExporterMenu")

    action = QAction(f"3D Print Export\t{_SHORTCUT}", mw)
    action.setObjectName("PrintExporterAction")
    action.triggered.connect(_run)
    menu.addAction(action)


def _add_shortcut(attempts: int = 40):
    """Bind Ctrl+Shift+P globally via a QShortcut on the main window.

    ApplicationShortcut context means it fires no matter which dock/view has
    focus or which workbench is active — the always-works global hotkey, with
    no workbench defined.
    """
    mw = Gui.getMainWindow()
    if mw is None:
        if attempts > 0:
            QtCore.QTimer.singleShot(250, lambda: _add_shortcut(attempts - 1))
        return
    if mw.findChild(QShortcut, "PrintExporterShortcut"):
        return
    sc = QShortcut(QKeySequence(_SHORTCUT), mw)
    sc.setObjectName("PrintExporterShortcut")
    sc.setContext(QtCore.Qt.ApplicationShortcut)
    sc.activated.connect(_run)


def _clear_saved_shortcut_override():
    """Drop any persisted ShortcutManager override for our command.

    FreeCAD saves accelerators to User prefs; a stale value (e.g. an earlier
    Ctrl+Shift+P) would otherwise shadow the _SHORTCUT we bind here. Clearing it
    makes the source-defined key authoritative on every load.
    """
    try:
        import FreeCAD
        grp = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Shortcut")
        if grp.GetString(_COMMAND, ""):
            grp.RemString(_COMMAND)
    except Exception:
        pass


def _install():
    _clear_saved_shortcut_override()
    commands.register()
    QtCore.QTimer.singleShot(0, _add_menu)
    QtCore.QTimer.singleShot(0, _add_shortcut)


# Registration happens at import time (InitGui.py imports this module).
_install()
