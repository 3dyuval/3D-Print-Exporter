from freecad.print_exporter.core import transform as tf


def test_identity_apply():
    m = tf.identity()
    assert tf.apply_to_point(m, (1, 2, 3)) == (1, 2, 3)


def test_translation():
    m = tf.translation(5, 7, 9)
    assert tf.apply_to_point(m, (1, 1, 1)) == (6, 8, 10)


def test_transformed_z_matches_apply():
    m = tf.translation(0, 0, -4)
    x, y, z = tf.apply_to_point(m, (2, 3, 10))
    assert z == tf.transformed_z(m, (2, 3, 10)) == 6


def test_matmul_compose_order():
    # matmul(a, b) applies b then a. Rotate-none + translate.
    t1 = tf.translation(1, 0, 0)
    t2 = tf.translation(0, 2, 0)
    composed = tf.matmul(t1, t2)  # apply t2 then t1
    assert tf.apply_to_point(composed, (0, 0, 0)) == (1, 2, 0)


def test_lib3mf_roundtrip_shape():
    # from_lib3mf(to_lib3mf(m)) == m using a fake wrapper mimicking the ctypes
    # [4][3] column-major Fields array.
    class FakeArray(list):
        pass

    class FakeTransform:
        def __init__(self):
            self._f = [[0.0, 0.0, 0.0] for _ in range(4)]

        @property
        def Fields(self):
            return self._f

        @Fields.setter
        def Fields(self, v):
            self._f = v

    class FakeWrapper:
        def GetIdentityTransform(self):
            t = FakeTransform()
            f = [[0.0, 0.0, 0.0] for _ in range(4)]
            f[0][0] = f[1][1] = f[2][2] = 1.0
            t.Fields = f
            return t

    m = tf.translation(3, 4, 5)
    m[0][1] = 0.5  # add an off-diagonal to catch transposition bugs
    w = FakeWrapper()
    back = tf.from_lib3mf(tf.to_lib3mf(w, m))
    assert back == m
