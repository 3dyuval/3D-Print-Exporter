# SPDX-License-Identifier: MIT
import os

ADDON_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
ICON_DIR = os.path.join(ADDON_ROOT, "Resources", "icons")
BUILTIN_HOOKS_DIR = os.path.join(ADDON_ROOT, "hooks")
