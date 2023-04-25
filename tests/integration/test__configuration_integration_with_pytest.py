from unittest.mock import MagicMock

import pytest


@pytest.fixture
def environment():
    return MagicMock()


def test_all_the_args(
    environment,
    global_defaults,
    grasshopper_config_file_args,
    cmdln_args,
    env_var_args,
    complete_configuration,
    pre_processed_args,
    scenario_file_args,
):
    print(f"GLOBAL DEFAULTS: {global_defaults}")
    print(f"GLOBAL CONFIG FILE: {grasshopper_config_file_args}")
    print(f"CMDLINE ARGS: {cmdln_args}")
    print(f"ENV VAR ARGS: {env_var_args}")
    print(f"PRE-PROCESSED ARGS: {pre_processed_args}")
    print(f"SCENARIO_FILE_ARGS: {scenario_file_args}")
    print(f"COMPLETE NEW: {complete_configuration}")
