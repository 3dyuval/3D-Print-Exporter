# SPDX-License-Identifier: MIT
"""Requirement protocol for parametric (DatumHook) macros.

A parametric macro is a .py file that declares a top-level REQUIREMENTS list and
a compute(inputs) -> transform function. Each requirement maps onto a NATIVE
FreeCAD property (see _TYPE_MAP), so it inherits undo/redo, touch-tracking and
dependency-graph invalidation for free.

Two-phase contract (critical — execute() runs inside doc.recompute()):
  Phase A (interactive, panel): resolve requirements -> write property values.
  Phase B (deterministic, execute): read resolved properties -> compute(). No UI.

A requirement dict:
  {"id": "PlateFace", "type": "selection", "label": "Face to lay on the plate",
   "options": [...]  # only for type == "choice"
   "default": ...}   # optional
"""

from __future__ import annotations

import ast

# requirement type -> FreeCAD property type
_TYPE_MAP = {
    "selection": "App::PropertyLinkSub",   # (obj, [subelement])
    "object":    "App::PropertyLink",       # whole-object link
    "choice":    "App::PropertyEnumeration",
    "quantity":  "App::PropertyLength",
    "value":     "App::PropertyFloat",
    "bool":      "App::PropertyBool",
}

_INPUT_GROUP = "Inputs"


def read_requirements(path: str) -> list[dict]:
    """Extract the REQUIREMENTS list from a macro WITHOUT executing it (ast).

    Reading requirements must never run macro code (same safety rule as reading
    a hook docstring). Only literal REQUIREMENTS are supported.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
    except Exception:
        return []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "REQUIREMENTS":
                    try:
                        return list(ast.literal_eval(node.value))
                    except Exception:
                        return []
    return []


def property_type_for(req: dict) -> str:
    return _TYPE_MAP[req["type"]]


def sync_properties(obj, requirements: list[dict]) -> None:
    """Make obj's Input-group properties exactly match `requirements`.

    Adds missing ones, removes stale ones (declared set wins — deterministic).
    Safe to call on create, on re-edit, and on document restore (macro's
    REQUIREMENTS may have changed since the object was saved).
    """
    declared = {r["id"]: r for r in requirements}

    # remove orphans: props in our Input group no longer declared
    for prop in list(obj.PropertiesList):
        try:
            grp = obj.getGroupOfProperty(prop)
        except Exception:
            grp = ""
        if grp == _INPUT_GROUP and prop not in declared:
            obj.removeProperty(prop)

    # add / configure declared props
    for req in requirements:
        pid = req["id"]
        ptype = property_type_for(req)
        if pid not in obj.PropertiesList:
            obj.addProperty(ptype, pid, _INPUT_GROUP, req.get("label", ""))
            # PropertyEnumeration: assigning a LIST sets the available choices;
            # assigning a STRING sets the current value. Set choices first.
            if req["type"] == "choice":
                setattr(obj, pid, list(req.get("options", [])))
            if "default" in req and req["type"] != "choice":
                try:
                    setattr(obj, pid, req["default"])
                except Exception:
                    pass


def missing_requirements(obj, requirements: list[dict]) -> list[str]:
    """Ids of requirements not yet fulfilled (empty link / unset). For UI hints.

    Deterministic and UI-free so execute() can call it to decide whether to skip.
    """
    out = []
    for req in requirements:
        pid = req["id"]
        if pid not in obj.PropertiesList:
            out.append(pid)
            continue
        val = getattr(obj, pid, None)
        if req["type"] in ("selection", "object"):
            # PropertyLink -> obj or None; PropertyLinkSub -> (obj, [subs]) or None
            linked = val[0] if isinstance(val, tuple) else val
            if not linked:
                out.append(pid)
    return out
