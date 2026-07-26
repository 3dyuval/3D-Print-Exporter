# SPDX-License-Identifier: MIT
"""The 3D Tools For Print workbench.

A real Gui.Workbench so command placement is sanctioned by FreeCAD:
appendMenu/appendToolbar call Command::addTo -> initAction -> setShortcut, which
is the ONLY path that binds a command's Accelerator (see src/Gui/Command.cpp).
That makes Ctrl+Alt+P work reliably and puts the commands in a menu/toolbar that
survive workbench switches — which the manual menu-bar approach did not.
"""

from __future__ import annotations

import os

import FreeCADGui as Gui

from .. import ICON_DIR

WB_NAME = "3D Tools For Print"
_SHORTCUT = "Ctrl+Alt+P"


def _install_global_shortcut():
    """Bind Ctrl+Alt+P to the main window (ApplicationShortcut) so it fires in
    any workbench. QShortcut/QAction/QKeySequence live in QtGui in FreeCAD's
    PySide shim (verified earlier)."""
    from PySide import QtCore
    from PySide.QtGui import QKeySequence, QShortcut

    mw = Gui.getMainWindow()
    if mw is None:
        return
    if mw.findChild(QShortcut, "ToolsForPrintShortcut"):
        return
    sc = QShortcut(QKeySequence(_SHORTCUT), mw)
    sc.setObjectName("ToolsForPrintShortcut")
    sc.setContext(QtCore.Qt.ApplicationShortcut)
    sc.activated.connect(lambda: Gui.runCommand("ToolsForPrint", 0))


class ToolsForPrintWorkbench(Gui.Workbench):
    MenuText = "3D Tools For Print"
    ToolTip = "Export the selection to 3MF with hooks, slicer hand-off and parametric 3D print hooks"
    Icon = os.path.join(ICON_DIR, "tools_for_print.svg")

    def Initialize(self):
        # Register commands (idempotent) and the datum restore observer.
        from . import commands, datum_commands

        commands.register()
        datum_commands.register()

        export_cmd = "ToolsForPrint"
        datum_cmd = "ToolsForPrint_NewDatumHook"

        # appendMenu/appendToolbar is what binds the Accelerator (Ctrl+Alt+P)
        # while this workbench's menu is loaded.
        self.appendToolbar(WB_NAME, [export_cmd, datum_cmd])
        self.appendMenu(WB_NAME, [export_cmd, datum_cmd])

        # Belt-and-suspenders: a global QShortcut on the main window so the
        # hotkey also fires from OTHER workbenches (ApplicationShortcut context),
        # independent of which workbench menu is currently loaded.
        _install_global_shortcut()

    def Activated(self):
        # Reattach proxies on any already-open documents when the WB is entered.
        from . import datum_commands
        try:
            import FreeCAD
            for doc in FreeCAD.listDocuments().values():
                for obj in doc.Objects:
                    datum_commands._reattach(obj)
        except Exception:
            pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"
