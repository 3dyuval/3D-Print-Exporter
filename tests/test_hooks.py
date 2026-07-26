import os

from freecad.tools_for_print.core import hooks as hookmod


def test_discover_and_load(tmp_path):
    d = tmp_path / "hooks"
    d.mkdir()
    (d / "good.py").write_text("def hook(ctx):\n    return 'ran'\n")
    (d / "_skip.py").write_text("def hook(ctx):\n    return 'no'\n")
    (d / "notes.txt").write_text("ignored")

    found = hookmod.discover([(str(d), "user")])
    names = [h.name for h in found]
    assert names == ["good"]              # _skip and .txt excluded
    fn = found[0].load_callable()
    assert fn(None) == "ran"


def test_user_shadows_builtin(tmp_path):
    b = tmp_path / "builtin"
    u = tmp_path / "user"
    b.mkdir()
    u.mkdir()
    (b / "op.py").write_text("def hook(ctx):\n    return 'builtin'\n")
    (u / "op.py").write_text("def hook(ctx):\n    return 'user'\n")

    found = hookmod.discover([(str(b), "builtin"), (str(u), "user")])
    assert len(found) == 1
    assert found[0].source == "user"
    assert found[0].load_callable()(None) == "user"


def test_bundled_hooks_are_valid():
    """The shipped hooks must import and expose hook(ctx)."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hooks_dir = os.path.join(here, "hooks")
    found = hookmod.discover([(hooks_dir, "builtin")])
    assert {h.name for h in found} >= {"ensure_on_bed", "align_face_to_plate"}
    for h in found:
        assert callable(h.load_callable())
