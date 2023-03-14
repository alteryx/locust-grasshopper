"""Contents of the locust_grasshopper plugin which gets auomatically loaded."""
import json
import logging
import os
import time

import pytest
import tagmatcher
import yaml

from grasshopper.lib.fixtures.grasshopper_constants import GrasshopperConstants
from grasshopper.lib.grasshopper import Grasshopper

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    """Add in the grasshopper specific cmdline args."""
    parser.addoption(
        "--runtime",
        action="store",
        type=float,
        help="Test journeys time in seconds",
    )
    parser.addoption(
        "-U",
        "--users",
        action="store",
        type=int,
        help="Peak number of concurrent Locust users",
    )
    parser.addoption(
        "-R",
        "--spawn_rate",
        action="store",
        type=float,
        help="Rate to spawn users at (users per second)",
    )
    parser.addoption(
        "-S",
        "--shape",
        action="store",
        help="Specify the specific shape to run the test on, (E.G. 'trend')",
    )
    parser.addoption(
        "--slack_webhook",
        action="store",
        default=None,
        help="COMING SOON: Slack the webhook url. Will post to slack if supplied.",
    )
    parser.addoption(
        "--slack_report_failures_only",
        action="store",
        default=False,
        help="COMING SOON: If you only want to report test failures to slack ("
        "threshold/check/http errors). ",
    )
    parser.addoption(
        "--scenario_file",
        action="store",
        default=None,
        help="The scenario file location",
    )
    parser.addoption(
        "--scenario_name",
        action="store",
        default=None,
        help="If specifying a config file, you can specify a singular "
        "scenario name in the yaml file",
    )
    parser.addoption(
        "--tags",
        action="store",
        default=None,
        help="If a scenario YAML file is specified `pytest -s <my_yaml_file>...`, "
        "then these are the tags that the scenarios must match in order to be "
        "collected. For example, --tags=foo~bar means the scenarios must have "
        "both the foo and bar tags. --tags=foo+bar means the scenarios can have "
        "either foo or bar tags. More info on the query string can be found in "
        "the `tag-matcher` pip package README",
    )
    parser.addoption(
        "--influxdb",
        action="store",
        default=None,
        help="LEGACY: The influxdb host to report to, E.g. `123.123.123.123`.",
    )
    parser.addoption(
        "--influx_host",
        action="store",
        default=None,
        help="The influxdb host to report to, E.g. `123.123.123.123`.",
    )
    parser.addoption(
        "--influx_port",
        action="store",
        default=None,
        help="Port for your `influxdb` in the case where it is non-default.",
    )
    parser.addoption(
        "--influx_user",
        action="store",
        default=None,
        help="Username for your `influxdb`, if you have one.",
    )
    parser.addoption(
        "--influx_pwd",
        action="store",
        default=None,
        help="Password for your `influxdb`, if you have one.",
    )
    parser.addoption(
        "--cleanup_s3",
        action="store",
        default=True,
        help="Whether or not to clean up the configured s3 locations before "
        "each test. Defaults to True.",
    )
    parser.addoption(
        "--shape_instance",
        action="store",
        default=None,
        help="this is unsupported at the command-line level. DO NOT USE!",
    )
    parser.addoption(
        "--scenario_delay",
        action="store",
        type=int,
        default=0,
        help="Optional: If selecting a scenario file to run multiple scenarios, "
        "add a delay in seconds between them. Defaults to 0.",
    )
    parser.addoption(
        "--rp_token",
        action="store",
        type=str,
        default=None,
        help="COMING SOON: Token for connecting to the ReportPortal API",
    )
    parser.addoption(
        "--rp_launch_name",
        action="store",
        type=str,
        default=None,
        help="COMING SOON: Launch name to use for a test run",
    )
    parser.addoption(
        "--rp_endpoint",
        action="store",
        type=str,
        default=None,
        help="COMING SOON: Url to link the ReportPortal server, the endpoint for "
        "posting",
    )
    parser.addoption(
        "--rp_project",
        action="store",
        type=str,
        default=None,
        help="COMING SOON: ReportPortal project where launch should be created",
    )


