import pytest
from assertpy import assert_that
from grasshopper.lib.reporting.shared_reporting import SharedReporting


@pytest.fixture(scope="session")
def fake_passing_threshold():
    threshold = {
        "less_than_in_ms": 1000,
        "actual_value_in_ms": 800,
        "percentile": 0.8,
        "succeeded": True,
        "http_method": "GET",
    }
    return threshold


@pytest.fixture(scope="session")
def fake_failing_threshold():
    threshold = {
        "less_than_in_ms": 1000,
        "actual_value_in_ms": 1200,
        "percentile": 0.8,
        "succeeded": False,
        "http_method": "POST",
    }
    return threshold


@pytest.fixture(scope="session")
def fake_thresholds_single(fake_passing_threshold):
    thresholds = [fake_passing_threshold]
    return thresholds


@pytest.fixture(scope="session")
def fake_thresholds_multiple(fake_passing_threshold, fake_failing_threshold):
    thresholds = [fake_passing_threshold, fake_failing_threshold]
    return thresholds


@pytest.fixture(scope="session")
def fake_trends_single_threshold(fake_thresholds_single):
    trends = {"fake trend": {"thresholds": fake_thresholds_single}}
    return trends


@pytest.fixture(scope="session")
def fake_trends_multiple_thresholds(fake_thresholds_multiple):
    trends = {"fake trend": {"thresholds": fake_thresholds_multiple}}
    return trends


@pytest.fixture(scope="session")
def fake_trends_multiple_trends(fake_thresholds_multiple):
    trends = {
        "fake trend 1": {"thresholds": fake_thresholds_multiple},
        "fake trend 2": {"thresholds": fake_thresholds_multiple},
    }
    return trends


@pytest.fixture(scope="session")
def fake_trends_no_thresholds(fake_thresholds_multiple):
    trends = {
        "fake trend 1": {},
        "fake trend 2": {},
    }
    return trends


def test__plain_threshold_string_happy(fake_passing_threshold):
    expected_string = "fake passing trend             80         1000ms     800ms     "
    threshold_string, _ = SharedReporting.plain_threshold_string(
        "fake passing trend", fake_passing_threshold
    )
    assert_that(threshold_string).is_equal_to(expected_string)


def test__plain_threshold_string_custom_format_str(fake_passing_threshold):
    expected_string = "fake passing trend | 80 | 1000ms | 800ms"
    format_string = "{} | {} | {} | {}"
    threshold_string, _ = SharedReporting.plain_threshold_string(
        "fake passing trend", fake_passing_threshold, format_string=format_string
    )
    assert_that(threshold_string).is_equal_to(expected_string)


def test__plain_threshold_string_invalid_threshold():
    expected_string = (
        "UNABLE TO PROCESS THRESHOLD FOR TREND <fake trend>: KeyError | 'percentile'"
    )
    threshold_string, _ = SharedReporting.plain_threshold_string("fake trend", {})
    assert_that(threshold_string).is_equal_to(expected_string)


def test__plain_threshold_string_trend_name_is_none(fake_passing_threshold):
    expected_string = (
        "UNABLE TO PROCESS THRESHOLD FOR TREND <None>: TypeError | "
        "unsupported format string passed to NoneType.__format__"
    )
    threshold_string, _ = SharedReporting.plain_threshold_string(
        None, fake_passing_threshold
    )
    assert_that(threshold_string).is_equal_to(expected_string)


def test__colorized_threshold_string_happy(fake_passing_threshold):
    expected_string = (
        "\x1b[1m\x1b[32mfake trend                     80         "
        "1000ms     800ms     \x1b[0m"
    )
    threshold_string, _ = SharedReporting.colorized_threshold_string(
        "fake trend", fake_passing_threshold
    )
    assert_that(threshold_string).is_equal_to(expected_string)


def test__colorized_threshold_string_failed(fake_failing_threshold):
    expected_string = (
        "\x1b[1m\x1b[31mfake trend                     80         "
        "1000ms     1200ms    \x1b[0m"
    )
    threshold_string, _ = SharedReporting.colorized_threshold_string(
        "fake trend", fake_failing_threshold
    )
    assert_that(threshold_string).is_equal_to(expected_string)


def test__colorized_threshold_string_invalid_threshold():
    expected_string = (
        "\x1b[1m\x1b[31mUNABLE TO PROCESS THRESHOLD FOR TREND <fake trend>: "
        "TypeError | 'NoneType' object is not subscriptable\x1b[0m"
    )
    threshold_string, _ = SharedReporting.colorized_threshold_string("fake trend", None)
    assert_that(threshold_string).is_equal_to(expected_string)


def test__colorized_threshold_string_empty_threshold():
    expected_string = (
        "\x1b[1m\x1b[31mUNABLE TO PROCESS THRESHOLD FOR TREND <fake trend>: "
        "KeyError | 'percentile'\x1b[0m"
    )
    threshold_string, _ = SharedReporting.colorized_threshold_string("fake trend", {})
    assert_that(threshold_string).is_equal_to(expected_string)


