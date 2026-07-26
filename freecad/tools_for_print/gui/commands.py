# SPDX-License-Identifier: MIT
"""The single '3D Tools For Print' command registered on the global toolbar."""

from __future__ import annotations

import os

import FreeCAD
import FreeCADGui as Gui

from .. import ICON_DIR


class ToolsForPrintCommand:
    def GetResources(self):
        return {
            "Pixmap": os.path.join(ICON_DIR, "tools_for_print.svg"),
            "MenuText": "3D Tools For Print",
            "Accelerator": "Ctrl+Alt+P",
            "ToolTip": (
                "Export selection to 3MF, then apply build-plate transforms via "
                "Python hooks (align a selected face to the plate, drop on bed, ...)."
            ),
        }

    def IsActive(self):
        return FreeCAD.ActiveDocument is not None

    def Activated(self):
        # Imported lazily so a lib3mf/Qt import error surfaces as a dialog, not
        # a load-time failure that hides the whole command.
        from .dialog import open_dialog

        open_dialog()


def register():
    Gui.addCommand("ToolsForPrint", ToolsForPrintCommand())