@pytest.fixture(scope="function")
def grasshopper_attr_names():
    """Returns all grasshopper related attribute/options that are available."""
    return GrasshopperConstants.GRASSHOPPER_ATTR_NAMES


@pytest.fixture(scope="function")
def scenario_content(request):
    """Returns the scenario content, given that a YAML file is being specified for
    the test run."""
    return _get_scenario_content(request=request)


@pytest.fixture(scope="function")
def grasshopper_scenario_args():
    """a fixture for grasshopper journey args, which will later be set by
    grasshopper_scenario_file_set_args."""
    return {}


@pytest.fixture(scope="function")
def grasshopper_scenario_file_set_args(grasshopper_scenario_args, scenario_content):
    """Sets the grasshopper args and grasshopper journey args if a YAML file is
    specified when invoking pytest."""
    grasshopper_scenario_file_args = {}
    if scenario_content is not None:
        grasshopper_scenario_file_args.update(
            scenario_content.get("grasshopper_args", {})
        )
        _update_scenario_args(
            new_scenario_args=scenario_content.get("grasshopper_scenario_args", {}),
            new_tags=scenario_content.get("tags", []),
            scenario_args_dict=grasshopper_scenario_args,
        )
    return grasshopper_scenario_file_args


@pytest.fixture(scope="function")
def grasshopper_base_args(
    grasshopper_scenario_file_set_args, grasshopper_attr_names, request
):
    """Grabs grasshopper args from cmdline options."""
    grasshopper_base_args = grasshopper_scenario_file_set_args

    # override commandline params on top of scenario file args
    grasshopper_base_args.update(
        _fetch_args(attr_names=grasshopper_attr_names, config=request.config)
    )
    logger.debug(
        f"After fetching incoming args from pytest, grasshopper_base_args"
        f"={grasshopper_base_args}"
    )
    return grasshopper_base_args


@pytest.fixture(scope="function")
def grasshopper_args_with_shape_processed(grasshopper_base_args):
    """Given grasshopper base args, sets the shape instance and all dependent
    attributes."""
    shape_name = grasshopper_base_args.get("shape", GrasshopperConstants.SHAPE_DEFAULT)
    shape_instance = Grasshopper.load_shape(
        shape_name=shape_name, **grasshopper_base_args
    )
    grasshopper_base_args["runtime"] = getattr(shape_instance, "runtime")
    grasshopper_base_args["users"] = getattr(shape_instance, "users")
    grasshopper_base_args["spawn_rate"] = getattr(shape_instance, "spawn_rate")
    grasshopper_base_args["shape_instance"] = shape_instance
    grasshopper_base_args["shape"] = shape_name
    logger.debug(
        f"After processing shape, px_args_with_shape_processed={grasshopper_base_args}"
    )
    return grasshopper_base_args


@pytest.fixture(scope="function")
def grasshopper_args_type_cast(grasshopper_args_with_shape_processed):
    """Ensure the types of the args are correct."""
    grasshopper_args_with_shape_processed["runtime"] = float(
        grasshopper_args_with_shape_processed.get(
            "runtime", GrasshopperConstants.RUNTIME_DEFAULT
        )
    )
    grasshopper_args_with_shape_processed["users"] = int(
        grasshopper_args_with_shape_processed.get(
            "users", GrasshopperConstants.USERS_DEFAULT
        )
    )
    grasshopper_args_with_shape_processed["spawn_rate"] = float(
        grasshopper_args_with_shape_processed.get(
            "spawn_rate", GrasshopperConstants.SPAWN_RATE_DEFAULT
        )
    )
    grasshopper_args_with_shape_processed["scenario_delay"] = float(
        grasshopper_args_with_shape_processed.get(
            "scenario_delay", GrasshopperConstants.SCENARIO_DELAY_DEFAULT
        )
    )
    logger.debug(
        f"After type casting, grasshopper_args_with_shape_processed="
        f"{grasshopper_args_with_shape_processed}"
    )
    return grasshopper_args_with_shape_processed


