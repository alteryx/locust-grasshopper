"""Contents of the locust_grasshopper plugin which gets automatically loaded."""
import atexit
import importlib
import logging
import os
import pathlib
import shutil
import time
import uuid

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
    logger.debug(f"CONFIG FIXTURE: global_defaults {config}")
    return config


@pytest.fixture(scope="session")
def grasshopper_config_file_args(request):
    config = GHConfiguration()
    try:
        # TODO: should move yaml read to it's own method
        path = request.getfixturevalue("grasshopper_config_file_path")
        with open(path, "r") as stream:
            raw = yaml.safe_load(stream)

        # transfer each section to GHConfiguration object, any other sections ignored
        # TODO: should we load any other sections?
        global_vals = raw.get("grasshopper", {})
        config.update(**global_vals)
        test_run_vals = raw.get("test_run", {})
        config.update(**test_run_vals)
        scenario_vals = raw.get("scenario", {})
        config.update(**scenario_vals)

    except pytest.FixtureLookupError:
        logger.warning(
            "CONFIG FIXTURE: Skipping loading from grasshopper configuration file "
            "because fixture 'grasshopper_config_file_path` not found. You can safely "
            "ignore this warning if you were not intending to use a grasshopper "
            "configuration file."
        )
    except FileNotFoundError:
        logger.warning(
            f"CONFIG FIXTURE: Skipping loading from grasshopper configuration file "
            f"because {path} not found."
        )
    except (yaml.YAMLError, AttributeError) as e:
        logger.warning(
            f"CONFIG FIXTURE: Unable to parse yaml file {path} with error " f"{e}."
        )

    logger.debug(f"CONFIG FIXTURE: grasshopper_config_file {config}")
    return config


@pytest.fixture(scope="session")
def env_var_prefix_key(request):
    prefix = "GH_"
    try:
        prefix = request.getfixturevalue("configuration_prefix_key")
        if type(prefix) != str or (type(prefix) == str and len(prefix) == 0):
            logger.warning(
                f"CONFIG FIXTURE: Fixture configuration_prefix_key may only be a non "
                f"zero length str, returned value {prefix}, ignoring value."
            )
            prefix = "GH_"
    except pytest.FixtureLookupError:
        pass

    logger.debug(f"CONFIG FIXTURE: env_var_prefix_key {prefix}")
    return prefix


@pytest.fixture(scope="session")
def extra_env_var_keys(request):
    keys = []
    try:
        keys = request.getfixturevalue("configuration_extra_env_var_keys")
        # only allow a list of strings for env_var_keys
        if not type_check_list_of_strs(keys):
            logger.warning(
                f"CONFIG FIXTURE: Fixture configuration_extra_env_var_keys may only "
                f"return a list of strings, returned value {keys}, ignoring value."
            )
            keys = []
    except pytest.FixtureLookupError:
        pass

    logger.debug(f"CONFIG FIXTURE: extra_env_var_keys {keys}")
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
                env_var_name = env_var_name.replace(env_var_prefix_key, "")

            if len(env_var_name) > 0:
                config.update_single_key(env_var_name.lower(), env_var_value)

    logger.debug(f"CONFIG FIXTURE: env_var_args {config}")

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

    logger.debug(f"CONFIG FIXTURE: cmdln_args {config}")

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
        pre_config.update_single_key("scenario_file", scenario_file)

        scenario_name = fetch_value_from_multiple_sources(
            [cmdln_args, env_var_args, grasshopper_config_file_args, global_defaults],
            "scenario_name",
        )
        pre_config.update_single_key("scenario_name", scenario_name)

    except Exception as e:
        logger.error(
            f"CONFIG_FIXTURE: Uncaught exception in pre_processed_args fixture: "
            f"{type(e).__name__} | {e}"
        )

    logger.debug(f"CONFIG FIXTURE: pre_processed_args {pre_config}")
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
                f"CONFIG FIXTURE: Unexpected error loading scenario {scenario_name} "
                f"from {scenario_file}: {type(e).__name__} | {e}"
            )

    logger.debug(f"CONFIG FIXTURE: scenario_file_args {config}")

    return config


