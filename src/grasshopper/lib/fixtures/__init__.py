"""Contents of the locust_grasshopper plugin which gets automatically loaded."""
import logging
import os
import time

import pytest
import tagmatcher
import yaml

from grasshopper.lib.configuration.gh_configuration import (
    ConfigurationConstants,
    GHConfiguration,
)
from grasshopper.lib.grasshopper import Grasshopper
from grasshopper.lib.util.decorators import deprecate

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    """Add in the grasshopper specific cmdline args."""
    for attr_name, attr_definition in ConfigurationConstants.COMPLETE_ATTRS.items():
        opts = attr_definition["opts"]
        option_attrs = attr_definition.get("attrs", {})
        parser.addoption(*opts, **option_attrs)


# --------------------------------------- LEGACY --------------------------------------
# legacy, keep for backwards compatibility
@pytest.fixture(scope="function")
@deprecate("grasshopper_scenario_args fixture", "complete_configuration")
def grasshopper_scenario_args():
    """a fixture for grasshopper journey args, which will later be set by
    grasshopper_scenario_file_set_args."""
    return GHConfiguration()


# legacy, keep for backwards compatibility
@pytest.fixture(scope="function")
@deprecate("grasshopper_args fixture", "complete_configuration")
def grasshopper_args(complete_configuration):
    config = GHConfiguration(complete_configuration)
    """The public fixture to be used by grasshopper tests. This is after all
    configuration has been set."""
    return config


# ---------------------------- CONFIGURATION FIXTURES ---------------------------
@pytest.fixture(scope="session")
def global_defaults():
    defaults = {
        k: v.get("default")
        for k, v in ConfigurationConstants.COMPLETE_ATTRS.items()
        if v.get("default") is not None
    }
    config = GHConfiguration(**defaults)
    logger.info(f"CONFIG FIXTURE: global_defaults {config}")
    return config


@pytest.fixture(scope="session")
def grasshopper_config_file_args(request):
    config = GHConfiguration()
    try:
        # TODO: should move yaml read to it's own method
        path = request.getfixturevalue("grasshopper_config_file_path")
        with open(path, "r") as stream:
            raw = yaml.safe_load(stream)

        # transfer each section to GHConfiguration object
        global_vals = raw.get("grasshopper", {})
        config.update(**global_vals)
        test_run_vals = raw.get("test_run", {})
        config.update(**test_run_vals)
        scenario_vals = raw.get("scenario", {})
        config.update(**scenario_vals)

    except pytest.FixtureLookupError:
        logger.warning(
            "Skipping loading from grasshopper configuration file because fixture "
            "'grasshopper_config_file_path` not found. You can safely ignore this "
            "warning if you were not intending to use a grasshopper configuration file."
        )
    except FileNotFoundError:
        logger.warning(
            f"Skipping loading from grasshopper configuration file because {path} not "
            f"found."
        )
    except (yaml.YAMLError, AttributeError) as e:
        logger.warning(f"Unable to parse yaml file {path} with error {e}.")

    return config


@pytest.fixture(scope="session")
def env_var_prefix_key(request):
    prefix = "GH_"
    try:
        prefix = request.getfixturevalue("configuration_prefix_key")
    except pytest.FixtureLookupError:
        logger.info(f"Using default environment variable prefix of {prefix}")
        pass
    return prefix


@pytest.fixture(scope="session")
def extra_env_var_keys(request):
    keys = []
    try:
        keys = request.getfixturevalue("configuration_extra_env_var_keys")
    except pytest.FixtureLookupError:
        pass
    return keys


@pytest.fixture(scope="session")
def env_var_args(env_var_prefix_key, extra_env_var_keys):
    config = GHConfiguration()

    for env_var_name, env_var_value in os.environ.items():
        if (
            env_var_name.lower() in ConfigurationConstants.COMPLETE_ATTRS.keys()
            or env_var_name.startswith(env_var_prefix_key)
            or env_var_name in extra_env_var_keys
        ):
            if env_var_name.startswith(env_var_prefix_key):
                env_var_name = env_var_name.lstrip(env_var_prefix_key)

            if len(env_var_name) > 0:
                config.update_single_key(env_var_name.lower(), env_var_value)

    return config


@pytest.fixture(scope="session")
def request_config(request):
    """Separate config so that we have something to patch during unit testing.

    I could not find a way to patch the request object successfully using pytester.
    Patching fixtures we have defined is easier and then we don't have worry about
    how to sub in a config or request object that does all the other things correctly,
    but with new command line arguments. Note that config is _not_ a dict, so you can
    not just do patch.dict(...), which would be the natural way for this type of use
    case.

    """
    return request.config


@pytest.fixture(scope="session")
def cmdln_args(request_config):
    config = GHConfiguration()

    for attr_name, attr_definition in ConfigurationConstants.COMPLETE_ATTRS.items():
        config.update_single_key(attr_name, request_config.getoption(f"--{attr_name}"))

    return config


@pytest.fixture(scope="session")
def pre_processed_args(
    global_defaults, grasshopper_config_file_args, env_var_args, cmdln_args
):
    pre_config = GHConfiguration()
    try:
        # calculate a small dictionary of args that we need to in order to do the full
        # merge of args first, determine if we currently have a scenario file & scenario
        # name specified. if we don't have both, then we can skip merging in any values
        # from scenario file. the collection code for when a yaml is specified will
        # perform collection and call pytest.main again with the scenario file &
        # scenario name
        scenario_file = fetch_value_from_multiple_sources(
            [cmdln_args, env_var_args, grasshopper_config_file_args, global_defaults],
            "scenario_file",
        )
        logger.info(f"scenario file value = {scenario_file}")
        pre_config.update_single_key("scenario_file", scenario_file)
        logger.info(f"pre_config = {pre_config}")

        scenario_name = fetch_value_from_multiple_sources(
            [cmdln_args, env_var_args, grasshopper_config_file_args, global_defaults],
            "scenario_name",
        )
        pre_config.update_single_key("scenario_name", scenario_name)

    except Exception as e:
        logger.error(
            f"Uncaught exception in pre_processed_args fixture: "
            f"{type(e).__name__} | {e}"
        )

    return pre_config


