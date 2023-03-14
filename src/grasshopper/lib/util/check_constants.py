"""Module: Check Constants."""


class CheckConstants:
    """Check verdict constants."""

    VERDICT_ALL_PASSED = "VERDICT_ALL_PASSED"
    # not 100% passed, but the failure rate is under the threshold specified
    VERDICT_PASSED_RATE_OVER_THRESHOLD = "VERDICT_PASSED_RATE_OVER_THRESHOLD"
    VERDICT_FAILED = "VERDICT_FAILED"
