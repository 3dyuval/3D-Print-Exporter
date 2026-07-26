# SPDX-License-Identifier: MIT
"""FreeCAD entry point — registers the 3D Print Exporter workbench."""

import FreeCADGui as Gui

from freecad.print_exporter.gui.workbench import PrintExporterWorkbench

Gui.addWorkbench(PrintExporterWorkbench())
