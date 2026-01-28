"""Module: BaseUserJourney.

Class to hold all the common functionality that we added on top of Locust's HttpUser
class.
"""

import logging
import signal
from collections import abc

import gevent
import grasshopper.lib.util.listeners  # noqa: F401
from grasshopper.lib.fixtures.grasshopper_constants import GrasshopperConstants
from grasshopper.lib.journeys.base_journey import BaseJourney, VULoggingAdapter
from locust import User

# This is an inbuilt logger, renamed for clarity of purpose.
# It logs messages without prefixing them with the virtual user (VU) number.
log_no_prefix = logging.getLogger(__name__)


class BaseUserJourney(User):
    """The base journey class for all other journey classes."""

    VUS_DICT = {}
    host = None
    _incoming_test_parameters = {}
    abstract = True
    base_torn_down = False
    defaults = {"thresholds": {}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vu_number = len(BaseUserJourney.VUS_DICT) + 1
        self.log_prefix = VULoggingAdapter(
            logging.getLogger(__name__), {"instance": self}
        )
        self.tags = {}

    @classmethod
    def update_incoming_scenario_args(cls, higher_precedence_args):
        """Add more values to scenario_args with higher precedence."""
        cls._incoming_test_parameters.update(higher_precedence_args)

    def on_start(self):
        """Initialize the journey, set tags, and then set the test parameters."""
        super().on_start()
        self._merge_incoming_defaults_and_params()
        self._test_parameters = self._incoming_test_parameters.copy()
        self._set_base_teardown_listeners()
        # self.client_id = str(uuid4())

        self._register_new_vu()
        self._set_thresholds()
        # self.environment.host = self.normalize_url(
        #     self.scenario_args.get("target_url") or self.host
        # )
        self.defaults["tags"] = self.tags
        # self.update_tags({"environment": self.environment.host})

        # TODO: currently global iterations is stored in the environment stats object
        # TODO: poke around to see if we can move it to a class attribute here
        self.vu_iteration = 0

    def update_tags(self, new_tags: dict):
        """Update the tags for the influxdb listener."""
        self.tags.update(new_tags)

    def _merge_incoming_defaults_and_params(self):
        BaseJourney.merge_incoming_scenario_args(self.defaults)

    def _set_base_teardown_listeners(self):
        gevent.signal_handler(signal.SIGINT, self.teardown)

    def _register_new_vu(self):
        """Increment the user count and return the new vu's number."""
        BaseUserJourney.VUS_DICT[self.vu_number] = self

    @property
    def scenario_args(self):
        return self._test_parameters

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
            self.log_prefix.warning(
                "Skipping registering thresholds due to invalid thresholds shape..."
            )

    @staticmethod
    def _verify_thresholds_collection_shape(thresholds_collection):
        valid_types = ["GET", "POST", "PUT", "DELETE", "HEAD", "PATCH", "CUSTOM"]
        if not isinstance(thresholds_collection, abc.Mapping):
            log_no_prefix.warning(
                f"Thresholds object is of type {type(thresholds_collection)} "
                f"but must be a mapping!"
            )
            return False
        for trend_name, threshold_values in thresholds_collection.items():
            if (
                threshold_values.get("type") is None
                or threshold_values.get("limit") is None
            ):
                log_no_prefix.warning(
                    f"Singular threshold object `{trend_name}` must have `type`"
                    f"and `limit` fields defined."
                )
                return False
            elif str(threshold_values.get("type")).upper() not in valid_types:
                log_no_prefix.warning(
                    f"For threshold object {trend_name}, type "
                    f"`{str(threshold_values.get('type')).upper()}` is "
                    f"invalid. Must be one of {valid_types}."
                )
                return False
            elif not str(threshold_values.get("limit")).isnumeric():
                log_no_prefix.warning(
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
        BaseUserJourney.VUS_DICT = {}
        self.environment.runner.quit()
