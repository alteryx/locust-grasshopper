from grasshopper.lib.util.shapes import Default, Spike


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


def test_spike_runtime_is_spike_duration_plus_cooldown_duration():
    shape = Spike(runtime=10, cooldown_duration=5, users=8, spawn_rate=2)

    assert [stage["duration"] for stage in shape.stages] == [10, 5]
    assert shape.configured_runtime == 15
