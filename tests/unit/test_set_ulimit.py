from unittest.mock import MagicMock, patch

from grasshopper.lib.grasshopper import Grasshopper


def test_set_ulimit_non_posix():
    """Verify that on non-posix systems, set_ulimit is a no-op."""
    with (
        patch("grasshopper.lib.grasshopper.os.name", "nt"),
        patch("grasshopper.lib.grasshopper.logger") as mock_logger,
    ):
        # If it's nt, resource shouldn't be accessed and no posix actions run.
        Grasshopper.set_ulimit()
        mock_logger.info.assert_any_call(
            "Can't modify open file limits on non-POSIX systems. Skipping ulimit adjustment."
        )


def test_set_ulimit_already_high():
    """Verify that when limits are already high, no changes are attempted."""
    mock_resource = MagicMock()
    mock_resource.RLIMIT_NOFILE = 8  # or any dummy constant

    # Simulate high initial limits (already above 10000)
    limits = [15000, 20000]
    mock_resource.getrlimit.side_effect = lambda limit_type: tuple(limits)

    with (
        patch("grasshopper.lib.grasshopper.os.name", "posix"),
        patch("grasshopper.lib.grasshopper.resource", mock_resource),
        patch("grasshopper.lib.grasshopper.logger") as mock_logger,
    ):
        Grasshopper.set_ulimit()

        mock_resource.getrlimit.assert_called_with(mock_resource.RLIMIT_NOFILE)
        mock_resource.setrlimit.assert_not_called()
        mock_logger.info.assert_any_call(
            "Current open files limits - soft: 15000, hard: 20000"
        )
        mock_logger.info.assert_any_call(
            "Hard limit of 20000 is in line with minimum required limit of 10000"
        )
        mock_logger.info.assert_any_call(
            "Soft limit of 15000 is in line with minimum required limit of 10000"
        )


def test_set_ulimit_increase_both_success():
    """Verify that both hard and soft limits are increased if both are below minimum."""
    mock_resource = MagicMock()
    mock_resource.RLIMIT_NOFILE = 8

    # State representation of system open file limits [soft, hard]
    limits = [2000, 5000]

    def getrlimit_mock(limit_type):
        return tuple(limits)

    def setrlimit_mock(limit_type, new_limits):
        limits[0] = new_limits[0]
        limits[1] = new_limits[1]

    mock_resource.getrlimit.side_effect = getrlimit_mock
    mock_resource.setrlimit.side_effect = setrlimit_mock

    with (
        patch("grasshopper.lib.grasshopper.os.name", "posix"),
        patch("grasshopper.lib.grasshopper.resource", mock_resource),
        patch("grasshopper.lib.grasshopper.logger") as mock_logger,
    ):
        Grasshopper.set_ulimit()
        mock_logger.info.assert_any_call(
            "Current open files limits - soft: 2000, hard: 5000"
        )

        # Successful hard limit increase
        mock_resource.setrlimit.assert_any_call(
            mock_resource.RLIMIT_NOFILE, (2000, 10000)
        )
        mock_logger.info.assert_any_call("Open files hard limit increased to 10000")

        # Successful soft limit increase
        mock_resource.setrlimit.assert_any_call(
            mock_resource.RLIMIT_NOFILE, (10000, 10000)
        )
        mock_logger.info.assert_any_call("Open files soft limit increased to 10000")

        mock_logger.warning.assert_not_called()