@pytest.fixture(scope="session")
def merge_sources(
    global_defaults,
    grasshopper_config_file_args,
    scenario_file_args,
    env_var_args,
    cmdln_args,
):
    config = GHConfiguration()

    # order matters here, this is determining the variable precedence
    try:
        config.update(global_defaults)
        config.update(grasshopper_config_file_args)
        config.update(scenario_file_args)
        config.update(env_var_args)
        config.update(cmdln_args)
    except Exception as e:
        logger.error(
            f"CONFIG FIXTURE: Unexpected error in merge_sources: "
            f"{type(e).__name__} | {e}"
        )
        pass

    logger.debug(f"CONFIG FIXTURE: env_var_args {config}")

    return config


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

    logger.debug(f"CONFIG FIXTURE: typecast {config}")

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
        logger.error(f"CONFIG FIXTURE: Shape is missing from configuration {config}")

    logger.debug(f"CONFIG FIXTURE: process_shape {config}")

    return config


@pytest.fixture(scope="session")
def complete_configuration(process_shape):
    config = GHConfiguration(process_shape)
    # TODO-DEPRECATED: Transfer the value from the deprecated arg to the new arg,
    # TODO: so that we can gracefully transfer use to the new arg
    # influxdb --> influx_host
    config.update_single_key("influx_host", config.get("influxdb"))

    logger.debug(f"CONFIG FIXTURE: complete_configuration {config}")

    return config


@pytest.fixture(scope="session")
def composite_weighted_user_classes():
    return YamlScenarioFile.composite_weighted_user_classes


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

    composite_weighted_user_classes = {}
    full_scenarios_list = []

    temp_gh_file = None

    # ^If a composite scenario is run, this will be the path to
    # the temp file. This file will be deleted after the test run via
    # the `cleanup_temp_file` fixture

    def collect(self):
        """Collect the file, knowing the path via self.fspath."""
        atexit.register(self._cleanup_temp_file)
        self.full_scenarios_list = yaml.safe_load(self.fspath.open())
        valid_scenarios = self._get_valid_scenarios(self.full_scenarios_list)
        for scenario_name, scenario_contents in valid_scenarios.items():
            yield self._create_scenario(scenario_name, scenario_contents)

    def _get_valid_scenarios(self, full_scenarios_list):
        """Filter and return valid scenarios."""
        valid_scenarios = _get_tagged_scenarios(
            full_scenarios_list=full_scenarios_list,
            config=self.config,
            fspath=self.fspath,
        )  # tag filter

        return valid_scenarios

    def _create_scenario(self, scenario_name, scenario_contents):
        """Create and yield a scenario based on scenario_contents."""
        test_file_name = scenario_contents.get("test_file_name")
        child_scenarios = scenario_contents.get("child_scenarios")

        if test_file_name:
            return Scenario.from_parent(
                self, name=scenario_name, spec=scenario_contents
            )
        elif child_scenarios:
            return self._create_composite_scenario(scenario_name, scenario_contents)
        else:
            raise AttributeError(
                f"The YAML scenario `{scenario_name}` "
                f"needs to specify either `test_file_name` or `child_scenarios`"
            )

    def _create_composite_scenario(self, scenario_name, scenario_contents):
        """Create and yield a composite scenario."""
        parent_path = pathlib.Path(__file__).parent.resolve()
        YamlScenarioFile.composite_weighted_user_classes = (
            _get_composite_weighted_user_classes(
                self.full_scenarios_list, scenario_contents
            )
        )

        source_gh_file_path = f"{parent_path}/../journeys/temp_gh_composite.py"
        YamlScenarioFile.temp_gh_file = f"{os.getcwd()}/temp_gh_composite.py"

        shutil.copy2(
            source_gh_file_path,
            YamlScenarioFile.temp_gh_file,
        )
        composite_scenario_spec = {"test_file_name": YamlScenarioFile.temp_gh_file}

        return Scenario.from_parent(
            self, name=scenario_name, spec=composite_scenario_spec
        )

    def _cleanup_temp_file(self):
        """Clean up the temp file."""
        if self.temp_gh_file and os.path.exists(self.temp_gh_file):
            logger.debug(f"Cleaning up temp file {self.temp_gh_file}")
            os.remove(self.temp_gh_file)


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
        # remove error message skipping args which is sometimes passed in by the ide
        ignore_args = ["--log-file", "--no-header", "--no-summary"]
        args = [
            arg
            for arg in args
            if not any([arg.startswith(ignore_arg) for ignore_arg in ignore_args])
        ]
        exit_code = pytest.main(args)
        assert exit_code == pytest.ExitCode.OK

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


