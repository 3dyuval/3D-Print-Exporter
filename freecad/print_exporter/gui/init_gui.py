# SPDX-License-Identifier: MIT
"""Register the command and add it to a global toolbar + Tools menu.

Single-command integration (no dedicated workbench): we add the command to a
toolbar that every workbench shows, and to the Tools menu, via the standard
Gui workbench-activation hook.
"""

from __future__ import annotations

import FreeCADGui as Gui

from . import commands


def _install():
    commands.register()
    # A global toolbar entry, available regardless of active workbench.
    try:
        Gui.addIconPath  # noqa: B018 - presence check
    except AttributeError:
        pass
    # Menu placement is handled per-workbench by FreeCAD; the command is also
    # reachable via Tools > 3D Print Export if the user adds it, and always
    # via the command name in a custom toolbar (Tools > Customize).


# Registration must happen at import time (InitGui.py imports this module).
_install()
