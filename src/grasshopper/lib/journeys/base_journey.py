"""Module: BaseJourney.

Class to hold all the common functionality that we added on top of Locust's HttpUser
class.
"""
import logging
import signal
from collections import abc
from uuid import uuid4

import gevent
from locust import HttpUser

import grasshopper.lib.util.listeners  # noqa: F401
from grasshopper.lib.fixtures.grasshopper_constants import GrasshopperConstants


class BaseJourney(HttpUser):
    """The base journey class for all other journey classes."""

    VUS_DICT = {}
    host = ""
    _incoming_test_parameters = {}
    abstract = True
    base_torn_down = False
    tags = {}
    defaults = {"tags": tags, "thresholds": {}}

    @classmethod
    @property
    def incoming_scenario_args(cls):
        return cls._incoming_test_parameters

    @property
    def scenario_args(self):
        return self._test_parameters

    @classmethod
    def replace_incoming_scenario_args(cls, brand_new_args={}):
        """Replace the existing set of scenario_args with a new collection."""
        cls._incoming_test_parameters = brand_new_args

    @classmethod
    def update_incoming_scenario_args(cls, higher_precedence_args):
        """Add more values to scenario_args with higher precedence."""
        cls._incoming_test_parameters.update(higher_precedence_args)

    @classmethod
    def merge_incoming_scenario_args(cls, lower_precedence_args):
        """Add more values to scenario_args with lower precedence."""
        new_args = lower_precedence_args.copy()
        new_args.update(cls._incoming_test_parameters)
        cls.replace_incoming_scenario_args(new_args)

    def update_tags(self, new_tags: dict):
        """Update the tags for the influxdb listener."""
        self.tags.update(new_tags)
        db_listener = self.environment.grasshopper_listeners.influxdb_listener
        if db_listener is not None:
            db_listener.additional_tags.update(new_tags)

    @classmethod
    def reset_class_attributes(cls):
        """Reset the class level attributes to their starting state.

        We are using class level attributes because most of the time we want the state
        to be shared across all the instances of the class, since these values *should*
        always be the same across the instances and performance should be better without
        storing a copy for every instance.

        But in order to support unit testing and possibly other scenarios, this method
        is provided as a way to reset to the starting state.
        """
        cls._incoming_test_parameters = {}
        cls.tags = {}
        cls.defaults = {"tags": cls.tags}
        cls.host = ""
        cls.abstract = True
        cls.base_torn_down = False
        BaseJourney.VUS_DICT = {}

    @classmethod
    def get_journey_object_given_vu_number(cls, vu_number):
        """Get the journey class if exists in the instance-level context, else None."""
        return cls.VUS_DICT.get(vu_number)

    def on_start(self):
        """Initialize the journey, set tags, and then set the test parameters."""
        super().on_start()
        self._merge_incoming_defaults_and_params()
        self._test_parameters = self._incoming_test_parameters.copy()
        self._set_base_teardown_listeners()
        self.client_id = str(uuid4())
        self._register_new_vu()
        self._set_thresholds()
        self.environment.host = self.scenario_args.get("target_url", "") or self.host
        self.update_tags({"environment": self.environment.host})

        # TODO: currently global iterations is stored in the environment stats object
        # TODO: poke around to see if we can move it to a class attribute here
        self.vu_iteration = 0

    def _register_new_vu(self):
        """Increment the user count and return the new vu's number."""
        self.vu_number = len(BaseJourney.VUS_DICT) + 1
        BaseJourney.VUS_DICT[self.vu_number] = self

    def _set_base_teardown_listeners(self):
        gevent.signal_handler(signal.SIGINT, self.teardown)  # ctrl-c teardown bind

    def _merge_incoming_defaults_and_params(self):
        self.merge_incoming_scenario_args(self.defaults)

    def _set_thresholds(self):
        self.environment.stats.trends = {}

        # If parameters are not passed in that need to be set, set them to the defaults
        self._check_for_threshold_parameters_and_set_thresholds(
            scenario_args=self.scenario_args
        )

    def _check_for_threshold_parameters_and_set_thresholds(self, scenario_args):
        thresholds_collection = scenario_args.get("thresholds")
        if thresholds_collection is None:
            return
        elif self._verify_thresholds_collection_shape(thresholds_collection):
            for trend_name, threshold_values in thresholds_collection.items():
                trend_name = str(trend_name)
                thresh_object = {
                    "less_than_in_ms": int(threshold_values.get("limit")),
                    "actual_value_in_ms": None,
                    "percentile": float(
                        threshold_values.get(
                            "percentile",
                            GrasshopperConstants.THRESHOLD_PERCENTILE_DEFAULT,
                        )
                    ),
                    "succeeded": None,
                    "http_method": str(threshold_values.get("type")).upper(),
                }
                if trend_name in self.environment.stats.trends:
                    self.environment.stats.trends[trend_name]["thresholds"].append(
                        thresh_object
                    )
                else:
                    self.environment.stats.trends[trend_name] = {
                        "tags": self.scenario_args.get("tags", {}),
                        "thresholds": [thresh_object],
                    }
        else:
            logging.warning(
                "Skipping registering thresholds due to invalid " "thresholds shape..."
            )

    @staticmethod
    def _verify_thresholds_collection_shape(thresholds_collection):
        valid_types = ["GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "CUSTOM"]
        if not isinstance(thresholds_collection, abc.Mapping):
            logging.warning(
                f"Thresholds object is of type {type(thresholds_collection)} "
                f"but must be a mapping!"
            )
            return False
        for trend_name, threshold_values in thresholds_collection.items():
            if (
                threshold_values.get("type") is None
                or threshold_values.get("limit") is None
            ):
                logging.warning(
                    f"Singular threshold object `{trend_name}` must have `type`"
                    f"and `limit` fields defined."
                )
                return False
            elif str(threshold_values.get("type")).upper() not in valid_types:
                logging.warning(
                    f"For threshold object {trend_name}, type "
                    f"`{str(threshold_values.get('type')).upper()}` is "
                    f"invalid. Must be one of {valid_types}."
                )
                return False
            elif not str(threshold_values.get("limit")).isnumeric():
                logging.warning(
                    f"For threshold object {trend_name}, threshold limit of "
                    f"`{threshold_values.get('limit')}` is invalid. "
                    f"Must be numeric."
                )
                return False
        return True

    def teardown(self, *args, **kwargs):
        """
        Tear down the journey and quit.

        The proper way to do your own tear down when extending this class is like so:
            def teardown(self, *args, **kwargs):
                # do your teardown stuff here
                super().teardown(*args, **kwargs)
        """
        self.base_torn_down = True
        stopped_vus = [vu.base_torn_down for vu in BaseJourney.VUS_DICT.values()]
        for i in range(60):
            if not all(stopped_vus):
                gevent.sleep(1)
            else:
                break
        BaseJourney.VUS_DICT = {}
        self.environment.runner.quit()