@pytest.fixture(scope="session")
def scenario_file_args(pre_processed_args):
    config = GHConfiguration()

    # if we don't have both scenario file and scenario name, then there are no values to
    # load for this source; in the case of scenario collection, the collection code
    # calls pytest.main again with the scenario and filename, prompting something to be
    # loaded the 2nd time through the process of building the configuration values
    scenario_file = pre_processed_args.get("scenario_file")
    scenario_name = pre_processed_args.get("scenario_name")

    if scenario_file and scenario_name:
        try:
            with open(scenario_file, "r") as stream:
                raw = yaml.safe_load(stream)
            scenario = raw.get(scenario_name)
            config.update(scenario.get("grasshopper_args", {}))
            config.update(scenario.get("grasshopper_scenario_args", {}))
            config.update_single_key(
                "scenario_test_file_name", scenario.get("test_file_name")
            )
            config.update_single_key("scenario_tags", scenario.get("tags"))
        except Exception as e:
            logger.warning(
                f"Unexpected error loading scenario {scenario_name} from "
                f"{scenario_file}: {type(e).__name__} | {e}"
            )

    return config


@pytest.fixture(scope="session")
def merge_sources(
    global_defaults,
    grasshopper_config_file_args,
    scenario_file_args,
    env_var_args,
    cmdln_args,
):
    complete_config = GHConfiguration()

    # order matters here, this is determining the variable precedence
    try:
        complete_config.update(global_defaults)
        complete_config.update(grasshopper_config_file_args)
        complete_config.update(scenario_file_args)
        complete_config.update(env_var_args)
        complete_config.update(cmdln_args)
    except Exception as e:
        logger.error(f"Unexpected error in merge_sources: {type(e).__name__} | {e}")
        pass

    return complete_config


@pytest.fixture(scope="session")
def typecast(merge_sources):
    config = GHConfiguration(merge_sources)

    # get the collection of attrs that have a typecast func listed
    attrs = {
        k: v
        for k, v in ConfigurationConstants.COMPLETE_ATTRS.items()
        if v.get("typecast") is not None
    }

    # apply the typecast lambda to the value
    for k, v in attrs.items():
        if config.get(k) is not None:
            config[k] = v["typecast"](config[k])

    return config


@pytest.fixture(scope="session")
def process_shape(typecast):
    config = GHConfiguration(typecast)
    shape = config.get("shape")

    # TODO: keeping same logic here, but probably we should decide if an existing
    # TODO: shape_instance should be overriden here??
    if shape is not None:
        # instantiate the shape and add to the args
        shape_instance = Grasshopper.load_shape(shape_name=shape, **config)
        config["shape_instance"] = shape_instance

        # a shape is passed all the configuration args, in case it wants to make
        # decisions based on any of the values; in return the shape may override
        # configuration values based on its calculations, within reason
        # (must be in list of "approved" keys)

        # get the overrides from the shape_instance
        overrides = shape_instance.get_shape_overrides()

        # filter out any that are not "approved keys"
        overrides = {
            k: v
            for k, v in overrides.items()
            if k in ConfigurationConstants.SHAPE_OVERRIDE_ATTR_NAMES
        }

        # add the overrides
        config.update(overrides)
    else:
        logger.error(f"Shape is missing from configuration {config}")

    return config


@pytest.fixture(scope="session")
def complete_configuration(process_shape):
    config = GHConfiguration(process_shape)
    # TODO-DEPRECATED
    # Transfer the value from the deprecated arg to the new arg, so that we can
    # gracefully transfer use to the new arg
    # influxdb --> influx_host
    config.update_single_key("influx_host", config.get("influxdb"))

    return config


# -------------------------------- OTHER FIXTURES ------------------------------
@pytest.fixture(scope="function", autouse=True)
def do_scenario_delay(grasshopper_args):
    """Functionality to delay between each scenario run."""
    yield
    delay = grasshopper_args.get("scenario_delay")
    if delay and delay > 0:
        logger.info(f"Waiting for {delay} seconds between scenarios...")
        time.sleep(delay)
    else:
        logger.debug(f"Skipping delay of {delay} seconds between scenarios...")


# -------------------------------- YAML COLLECTION ------------------------------
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
        args = (
            [
                self.test_file_name,
                f"--scenario_file={self.scenario_file}",
                f"--scenario_name={self.scenario_name}",
            ]
            + [
                f"--{option_name}={self.config.getoption(option_name)}"
                for option_name in _fetch_args(
                    attr_names=ConfigurationConstants.COMPLETE_ATTRS.keys(),
                    config=self.config,
                )
            ]
            + [
                extra_arg
                for extra_arg in list(self.config.invocation_params.args)
                if "--" in extra_arg
            ]
        )  # pass down any other params that were supplied when invoking pytest

        # remove log-file args to avoid each test overwriting it
        args = [arg for arg in args if not arg.startswith("--log-file")]
        pytest.main(args)

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


# ------------------------------------- HELPERS ------------------------------------
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


def fetch_value_from_multiple_sources(sources, key):
    """Calculate a value from the given sources, using the list order as precedence.

    Used by the pre-proccess fixture to fetch a few values that we need in order to do
    the entire merge of values.

    """
    value = None
    for source in sources:
        value = value or source.get(key)
    return value