def test__colorized_threshold_trend_name_is_none(fake_passing_threshold):
    expected_string = (
        "\x1b[1m\x1b[31mUNABLE TO PROCESS THRESHOLD FOR TREND <None>: "
        "TypeError | unsupported format string passed to NoneType.__format__\x1b[0m"
    )
    threshold_string, _ = SharedReporting.colorized_threshold_string(
        None, fake_passing_threshold
    )
    assert_that(threshold_string).is_equal_to(expected_string)


def test__calculate_threshold_lines_happy(fake_trends_single_threshold):
    expected_line = "fake trend                     80         1000ms     800ms     "
    lines = SharedReporting.calculate_threshold_lines(fake_trends_single_threshold)
    assert_that(lines).is_type_of(list)
    assert_that(lines).contains(expected_line)


def test__calculate_threshold_lines_multiple_thresholds(
    fake_trends_multiple_thresholds,
):
    expected_line_1 = "fake trend                     80         1000ms     800ms     "
    expected_line_2 = "fake trend                     80         1000ms     1200ms    "
    lines = SharedReporting.calculate_threshold_lines(fake_trends_multiple_thresholds)
    assert_that(lines).is_type_of(list)
    assert_that(lines).contains(expected_line_1)
    assert_that(lines).contains(expected_line_2)


def test__calculate_threshold_lines_multiple_trends(fake_trends_multiple_trends):
    expected_line_1 = "fake trend 1                   80         1000ms     800ms     "
    expected_line_2 = "fake trend 1                   80         1000ms     1200ms    "
    expected_line_3 = "fake trend 2                   80         1000ms     800ms     "
    expected_line_4 = "fake trend 2                   80         1000ms     1200ms    "
    lines = SharedReporting.calculate_threshold_lines(fake_trends_multiple_trends)
    assert_that(lines).is_type_of(list)
    assert_that(lines).contains(expected_line_1)
    assert_that(lines).contains(expected_line_2)
    assert_that(lines).contains(expected_line_3)
    assert_that(lines).contains(expected_line_4)


def test__calculate_threshold_lines_custom_format_str(fake_trends_multiple_trends):
    expected_line_1 = "fake trend 1 | 80 | 1000ms | 800ms"
    expected_line_2 = "fake trend 1 | 80 | 1000ms | 1200ms"
    expected_line_3 = "fake trend 2 | 80 | 1000ms | 800ms"
    expected_line_4 = "fake trend 2 | 80 | 1000ms | 1200ms"
    format_string = "{} | {} | {} | {}"
    lines = SharedReporting.calculate_threshold_lines(
        fake_trends_multiple_trends, format_string=format_string
    )
    assert_that(lines).is_type_of(list)
    assert_that(lines).contains(expected_line_1)
    assert_that(lines).contains(expected_line_2)
    assert_that(lines).contains(expected_line_3)
    assert_that(lines).contains(expected_line_4)


def test__calculate_threshold_lines_custom_formatter(fake_trends_multiple_trends):
    expected_line_1 = (
        "\x1b[1m\x1b[32mfake trend 1                   80         1000ms     "
        "800ms     \x1b[0m"
    )
    expected_line_2 = (
        "\x1b[1m\x1b[31mfake trend 1                   80         1000ms     "
        "1200ms    \x1b[0m"
    )
    expected_line_3 = (
        "\x1b[1m\x1b[32mfake trend 2                   80         1000ms     "
        "800ms     \x1b[0m"
    )
    expected_line_4 = (
        "\x1b[1m\x1b[31mfake trend 2                   80         1000ms     "
        "1200ms    \x1b[0m"
    )
    lines = SharedReporting.calculate_threshold_lines(
        fake_trends_multiple_trends,
        formatter=SharedReporting.colorized_threshold_string,
    )
    assert_that(lines).is_type_of(list)
    assert_that(lines).contains(expected_line_1)
    assert_that(lines).contains(expected_line_2)
    assert_that(lines).contains(expected_line_3)
    assert_that(lines).contains(expected_line_4)


def test__calculate_threshold_lines_empty_trends():
    lines = SharedReporting.calculate_threshold_lines({})
    assert_that(lines).is_type_of(list)
    assert_that(lines).is_empty()


def test__calculate_threshold_lines_no_thresholds(fake_trends_no_thresholds):
    lines = SharedReporting.calculate_threshold_lines(fake_trends_no_thresholds)
    assert_that(lines).is_type_of(list)
    assert_that(lines).is_empty()


def test__calculate_threshold_lines_none():
    lines = SharedReporting.calculate_threshold_lines(None)
    assert_that(lines).is_type_of(list)
    assert_that(lines).is_empty()
