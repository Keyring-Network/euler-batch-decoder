"""Test the __main__ module."""

from __future__ import annotations

import subprocess
import sys


def test_main_module_execution():
    """Test that the main module can be executed."""
    # Test running the module with --help
    result = subprocess.run([sys.executable, "-m", "evc_batch_decoder", "--help"], capture_output=True, text=True)  # noqa: S603

    assert result.returncode == 0
    assert "Decode EVC batch transaction data" in result.stdout
