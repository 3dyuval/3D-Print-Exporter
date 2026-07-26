from freecad.tools_for_print.param import requirements as req


class FakeObj:
    """Minimal App::FeaturePython double for sync_properties/missing_requirements."""

    def __init__(self):
        self._props = {}       # name -> value
        self._groups = {}      # name -> group

    @property
    def PropertiesList(self):
        return list(self._props.keys())

    def getGroupOfProperty(self, name):
        return self._groups.get(name, "")

    def addProperty(self, ptype, name, group="", doc="", **kw):
        self._props[name] = None
        self._groups[name] = group
        return self

    def removeProperty(self, name):
        self._props.pop(name, None)
        self._groups.pop(name, None)

    def __getattr__(self, name):
        # property access
        props = self.__dict__.get("_props", {})
        if name in props:
            return props[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in ("_props", "_groups"):
            super().__setattr__(name, value)
        elif name in self.__dict__.get("_props", {}):
            self._props[name] = value
        else:
            super().__setattr__(name, value)


def test_sync_adds_declared_properties():
    obj = FakeObj()
    reqs = [
        {"id": "PlateFace", "type": "selection", "label": "face"},
        {"id": "Angle", "type": "value", "label": "deg", "default": 45.0},
    ]
    req.sync_properties(obj, reqs)
    assert "PlateFace" in obj.PropertiesList
    assert "Angle" in obj.PropertiesList
    assert obj.Angle == 45.0


def test_sync_removes_orphans():
    obj = FakeObj()
    req.sync_properties(obj, [{"id": "A", "type": "value"}])
    assert "A" in obj.PropertiesList
    # macro changed: A no longer declared, B is
    req.sync_properties(obj, [{"id": "B", "type": "value"}])
    assert "A" not in obj.PropertiesList  # orphan removed
    assert "B" in obj.PropertiesList


def test_sync_leaves_non_input_props_alone():
    obj = FakeObj()
    obj.addProperty("App::PropertyString", "MacroName", "DatumHook", "")
    req.sync_properties(obj, [{"id": "A", "type": "value"}])
    # MacroName is in a different group -> untouched
    assert "MacroName" in obj.PropertiesList


def test_missing_requirements_flags_unset_links():
    obj = FakeObj()
    reqs = [{"id": "Face", "type": "selection"}, {"id": "N", "type": "value"}]
    req.sync_properties(obj, reqs)
    # Face link unset -> missing; N is a value (not a link) -> not flagged
    assert req.missing_requirements(obj, reqs) == ["Face"]
    obj.Face = (object(), ["Face1"])  # fulfilled
    assert req.missing_requirements(obj, reqs) == []


def test_choice_sets_enum_options():
    obj = FakeObj()
    req.sync_properties(obj, [{"id": "Mode", "type": "choice",
                               "options": ["a", "b", "c"]}])
    assert obj.Mode == ["a", "b", "c"]  # list assignment = enum choices
