"""Stub FreeCAD/FreeCADGui so gui/* is importable without a FreeCAD install.

Core tests don't need these, but importing shared modules might pull them in.
"""

import sys
import types

for _name in ("FreeCAD", "FreeCADGui"):
    sys.modules.setdefault(_name, types.ModuleType(_name))