def _get_tagged_scenarios(full_scenarios_list, config, fspath) -> dict:
    valid_scenarios = {}
    tags_to_query_for = config.getoption("--tags") or os.getenv("TAGS")
    if tags_to_query_for:
        for scenario_name, scenario_contents in full_scenarios_list.items():
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
            if tagmatcher.match(query_str=tags_to_query_for, tags=tags_list):
                valid_scenarios[scenario_name] = scenario_contents
        logging.info(
            f"Scenarios collected that match the specific tag query `"
            f"{tags_to_query_for}`: "
            f"{[scenario_name for scenario_name in valid_scenarios.keys()]}"
        )
    else:
        logging.warning(
            f"Since no tags param was specified, ALL scenarios in "
            f"{fspath} will be run!"
        )
        valid_scenarios = full_scenarios_list

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


def type_check_list_of_strs(list_of_strs):
    """Return True if list of strings or [], false if anything else."""
    check_passed = False
    if type(list_of_strs) == list:
        all_strs = True
        for s in list_of_strs:
            all_strs = all_strs and type(s) == str
        check_passed = all_strs
    return check_passed


def _get_composite_weighted_user_classes(
    full_scenarios_list, composite_scenario_contents
):
    """Generate a dictionary of journey classes with their associated weights."""
    weighted_user_classes = {}
    child_scenario_specs = _get_child_scenario_specs(
        full_scenarios_list, composite_scenario_contents
    )
    for child_scenario_spec in child_scenario_specs:
        file_dir = os.getcwd()
        test_file_name = child_scenario_spec.get("test_file_name")
        test_file_path = os.path.join(file_dir, test_file_name)
        base_journey_class = _import_class_with_journey(
            absolute_file_path=test_file_path
        )
        base_class_name = base_journey_class.__name__
        composite_class_name = (
            f"composite_journey_class_{base_class_name}_{uuid.uuid4()}"
        )

        # dynamically create a child class which inherits from the base class,
        # required for having separate scenario args
        child_journey_class = type(
            composite_class_name,
            (base_journey_class,),
            {
                "_incoming_test_parameters": child_scenario_spec.get(
                    "grasshopper_scenario_args"
                )
            },
        )
        weighted_user_classes[child_journey_class] = child_scenario_spec.get("weight")
    return weighted_user_classes


def _import_class_with_journey(absolute_file_path):
    """Import and return a class with 'journey' in its name from a module file."""
    module_name = os.path.splitext(absolute_file_path)[0]
    spec = importlib.util.spec_from_file_location(module_name, absolute_file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Now, inspect the module's attributes to find the class with "journey" in
    # its name
    for name, obj in vars(module).items():
        if (
            isinstance(obj, type)
            and "journey" in name.lower()
            and "base" not in name.lower()
        ):
            return obj

    # If no class with "journey" in its name is found, return None
    logger.error("Import error: No class with 'journey' in its name found.")
    return None


def _get_child_scenario_specs(full_scenarios_list, composite_scenario_contents):
    """Extract and prepare child scenario specs given composite scenario contents."""
    child_scenarios = composite_scenario_contents.get("child_scenarios")
    child_scenario_specs = []
    for child_scenario in child_scenarios:
        child_scenario_name = child_scenario.get("scenario_name")
        child_scenario_overrides = child_scenario.get(
            "grasshopper_scenario_arg_overrides", {}
        )
        child_scenario_spec = full_scenarios_list.get(child_scenario_name)
        if child_scenario_spec is None:
            raise YamlError(
                f"Child scenario `{child_scenario_name}` not found in "
                f"the specified YAML scenario file."
            )
        _check_for_recursion(child_scenario_name, child_scenario_spec)
        child_scenario_spec.setdefault("grasshopper_scenario_args", {}).update(
            child_scenario_overrides
        )
        child_scenario_spec["weight"] = child_scenario.get("weight", 1)
        child_scenario_specs.append(child_scenario_spec)
    return child_scenario_specs


def _check_for_recursion(child_scenario_name, child_scenario_spec):
    if child_scenario_spec.get("child_scenarios"):
        raise YamlError(
            f"Child scenario `{child_scenario_name}` "
            f"cannot have child scenarios. Recursive child scenarios are not "
            f"supported at this time."
        )
