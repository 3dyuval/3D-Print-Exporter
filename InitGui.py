# SPDX-License-Identifier: MIT
"""FreeCAD entry point — registers the 3D Tools For Print workbench."""

import FreeCADGui as Gui

from freecad.tools_for_print.gui.workbench import ToolsForPrintWorkbench

Gui.addWorkbench(ToolsForPrintWorkbench())
