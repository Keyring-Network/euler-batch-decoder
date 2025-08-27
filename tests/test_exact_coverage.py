"""Exact tests to hit the final 4 lines for 100% coverage."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner


def test_cli_keyboard_interrupt_lines_116_117():
    """Hit lines 116-117: KeyboardInterrupt during sys.stdin.read()."""
    from evc_batch_decoder.cli import decode_batch

    runner = CliRunner()

    # Mock sys.stdin.read to raise KeyboardInterrupt - this will hit lines 116-117
    with patch("sys.stdin.read", side_effect=KeyboardInterrupt("Ctrl+C pressed")):
        result = runner.invoke(decode_batch, [])  # No arguments to force stdin path

        # Should hit lines 116-117 in the KeyboardInterrupt except block
        assert result.exit_code == 1
        assert "No batch data provided" in result.output


def test_cli_empty_input_lines_120_121():
    """Hit lines 120-121: input_data remains empty after processing."""
    from evc_batch_decoder.cli import decode_batch

    runner = CliRunner()

    # Create scenario where input_data stays None/empty to hit lines 120-121
    # We need to bypass the stdin reading but still have empty input_data

    # Mock to simulate stdin returning data that gets processed but input_data remains empty
    with patch("sys.stdin.read", return_value="   "):  # Whitespace that becomes empty after strip()
        result = runner.invoke(decode_batch, [])

        # This should hit the final check at lines 120-121
        assert result.exit_code == 1
        assert "No batch data provided" in result.output


def test_cli_direct_keyboard_interrupt_scenario():
    """Direct KeyboardInterrupt simulation hitting exact lines."""
    from evc_batch_decoder.cli import decode_batch

    runner = CliRunner()

    # Multiple approaches to ensure we hit the KeyboardInterrupt path
    keyboard_interrupts = [
        KeyboardInterrupt(),
        KeyboardInterrupt("User interrupt"),
        KeyboardInterrupt("^C"),
    ]

    for interrupt in keyboard_interrupts:
        with patch("sys.stdin.read", side_effect=interrupt):
            result = runner.invoke(decode_batch, [])
            # Should hit lines 116-117
            assert result.exit_code == 1
            if "No batch data provided" in result.output:
                # Successfully hit the KeyboardInterrupt path
                break


def test_cli_empty_input_scenarios():
    """Test various empty input scenarios to hit lines 120-121."""
    from evc_batch_decoder.cli import decode_batch

    runner = CliRunner()

    # Scenarios that should result in empty input_data and hit lines 120-121
    empty_scenarios = [
        "",  # Completely empty
        " ",  # Single space (becomes empty after strip)
        "\n",  # Just newline (becomes empty after strip)
        "\t",  # Just tab (becomes empty after strip)
        "   \n\t   ",  # Mixed whitespace (becomes empty after strip)
    ]

    for scenario in empty_scenarios:
        with patch("sys.stdin.read", return_value=scenario):
            result = runner.invoke(decode_batch, [])
            # Should hit lines 120-121
            assert result.exit_code == 1
            if "No batch data provided" in result.output:
                # Successfully hit the empty input path
                continue


def test_force_exact_line_execution():
    """Force execution of the exact missing lines using precise mocks."""
    from evc_batch_decoder.cli import decode_batch

    runner = CliRunner()

    # Test 1: Force KeyboardInterrupt in stdin.read() to hit lines 116-117
    def raise_keyboard_interrupt():
        raise KeyboardInterrupt("Forced interrupt for coverage")

    with patch("sys.stdin.read", side_effect=raise_keyboard_interrupt):
        result = runner.invoke(decode_batch, [])
        # This MUST hit lines 116-117
        assert result.exit_code == 1

    # Test 2: Force empty input_data to hit lines 120-121
    # We need input_data to remain falsy after all processing
    with patch("sys.stdin.read", return_value=""):  # Empty string
        result = runner.invoke(decode_batch, [])
        # This MUST hit lines 120-121
        assert result.exit_code == 1