def test_set_ulimit_hard_fails_soft_success():
    """Verify that if hard limit increase fails, soft limit still attempts to increase up to hard limit."""
    mock_resource = MagicMock()
    mock_resource.RLIMIT_NOFILE = 8

    initial_limits = [2000, 5000]

    def getrlimit_mock(limit_type):
        return tuple(initial_limits)

    def setrlimit_mock(limit_type, new_limits):
        if new_limits[1] == 10000:  # trying to increase hard limit to 10000
            raise PermissionError("Not permitted")
        # Soft limit increase to 5000 should succeed
        initial_limits[0] = new_limits[0]
        initial_limits[1] = new_limits[1]

    mock_resource.getrlimit.side_effect = getrlimit_mock
    mock_resource.setrlimit.side_effect = setrlimit_mock

    with (
        patch("grasshopper.lib.grasshopper.os.name", "posix"),
        patch("grasshopper.lib.grasshopper.resource", mock_resource),
        patch("grasshopper.lib.grasshopper.logger") as mock_logger,
    ):
        Grasshopper.set_ulimit()

        # It should try to set hard limit to (2000, 10000) -> fails
        mock_resource.setrlimit.assert_any_call(
            mock_resource.RLIMIT_NOFILE, (2000, 10000)
        )
        mock_logger.warning.assert_any_call(
            "Could not increase hard limit directly: Not permitted"
        )
        # It should then try to set soft limit to (10000, 5000) -> succeeds (hard limit should remain original 5000 since it failed to increase)
        mock_resource.setrlimit.assert_any_call(
            mock_resource.RLIMIT_NOFILE, (10000, 5000)
        )
        mock_logger.info.assert_any_call("Open files soft limit increased to 10000")

        mock_logger.info.assert_any_call(
            "Final open files limits - soft: 10000, hard: 5000"
        )


def test_set_ulimit_hard_success_soft_fails():
    """Verify that a warning is logged if the hard limit is successfully increased but soft limit fails to increase."""
    mock_resource = MagicMock()
    mock_resource.RLIMIT_NOFILE = 8

    # State tracking of limits [soft, hard]
    limits = [2000, 5000]

    def getrlimit_mock(limit_type):
        return tuple(limits)

    def setrlimit_mock(limit_type, new_limits):
        # If trying to set soft limit to 10000, raise exception
        if new_limits[0] == 10000:
            raise PermissionError("Soft limit adjustment denied")
        # Otherwise hard limit succeeds
        limits[0] = new_limits[0]
        limits[1] = new_limits[1]

    mock_resource.getrlimit.side_effect = getrlimit_mock
    mock_resource.setrlimit.side_effect = setrlimit_mock

    with (
        patch("grasshopper.lib.grasshopper.os.name", "posix"),
        patch("grasshopper.lib.grasshopper.resource", mock_resource),
        patch("grasshopper.lib.grasshopper.logger") as mock_logger,
    ):
        Grasshopper.set_ulimit()

        # Info log before changes
        mock_logger.info.assert_any_call(
            "Current open files limits - soft: 2000, hard: 5000"
        )
        # Successful hard limit increase
        mock_resource.setrlimit.assert_any_call(
            mock_resource.RLIMIT_NOFILE, (2000, 10000)
        )
        mock_logger.info.assert_any_call("Open files hard limit increased to 10000")

        # Failed soft limit increase
        mock_resource.setrlimit.assert_any_call(
            mock_resource.RLIMIT_NOFILE, (10000, 10000)
        )
        mock_logger.warning.assert_any_call(
            "Could not increase soft limit directly: Soft limit adjustment denied"
        )

        mock_logger.info.assert_any_call(
            "Final open files limits - soft: 2000, hard: 10000"
        )

        # Verify warning log
        assert (
            "System open file limit '2000' is below minimum"
            in mock_logger.warning.call_args[0][0]
        )


def test_set_ulimit_outer_exception():
    """Verify that if getrlimit raises an exception, it is caught and logged gracefully."""
    mock_resource = MagicMock()
    mock_resource.RLIMIT_NOFILE = 8
    mock_resource.getrlimit.side_effect = OSError("System error")

    with (
        patch("grasshopper.lib.grasshopper.os.name", "posix"),
        patch("grasshopper.lib.grasshopper.resource", mock_resource),
        patch("grasshopper.lib.grasshopper.logger") as mock_logger,
    ):
        Grasshopper.set_ulimit()

        mock_logger.warning.assert_called_once()
        assert (
            "Failed to retrieve system open file limits:"
            in mock_logger.warning.call_args[0][0]
        )