@pytest.fixture(scope="function")
def grasshopper_args(grasshopper_args_type_cast):
    """The public fixture to be used by grasshopper tests. This is after all
    configuration has been set."""
    logger.debug(
        f"After final processing, grasshopper_args =" f" {grasshopper_args_type_cast}"
    )
    return grasshopper_args_type_cast


@pytest.fixture(scope="function", autouse=True)
def do_scenario_delay(grasshopper_args):
    """Functionality to delay between each scenario run."""
    yield
    delay = grasshopper_args.get("scenario_delay")
    if delay > 0:
        logger.info(f"Waiting for {delay} seconds between scenarios...")
        time.sleep(delay)
    else:
        logger.debug(f"Skipping delay of {delay} seconds between scenarios...")


def pytest_collect_file(parent, path):
    """Collect Yaml files for pytest."""
    logger.debug(f"Performing collection for yaml {parent} {path}")
    allowed_yaml_exts = [".yaml", ".yml"]
    # if pytest is run via yaml, E.G. `pytest my_scenarios.yaml`, then return a YAML
    # scenario file pytest node. This node will then kick off individual files
    # that point to certain scenario names within that yaml. Once the individual
    # files are kicked off, then we fall into the else case.
    if path.ext.lower() in allowed_yaml_exts:
        return YamlScenarioFile.from_parent(parent, fspath=path)
    else:
        return


@pytest.fixture(scope="session", autouse=True)
def rp_args(request):
    """Load all the report portal specific arguments.

    TODO: Note that we aren't putting these (the rp_* args) in grasshopper_args
    currently because the scope of grasshopper_args isn't compatible --> really we
    should re-work grasshopper_args to be 1) global configuration items that are the
    same for the entire suite such as reportportal, slack, influx, etc. 2) global-ish
    items that each scenario may have a different value for (but the keys are common)
    such as runtime, users and 3) journey args which are test specific keys where
    each scenario may have a different value such as flow_name, directory_name,
    node_name, etc. Each of these categories really should be handled separately as
    we want slightly different behavior for each set (and also, as I said above,
    it messes up the fixture scope by putting them all in the same bucket)

    """
    args = {}
    args["token"] = request.config.getoption("--rp_token") or os.getenv("RP_TOKEN")

    args["rp_launch_name"] = (
        request.config.getoption("--rp_launch_name")
        or os.getenv("RP_LAUNCH_NAME")
        or "Grasshopper Performance Test Run | Launch name unknown"
    )
    args["rp_endpoint"] = (
        request.config.getoption("--rp_endpoint")
        or os.getenv("RP_ENDPOINT")
        or "http://reportportal.devops.alteryx.com"
    )
    args["rp_project"] = (
        request.config.getoption("--rp_project")
        or os.getenv("RP_PROJECT")
        or "PERFORMANCE"
    )
    return args


class YamlScenarioFile(pytest.File):
    """The logic behind what to do when a Yaml file is specified in pytest."""

    def collect(self):
        """Collect the file, knowing the path via self.fspath."""
        # Third Party
        import yaml

        raw = yaml.safe_load(self.fspath.open())
        valid_scenarios = _get_tagged_scenarios(
            raw_yaml_dict=raw, config=self.config, fspath=self.fspath
        )  # tag filter
        for scenario_name, scenario_contents in valid_scenarios.items():
            test_file_name = scenario_contents.get("test_file_name")
            if test_file_name:
                yield Scenario.from_parent(
                    self, name=scenario_name, spec=scenario_contents
                )
            else:
                raise AttributeError(
                    f"The YAML scenario `{scenario_name}` "
                    f"is missing the required `test_file_name` parameter"
                )


