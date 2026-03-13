from unittest.mock import MagicMock, create_autospec
from uuid import uuid4

import pytest
from grasshopper.lib.journeys.base_journey import BaseJourney
from grasshopper.lib.util.metrics import count_iterations, task
from locust.env import Environment
from locust.stats import RequestStats


@pytest.fixture(scope="session")
def sample_func():
    def sample(journey):
        # just return the same object, so we can check that it's working correctly
        return journey

    return sample


@pytest.fixture(scope="session")
def sample_func_different():
    def sample(journey):
        # just return the same object, so we can check that it's working correctly
        return journey

    return sample


@pytest.fixture
def mock_journey():
    mock_journey = create_autospec(BaseJourney)
    mock_journey.vu_iteration = 0
    mock_journey.client_id = uuid4()
    mock_journey.environment = create_autospec(Environment)
    mock_journey.environment.stats = create_autospec(RequestStats)
    mock_journey.environment.stats.num_iterations = 0
    return mock_journey


def check_iteration_count(journey, count):
    assert (
        journey.environment.stats.num_iterations == count
    ), "Decorator did not actually increment the environment iterations count"
    assert (
        journey.vu_iteration == count
    ), "Decorator did not actually increment the vu_iteration count on the journey"


def test__count_iterations(sample_func, mock_journey):
    # simulate applying our decorator, remember that
    # @decorator
    # def method(...): ...
    # is syntactic sugar for replace method with decorator(method)
    # therefore to call method, you would do (decorator(method))(...)
    wrapped_func = count_iterations(sample_func)
    assert callable(wrapped_func), "Return value of decorator is not a callable."
    result_of_calling_wrapped_func = wrapped_func(mock_journey)
    check_iteration_count(result_of_calling_wrapped_func, 1)


def test__count_iterations_multiple_calls(sample_func, mock_journey):
    wrapped_func = count_iterations(sample_func)
    wrapped_func(mock_journey)
    wrapped_func(mock_journey)
    result_of_calling_wrapped_func = wrapped_func(mock_journey)
    check_iteration_count(result_of_calling_wrapped_func, 3)


def test__count_iterations_multiple_functions(
    sample_func, sample_func_different, mock_journey
):
    # check that multiple wraps (represents different tasks on same journey) can both
    # increment the vu_iteration count correctly
    wrapped_func = count_iterations(sample_func)
    wrapped_func(mock_journey)
    wrapped_diff = count_iterations(sample_func_different)
    wrapped_diff(mock_journey)
    result_of_calling_wrapped_func = wrapped_func(mock_journey)
    check_iteration_count(result_of_calling_wrapped_func, 3)


def test__task_default_weight(sample_func, mock_journey):
    wrapped_func = task(sample_func)
    assert callable(wrapped_func), "Return value of decorator is not a callable."
    result_of_calling_wrapped_func = wrapped_func(mock_journey)
    # our task decorator wraps locust's task decorator with vu_iteration tracking
    # check that the locust_task_weight attr was transferred to the new wrapped function
    # this attr is how locust tells which tasks are to be collected when running a test
    assert wrapped_func.locust_task_weight == 1
    check_iteration_count(result_of_calling_wrapped_func, 1)


def test__task_specifying_weight(sample_func):
    # use this class to check specifying the decorator with a weight
    # there should be a way to check using the function equivalent, but I couldn't
    # quite get the mocking correct in that case, since both our code and the locust
    # code are assuming that the task is a bound method on the journey class
    # the syntactic equivalent for the sugar @task(4) is
    # the attribute fake_task = (task(4))(fake_task)
    class FakeJourney(BaseJourney):
        client_id = uuid4()
        vu_iteration = 0

        @task(4)
        def fake_task(self):
            return self

    env = create_autospec(Environment)
    env.stats = create_autospec(RequestStats)
    env.stats.num_iterations = 0
    env.events = MagicMock()
    journey = FakeJourney(env)
    journey_after = journey.fake_task()
    assert journey_after.fake_task.locust_task_weight == 4
