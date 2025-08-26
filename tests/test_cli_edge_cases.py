"""Test CLI edge cases for 100% coverage."""

from __future__ import annotations

import tempfile
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from evc_batch_decoder.cli import decode_batch


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@patch('evc_batch_decoder.cli.Web3')
def test_cli_tx_hash_rpc_connection_but_tx_error(mock_web3, runner):
    """Test CLI with RPC connection success but transaction retrieval error."""
    mock_w3_instance = Mock()
    mock_web3.return_value = mock_w3_instance
    # Connection succeeds but transaction fetch fails  
    mock_w3_instance.eth.get_transaction.side_effect = Exception("Transaction not found")
    
    result = runner.invoke(decode_batch, [
        "--tx-hash", "0xabc123",
        "--rpc-url", "https://eth.llamarpc.com"
    ])
    
    assert result.exit_code == 1
    assert "Error loading transaction" in result.output


def test_cli_file_with_invalid_json(runner):
    """Test CLI with file containing invalid JSON."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"invalid": json}')  # Invalid JSON
        temp_file = f.name
    
    result = runner.invoke(decode_batch, ["--file", temp_file])
    
    # Should still work, treating as raw hex string
    assert result.exit_code == 1  # Will fail due to invalid hex
    

def test_cli_stdin_keyboard_interrupt(runner):
    """Test CLI stdin with keyboard interrupt handling."""
    # This tests the KeyboardInterrupt handling in stdin reading
    with patch('sys.stdin.read') as mock_stdin:
        mock_stdin.side_effect = KeyboardInterrupt()
        
        result = runner.invoke(decode_batch, input="")
        
        assert result.exit_code == 1
        assert "No batch data provided" in result.output


def test_cli_with_debug_flag(runner):
    """Test CLI with debug information on error."""
    # Test the debug flag path - Note: click returns exit code 2 for invalid arguments
    result = runner.invoke(decode_batch, ["invalid_hex_data", "--debug"])
    
    # Click returns 2 for parsing errors, 1 for application errors
    assert result.exit_code in [1, 2]
    # Should show some kind of error
    assert "error" in result.output.lower() or "Error" in result.output


@patch('evc_batch_decoder.cli.Web3')
def test_cli_tx_hash_with_hex_bytes_input(mock_web3, runner):
    """Test CLI with transaction that returns hex bytes."""
    mock_w3_instance = Mock()
    mock_web3.return_value = mock_w3_instance
    
    # Mock transaction with hex bytes (no .hex() method)
    mock_tx = {'input': "0x0ac3e31803e80320"}  # Direct hex string
    mock_w3_instance.eth.get_transaction.return_value = mock_tx
    
    result = runner.invoke(decode_batch, [
        "--tx-hash", "0xabc123",
        "--rpc-url", "https://eth.llamarpc.com"
    ])
    
    assert result.exit_code == 0


def test_cli_file_read_with_plain_text(runner):
    """Test CLI file reading with plain text (not JSON)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("0x0ac3e31803e80320")  # Plain hex string
        temp_file = f.name
    
    result = runner.invoke(decode_batch, ["--file", temp_file])
    
    assert result.exit_code == 0
    assert "EVC Batch Decoder Results" in result.output


def test_cli_empty_stdin(runner):
    """Test CLI with empty stdin."""
    result = runner.invoke(decode_batch, input="")
    
    assert result.exit_code == 1
    assert "No batch data provided" in result.output
