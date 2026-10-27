def test_plain_pytest_initializes_gevent_before_network_plugins(pytester):
    """Loading an HTTP plugin must not break Locust's SSL initialization."""
    pytester.makeini(
        """
        [pytest]
        addopts = -p locust_grasshopper
        """
    )
    pytester.makepyfile(
        """
        from grasshopper.lib.grasshopper import Grasshopper
        from urllib3.util.ssl_ import create_urllib3_context

        def test_https_setup():
            create_urllib3_context()
        """
    )

    result = pytester.runpytest_subprocess(
        "-p", "requests_mock", "-W", "error::gevent.monkey.MonkeyPatchWarning"
    )
    result.assert_outcomes(passed=1)
