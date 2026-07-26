from freecad.print_exporter.core import operations as ops
from freecad.print_exporter.core import transform as tf

from tests.fakes import FakeBuildItem, FakeModel


def test_ensure_on_bed_drops_to_zero():
    # a part floating with min z = 4 should drop by 4
    item = FakeBuildItem(vertices=[(0, 0, 4), (10, 0, 6), (0, 10, 9)])
    model = FakeModel([item])
    moved = ops.ensure_on_bed(model)
    assert moved == 1
    assert model.item_min_z(item) == 0


def test_ensure_on_bed_lifts_sunk_part():
    item = FakeBuildItem(vertices=[(0, 0, -3), (1, 0, -1)])
    model = FakeModel([item])
    ops.ensure_on_bed(model)
    assert model.item_min_z(item) == 0


def test_ensure_on_bed_noop_when_already_on_bed():
    item = FakeBuildItem(vertices=[(0, 0, 0), (1, 1, 2)])
    model = FakeModel([item])
    assert ops.ensure_on_bed(model) == 0


def test_allow_negative_z_leaves_small_sink():
    item = FakeBuildItem(vertices=[(0, 0, -0.02), (1, 0, 3)])
    model = FakeModel([item])
    moved = ops.ensure_on_bed(model, allow_negative_z=True, sink_threshold=0.05)
    assert moved == 0  # within threshold, left alone


def test_apply_to_all_composes():
    items = [FakeBuildItem([(0, 0, 0)]), FakeBuildItem([(0, 0, 0)])]
    model = FakeModel(items)
    n = ops.apply_to_all(model, tf.translation(1, 2, 3))
    assert n == 2
    for it in items:
        assert tf.apply_to_point(it.transform, (0, 0, 0)) == (1, 2, 3)
