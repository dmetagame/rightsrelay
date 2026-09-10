import subprocess
from pathlib import Path


def test_browser_cannot_keep_green_clearance_after_status_connection_fails():
    result = subprocess.run(["node", str(Path(__file__).with_name("console_browser.cjs"))],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
