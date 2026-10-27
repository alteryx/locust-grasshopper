"""Exercise report colors through pytest's real file-descriptor capture."""

import errno
import os
import pty
import re
import select
import subprocess
import sys
import time
from pathlib import Path

import pytest


def _run_in_terminal(command: list[str], cwd: Path, env: dict[str, str]) -> str:
    master, slave = pty.openpty()
    try:
        process = subprocess.Popen(
            command, cwd=cwd, env=env, stdout=slave, stderr=slave
        )
    finally:
        os.close(slave)
    try:
        chunks = []
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.1)
            if not ready:
                if process.poll() is not None:
                    break
                continue
            try:
                chunk = os.read(master, 65536)
            except OSError as error:
                if error.errno != errno.EIO:
                    raise
                break
            if not chunk:
                break
            chunks.append(chunk)
        else:
            pytest.fail("pytest terminal subprocess timed out")
        output = b"".join(chunks).decode()
        assert process.wait(timeout=5) == 0, output
        return output
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        os.close(master)


@pytest.mark.parametrize(
    "terminal,color_env,colored",
    [
        (True, {}, True),
        (False, {}, False),
        (True, {"NO_COLOR": "1"}, False),
        (False, {"FORCE_COLOR": "1"}, True),
    ],
)
def test_live_report_colors_with_fd_capture(
    pytester: pytest.Pytester, terminal: bool, color_env: dict[str, str], colored: bool
) -> None:
    pytester.makeini("""
        [pytest]
        addopts = -p locust_grasshopper
        log_cli = true
        log_cli_level = INFO
    """)
    pytester.makepyfile("""
        from grasshopper.lib.util.check_constants import CheckConstants
        from grasshopper.lib.util.utils import report_checks_to_console, report_thresholds_to_console

        def test_reports():
            report_thresholds_to_console({"latency probe": {"thresholds": [{
                "http_method": "GET", "percentile": 0.95, "less_than_in_ms": 500,
                "actual_value_in_ms": 20, "succeeded": True,
            }]}})
            report_checks_to_console({
                name: {"passed": 1, "failed": 0, "total": 1,
                       "percentage_passed_display": 100.0, "verdict": verdict}
                for name, verdict in [
                    ("literal [red] name", CheckConstants.VERDICT_ALL_PASSED),
                    ("failed probe", CheckConstants.VERDICT_FAILED),
                    ("warning probe", CheckConstants.VERDICT_PASSED_RATE_OVER_THRESHOLD),
                ]
            })
    """)
    env = os.environ.copy()
    for key in (
        "NO_COLOR",
        "FORCE_COLOR",
        "PY_COLORS",
        "PYTHON_COLORS",
        "TTY_COMPATIBLE",
        "TTY_INTERACTIVE",
        "PYTEST_ADDOPTS",
    ):
        env.pop(key, None)
    env.update(TERM="xterm-256color", COLORTERM="truecolor", TERM_PROGRAM="vscode")
    env.update(color_env)
    command = [sys.executable, "-m", "pytest", "--capture=fd", "--log-file=run.log"]
    if terminal:
        output = _run_in_terminal(command, pytester.path, env)
    else:
        result = subprocess.run(
            command,
            cwd=pytester.path,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        output = result.stdout

    for name, color, verdict in [
        ("latency probe", 32, "PASS"),
        ("literal [red] name", 32, "PASS"),
        ("failed probe", 31, "FAIL"),
        ("warning probe", 33, "WARN"),
    ]:
        row = next(line for line in output.splitlines() if name in line)
        assert bool(re.search(rf"\x1b\[[\d;]*{color}m{verdict}", row)) is colored
    if not color_env:
        assert "\x1b[" not in (pytester.path / "run.log").read_text()
