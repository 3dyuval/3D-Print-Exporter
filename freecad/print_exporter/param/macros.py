# SPDX-License-Identifier: MIT
"""Discovery, loading and input-resolution for parametric (DatumHook) macros.

A parametric macro lives in the param_hooks/ folder and declares:
    REQUIREMENTS = [ {...}, ... ]      # see requirements.py
    def compute(inputs) -> transform   # 3x4 list (core.transform convention)

Loading a macro imports it (unlike reading REQUIREMENTS, which is ast-only).
resolve_inputs() turns the object's resolved properties into the concrete
values compute() expects — this is Phase B, so it must be deterministic and
UI-free (no selection, no prompting).
"""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass

from . import requirements as reqmod


@dataclass
class ParamMacro:
    name: str
    path: str
    description: str = ""
    requirements: list = None

    def __post_init__(self):
        if self.requirements is None:
            self.requirements = reqmod.read_requirements(self.path)

    @property
    def summary(self) -> str:
        for line in self.description.splitlines():
            if line.strip():
                return line.strip()
        return ""

    def load_compute(self):
        spec = importlib.util.spec_from_file_location(
            f"printexp_param_{self.name}", self.path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        fn = getattr(module, "compute", None)
        if not callable(fn):
            raise AttributeError(f"Param macro '{self.name}' has no compute(inputs).")
        return fn


def _read_docstring(path: str) -> str:
    import ast
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return (ast.get_docstring(ast.parse(fh.read())) or "").strip()
    except Exception:
        return ""


def discover(dirs: list[tuple[str, str]]) -> list[ParamMacro]:
    found: dict[str, ParamMacro] = {}
    for d, _source in dirs:
        if not d or not os.path.isdir(d):
            continue
        for entry in sorted(os.listdir(d)):
            if not entry.endswith(".py") or entry.startswith("_"):
                continue
            name = entry[:-3]
            full = os.path.join(d, entry)
            found[name] = ParamMacro(
                name=name, path=full, description=_read_docstring(full)
            )
    return sorted(found.values(), key=lambda m: m.name)


def find_by_name(dirs, name) -> "ParamMacro | None":
    for m in discover(dirs):
        if m.name == name:
            return m
    return None


# --- Phase B input resolution (deterministic, UI-free) --------------------- #

def resolve_inputs(obj, requirements: list[dict]) -> dict:
    """Turn resolved object properties into concrete values for compute().

    selection -> a FreeCAD sub-shape (Face/Edge/...) or None
    object    -> the linked DocumentObject or None
    others    -> the raw property value
    Raises nothing; unresolved links come back as None so compute() can decide.
    """
    out = {}
    for req in requirements:
        pid = req["id"]
        rtype = req["type"]
        val = getattr(obj, pid, None)
        if rtype == "selection":
            out[pid] = _resolve_linksub(val)
        elif rtype == "object":
            out[pid] = val  # DocumentObject or None
        else:
            out[pid] = val
    return out


def _resolve_linksub(linksub):
    """(obj, [subnames]) -> the referenced sub-shape (first sub), or None."""
    if not linksub:
        return None
    linked, subs = linksub
    if linked is None:
        return None
    shape = getattr(linked, "Shape", None)
    if shape is None:
        return None
    if not subs:
        return shape
    sub = subs[0]
    try:
        return shape.getElement(sub)  # e.g. "Face3" -> the Face
    except Exception:
        return None
