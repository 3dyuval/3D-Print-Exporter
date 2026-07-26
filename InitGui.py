# SPDX-License-Identifier: MIT
"""FreeCAD entry point. Registers the single '3D Print Export' command."""

from freecad.print_exporter.gui import init_gui  # noqa: F401  (side effects)
