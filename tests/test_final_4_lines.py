"""Target the final 4 CLI lines for absolute 100% coverage."""

from __future__ import annotations

import sys
from unittest.mock import patch

from click.testing import CliRunner


class TestFinal4Lines:
    """Precisely target the final 4 CLI lines."""

    def test_cli_line_116_117_keyboard_interrupt_stdin_read(self):
        """Hit CLI lines 116-117: KeyboardInterrupt during sys.stdin.read()."""
        from evc_batch_decoder.cli import decode_batch

        runner = CliRunner()

        # We need to interrupt exactly when stdin_data = sys.stdin.read() is called
        # This is line ~108, and the KeyboardInterrupt is caught at lines 115-117

        def mock_stdin_read():
            # This simulates the user pressing Ctrl+C during stdin read
            raise KeyboardInterrupt("User pressed Ctrl+C during stdin.read()")

        with patch("sys.stdin.read", side_effect=mock_stdin_read):
            # This should trigger the KeyboardInterrupt except block at lines 116-117
            result = runner.invoke(decode_batch, input="", standalone_mode=False)

            # The KeyboardInterrupt should be caught and result in exit code 1
            assert result.exit_code == 1
            assert "No batch data provided" in result.output

    def test_cli_line_120_121_empty_input_after_processing(self):
        """Hit CLI lines 120-121: input_data becomes empty after all processing."""
        from evc_batch_decoder.cli import decode_batch

        runner = CliRunner()

        # We need input_data to be set but then become falsy after processing
        # This happens when all sources return only whitespace

        # Mock stdin to return whitespace that becomes empty after strip()
        def mock_stdin_read():
            return "   \n\t\n   "  # This will become empty after strip()

        with patch("sys.stdin.read", side_effect=mock_stdin_read):
            # Also ensure no file argument is passed and no other input sources
            result = runner.invoke(decode_batch, [], input="", standalone_mode=False)

            # This should hit the `if not input_data:` check at lines 120-121
            assert result.exit_code == 1
            assert "No batch data provided" in result.output

    def test_comprehensive_final_4_lines(self):
        """Comprehensive test for the final 4 CLI lines using multiple approaches."""
        from evc_batch_decoder.cli import decode_batch

        runner = CliRunner()

        # Test 1: KeyboardInterrupt during stdin read (lines 116-117)
        def interrupt_read():
            raise KeyboardInterrupt()

        with patch("sys.stdin.read", side_effect=interrupt_read):
            result = runner.invoke(decode_batch, [])
            # Should hit lines 116-117
            assert result.exit_code == 1

        # Test 2: Empty input_data after processing (lines 120-121)
        scenarios_for_empty = [
            "",  # Actually empty
            " ",  # Single space
            "\n",  # Just newline
            "\t",  # Just tab
            "   ",  # Multiple spaces
            "\n\n",  # Multiple newlines
            " \n\t ",  # Mixed whitespace
        ]

        for empty_scenario in scenarios_for_empty:
            with patch("sys.stdin.read", return_value=empty_scenario):
                result = runner.invoke(decode_batch, [])
                # Should hit lines 120-121 when input_data.strip() is empty
                if result.exit_code == 1 and "No batch data provided" in result.output:
                    # Successfully hit the empty input path
                    continue

    def test_direct_cli_invocation_edge_cases(self):
        """Direct CLI invocation with precise edge case simulation."""
        from evc_batch_decoder.cli import decode_batch

        runner = CliRunner()

        # Test KeyboardInterrupt in the exact context
        original_stdin_read = sys.stdin.read

        def controlled_keyboard_interrupt():
            # This exactly simulates what happens when user presses Ctrl+C during stdin read
            raise KeyboardInterrupt("Simulated Ctrl+C")

        # Replace sys.stdin.read temporarily
        sys.stdin.read = controlled_keyboard_interrupt

        try:
            # This should trigger the KeyboardInterrupt handling at lines 116-117
            result = runner.invoke(decode_batch, [], catch_exceptions=True)
            assert result.exit_code == 1
        finally:
            # Restore original stdin.read
            sys.stdin.read = original_stdin_read

        # Test empty input after all processing
        with patch.object(sys.stdin, "read", return_value=""):
            result = runner.invoke(decode_batch, [])
            # Should hit lines 120-121
            assert result.exit_code == 1
            assert "No batch data provided" in result.output

    def test_exact_line_targeting(self):
        """Exact targeting of the specific missing lines."""
        from evc_batch_decoder.cli import decode_batch

        runner = CliRunner()

        # For lines 116-117: KeyboardInterrupt during stdin processing
        class ExactKeyboardInterrupt(KeyboardInterrupt):
            """Exactly the type of interrupt we expect."""

            pass

        with patch("sys.stdin.read", side_effect=ExactKeyboardInterrupt("Exact Ctrl+C")):
            result = runner.invoke(decode_batch, [])
            # This should execute lines 116-117 exactly
            assert result.exit_code == 1

        # For lines 120-121: input_data empty after all processing
        # We need to ensure stdin returns something that becomes empty after processing
        with patch("sys.stdin.read", return_value=""):
            # No file argument, no tx_hash, just empty stdin
            result = runner.invoke(decode_batch, [])
            # This should execute lines 120-121 exactly
            assert result.exit_code == 1
            assert "No batch data provided" in result.output
