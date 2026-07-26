"""The macro-file hash underpins staleness detection: FreeCAD's dependency graph
can't see the .py contents change, so we hash the file into a property. These
tests cover the pure hashing (no FreeCAD needed)."""

import sys
import types

# datumhook imports FreeCAD-ish modules at module load via `from .. import ICON_DIR`
# (pure) but also `from . import macros` (pure) — stub FreeCAD just in case.
sys.modules.setdefault("FreeCAD", types.ModuleType("FreeCAD"))
sys.modules.setdefault("FreeCADGui", types.ModuleType("FreeCADGui"))

from freecad.tools_for_print.param import datumhook  # noqa: E402


def test_hash_stable_and_content_sensitive(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("def compute(inputs):\n    return 1\n")
    h1 = datumhook._macro_file_hash(str(f))
    assert h1 and datumhook._macro_file_hash(str(f)) == h1  # stable

    f.write_text("def compute(inputs):\n    return 2\n")   # edit contents
    assert datumhook._macro_file_hash(str(f)) != h1        # detected


def test_hash_missing_file_is_empty():
    assert datumhook._macro_file_hash("/no/such/file.py") == ""
