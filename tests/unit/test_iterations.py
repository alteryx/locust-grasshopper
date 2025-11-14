"""Unit tests for the iterations feature."""

from unittest.mock import MagicMock, create_autospec, patch

import pytest
from grasshopper.lib.grasshopper import Grasshopper
from grasshopper.lib.journeys.base_journey import BaseJourney
from locust.env import Environment
from locust.exception import StopUser
from locust.runners import LocalRunner
from locust.user.task import DefaultTaskSet, TaskSet


class MockJourney(BaseJourney):
    """Mock journey for testing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_count = 0

    def example_task(self):
        self.task_count += 1


@pytest.fixture
def mock_environment():
    """Create a mock environment for testing."""
    env = create_autospec(Environment)
    env.runner = create_autospec(LocalRunner)
    env.runner.user_count = 1
    env.runner.iterations_count = 0
    env.runner.iterations_exhausted = False
    return env


def test_setup_iteration_limit_initializes_runner_attributes(mock_environment):
    """Test that _setup_iteration_limit properly initializes runner attributes."""
    Grasshopper._setup_iteration_limit(mock_environment, 10)

    assert mock_environment.runner.iterations_count == 0
    assert mock_environment.runner.iterations_exhausted is False


def test_setup_iteration_limit_patches_taskset_methods(mock_environment):
    """Test that _setup_iteration_limit patches TaskSet methods."""
    # Store original methods
    original_taskset_execute = TaskSet.execute_task
    original_default_taskset_execute = DefaultTaskSet.execute_task

    try:
        Grasshopper._setup_iteration_limit(mock_environment, 10)

        # Check that methods have been patched (wrapped)
        assert TaskSet.execute_task != original_taskset_execute
        assert DefaultTaskSet.execute_task != original_default_taskset_execute

    finally:
        # Restore original methods
        TaskSet.execute_task = original_taskset_execute
        DefaultTaskSet.execute_task = original_default_taskset_execute


def test_iteration_limit_stops_after_reaching_limit(mock_environment):
    """Test that tasks stop executing after iteration limit is reached."""
    # Store original method
    original_taskset_execute = TaskSet.execute_task

    try:
        Grasshopper._setup_iteration_limit(mock_environment, 2)

        # Create a mock TaskSet instance
        mock_taskset = MagicMock(spec=TaskSet)

        # Create a callable mock task that is a bound method
        mock_task = MagicMock()
        mock_task.__self__ = mock_taskset

        # Execute tasks up to the limit
        TaskSet.execute_task(mock_taskset, mock_task)
        assert mock_environment.runner.iterations_count == 1

        TaskSet.execute_task(mock_taskset, mock_task)
        assert mock_environment.runner.iterations_count == 2

        # Next execution should raise StopUser
        with pytest.raises(StopUser):
            TaskSet.execute_task(mock_taskset, mock_task)

        # Verify that iteration target was reached
        assert mock_environment.runner.iterations_exhausted is True

    finally:
        # Restore original method
        TaskSet.execute_task = original_taskset_execute


def test_launch_test_with_runtime_only():
    """Test that launch_test runs for defined runtime when only runtime is specified (iterations=0).

    Runtime is always set as a safeguard to prevent tests from getting stuck.
    """
    with patch.object(Grasshopper, "set_ulimit"), patch.object(
        Grasshopper, "_setup_iteration_limit"
    ) as mock_setup_iterations, patch(
        "grasshopper.lib.grasshopper.Environment"
    ) as MockEnvironment, patch(
        "grasshopper.lib.grasshopper.gevent.spawn_later"
    ) as mock_spawn_later, patch("grasshopper.lib.grasshopper.gevent.spawn"), patch(
        "grasshopper.lib.grasshopper.locust.stats.stats_history"
    ), patch("grasshopper.lib.grasshopper.GrasshopperListeners"):
        # Setup mock environment
        mock_env = MagicMock()
        mock_env.runner = MagicMock()
        mock_env.runner.greenlet = MagicMock()
        mock_env.runner.greenlet.join = MagicMock()
        MockEnvironment.return_value = mock_env

        # Mock shape instance
        mock_shape = MagicMock()
        mock_shape.configured_runtime = 120

        # Launch test with iterations=0 and positive runtime
        kwargs = {"iterations": 0, "runtime": 120, "shape_instance": mock_shape}

        Grasshopper.launch_test(MockJourney, **kwargs)

        # Verify that _setup_iteration_limit was NOT called (iterations is 0)
        mock_setup_iterations.assert_not_called()

        # Verify that runtime timer WAS set
        mock_spawn_later.assert_called_once()
        # Check that it was called with the runtime value
        assert mock_spawn_later.call_args[0][0] == 120


def test_launch_test_with_both_iterations_and_runtime():
    """Test that launch_test stops based on what occurs first when both iterations and runtime are positive.

    Runtime is always set as a safeguard. When iterations are also specified,
    the test will stop when either limit is reached first.
    """
    with patch.object(Grasshopper, "set_ulimit"), patch.object(
        Grasshopper, "_setup_iteration_limit"
    ) as mock_setup_iterations, patch(
        "grasshopper.lib.grasshopper.Environment"
    ) as MockEnvironment, patch(
        "grasshopper.lib.grasshopper.gevent.spawn_later"
    ) as mock_spawn_later, patch("grasshopper.lib.grasshopper.gevent.spawn"), patch(
        "grasshopper.lib.grasshopper.locust.stats.stats_history"
    ), patch("grasshopper.lib.grasshopper.GrasshopperListeners"):
        # Setup mock environment
        mock_env = MagicMock()
        mock_env.runner = MagicMock()
        mock_env.runner.greenlet = MagicMock()
        mock_env.runner.greenlet.join = MagicMock()
        MockEnvironment.return_value = mock_env

        # Mock shape instance
        mock_shape = MagicMock()
        mock_shape.configured_runtime = 120

        # Launch test with both positive iterations and positive runtime
        kwargs = {"iterations": 10, "runtime": 120, "shape_instance": mock_shape}

        Grasshopper.launch_test(MockJourney, **kwargs)

        # Verify that BOTH iteration limit and runtime timer were set up
        mock_setup_iterations.assert_called_once_with(mock_env, 10)
        mock_spawn_later.assert_called_once()
        # Check that runtime timer was called with the runtime value
        assert mock_spawn_later.call_args[0][0] == 120