class Scenario(pytest.Item):
    """A pytest test that corresponds to a scenario within a scenario file."""

    def __init__(self, name, parent, spec):
        """Set the scenario properties in order to be run via runtest."""
        super().__init__(name, parent)
        self.parent = parent

        self.scenario_name = name
        self.scenario_file = self.parent.fspath
        self.test_file_name = spec.get("test_file_name")

    def runtest(self):
        """Run the pytest test/scenario."""
        pytest.main(
            [
                self.test_file_name,
                f"--scenario_file={self.scenario_file}",
                f"--scenario_name={self.scenario_name}",
            ]
            + [
                f"--{option_name}={self.config.getoption(option_name)}"
                for option_name in _fetch_args(
                    attr_names=GrasshopperConstants.GRASSHOPPER_ATTR_NAMES,
                    config=self.config,
                )
            ]
            + [
                extra_arg
                for extra_arg in list(self.config.invocation_params.args)
                if "--" in extra_arg
            ]  # pass down any other params that were supplied when invoking pytest
        )

    def repr_failure(self, excinfo):
        """Call this method when self.runtest() raises an exception."""
        if isinstance(excinfo.value, YamlError):
            return "\n".join(
                [
                    f"Scenario `{self.name}` FAILED: ",
                    "{1!r}: {2!r}".format(*excinfo.value.args),
                ]
            )

    def reportinfo(self):
        """Return info about the scenario being run."""
        return self.fspath, 0, f"Scenario: {self.name}"


class YamlError(Exception):
    """Custom exception for error reporting."""


# --------------------------------------- HELPERS --------------------------------------
def _update_scenario_args(
    new_scenario_args: dict, scenario_args_dict: dict, new_tags: list
):
    if new_scenario_args.get("thresholds"):
        new_scenario_args["thresholds"] = json.loads(new_scenario_args["thresholds"])
    scenario_args_dict["tags"] = new_tags
    scenario_args_dict.update(new_scenario_args)


def _fetch_args(attr_names, config) -> dict:
    args = {}
    for arg in attr_names:
        if arg in config.option.__dict__.keys() and config.getoption(f"{arg}"):
            args[arg] = config.getoption(f"{arg}")
    return args


def _get_tagged_scenarios(raw_yaml_dict, config, fspath) -> dict:
    valid_scenarios = {}
    if config.getoption("--tags"):
        for scenario_name, scenario_contents in raw_yaml_dict.items():
            tags_list = scenario_contents.get("tags")

            # protecting for the case where tags is specified as a key in the
            # YAML, but there's no value pair
            if not tags_list:
                tags_list = []

            # always include the scenario name as a tag, this gives an easy way to
            # select a single scenario in test pipelines (you can also do the
            # entirely different format of specifying the .py file, yaml file &
            # scenario name, but this makes the script logic much more complex)
            tags_list.append(scenario_name)
            if tagmatcher.match(query_str=config.getoption("--tags"), tags=tags_list):
                valid_scenarios[scenario_name] = scenario_contents
        logging.info(
            f"Scenarios collected that match the specific tag query `"
            f'{config.getoption("--tags")}`: '
            f"{[scenario_name for scenario_name in valid_scenarios.keys()]}"
        )
    else:
        logging.warning(
            f"Since no --tags param was specified, ALL scenarios in "
            f"{fspath} will be run!"
        )
        valid_scenarios = raw_yaml_dict

    return valid_scenarios


def _get_scenario_content(request):
    scenario_file_name = request.config.getoption("scenario_file")
    scenario_name = request.config.getoption("scenario_name")
    if scenario_file_name:
        logger.info(
            f"Initiating scenario `{scenario_name}` in `{scenario_file_name}`..."
        )
        with open(str(scenario_file_name), "r") as stream:
            yaml_dict = yaml.safe_load(stream)
            scenario_dict = yaml_dict.get(str(scenario_name), None)
            if scenario_dict is None:
                raise ValueError(
                    f"Unable to find scenario {scenario_name} "
                    f"in scenario file `{scenario_file_name}`. "
                    f"Please check your spelling."
                )
            return scenario_dict
    else:
        logger.info(
            "No scenario file specified. "
            "Initiating default scenario + command-line params..."
        )
        return None
