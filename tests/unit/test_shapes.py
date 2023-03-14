from grasshopper.lib.util.shapes import Default


def test_default_shape():
    shape = Default(runtime=100, spawn_rate=100, users=100)
    assert shape.configured_runtime == 100

    shape = Default()
    assert shape.configured_runtime == 120

    shape = Default(spawn_rate=100, users=100)
    assert shape.configured_runtime == 120

    Default.DEFAULT_RUNTIME = 1
    shape = Default()
    assert shape.configured_runtime == 1

    Default.DEFAULT_RUNTIME = 1
    shape = Default(runtime=100)
    assert shape.configured_runtime == 100
