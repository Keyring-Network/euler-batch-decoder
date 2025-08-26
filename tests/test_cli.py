"""Test the CLI module functionality."""

from __future__ import annotations

import json
import tempfile
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from evc_batch_decoder.cli import decode_batch


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def sample_batch_data():
    """Sample batch data for testing."""
    return "0x0ac3e31803e80320"


@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing."""
    return {"data": "0x0ac3e31803e80320"}


def test_cli_basic_decode(runner, sample_batch_data):
    """Test basic CLI decoding functionality."""
    result = runner.invoke(decode_batch, [sample_batch_data])

    assert result.exit_code == 0
    assert "EVC Batch Decoder Results" in result.output


def test_cli_json_output(runner, sample_batch_data):
    """Test CLI with JSON output flag."""
    result = runner.invoke(decode_batch, [sample_batch_data, "--json-output"])

    assert result.exit_code == 0
    # Should contain JSON-like structure
    assert '"batch"' in result.output
    assert '"analysis"' in result.output
    assert '"items"' in result.output


def test_cli_readme_format(runner, sample_batch_data):
    """Test CLI with README format flag."""
    result = runner.invoke(decode_batch, [sample_batch_data, "--readme-format"])

    assert result.exit_code == 0
    assert "Changes:" in result.output


def test_cli_file_input(runner, sample_json_data):
    """Test CLI with file input."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_json_data, f)
        temp_file = f.name

    result = runner.invoke(decode_batch, ["--file", temp_file])

    assert result.exit_code == 0
    assert "EVC Batch Decoder Results" in result.output


def test_cli_chain_id_option(runner, sample_batch_data):
    """Test CLI with chain ID option."""
    result = runner.invoke(decode_batch, [sample_batch_data, "--chain-id", "1"])

    assert result.exit_code == 0
    assert "EVC Batch Decoder Results" in result.output


@patch("evc_batch_decoder.cli.Web3")
def test_cli_with_rpc_url_success(mock_web3, runner, sample_batch_data):
    """Test CLI with RPC URL option (successful connection)."""
    mock_w3_instance = Mock()
    mock_web3.return_value = mock_w3_instance

    result = runner.invoke(decode_batch, [sample_batch_data, "--rpc-url", "https://eth.llamarpc.com"])

    assert result.exit_code == 0
    assert "Connected to RPC" in result.output


@patch("evc_batch_decoder.cli.Web3")
def test_cli_with_rpc_url_failure(mock_web3, runner, sample_batch_data):
    """Test CLI with RPC URL option (connection failure)."""
    mock_web3.side_effect = Exception("Connection failed")

    result = runner.invoke(decode_batch, [sample_batch_data, "--rpc-url", "https://invalid-url.com"])

    assert result.exit_code == 0  # Should continue without RPC
    assert "Warning: Failed to connect to RPC" in result.output


def test_cli_tx_hash_without_rpc(runner):
    """Test CLI with tx-hash but no RPC URL (should fail)."""
    result = runner.invoke(decode_batch, ["--tx-hash", "0xabc123"])

    assert result.exit_code == 1
    assert "Error: --rpc-url is required when using --tx-hash" in result.output


@patch("evc_batch_decoder.cli.Web3")
def test_cli_tx_hash_with_rpc_success(mock_web3, runner):
    """Test CLI with tx-hash and RPC (successful)."""
    # Mock Web3 and transaction
    mock_w3_instance = Mock()
    mock_web3.return_value = mock_w3_instance

    mock_tx = {"input": Mock()}
    mock_tx["input"].hex.return_value = "0x0ac3e31803e80320"
    mock_w3_instance.eth.get_transaction.return_value = mock_tx

    result = runner.invoke(decode_batch, ["--tx-hash", "0xabc123", "--rpc-url", "https://eth.llamarpc.com"])

    assert result.exit_code == 0
    assert "Loaded transaction data from" in result.output


@patch("evc_batch_decoder.cli.Web3")
def test_cli_tx_hash_with_rpc_failure(mock_web3, runner):
    """Test CLI with tx-hash and RPC (transaction fetch failure)."""
    # Mock Web3 but make transaction fetch fail
    mock_w3_instance = Mock()
    mock_web3.return_value = mock_w3_instance
    mock_w3_instance.eth.get_transaction.side_effect = Exception("Transaction not found")

    result = runner.invoke(decode_batch, ["--tx-hash", "0xabc123", "--rpc-url", "https://eth.llamarpc.com"])

    assert result.exit_code == 1
    assert "Error loading transaction" in result.output


def test_cli_no_input(runner):
    """Test CLI with no input (should fail)."""
    result = runner.invoke(decode_batch, input="")

    assert result.exit_code == 1
    assert "No batch data provided" in result.output


def test_cli_stdin_input(runner, sample_batch_data):
    """Test CLI with stdin input."""
    result = runner.invoke(decode_batch, input=sample_batch_data)

    assert result.exit_code == 0
    assert "EVC Batch Decoder Results" in result.output


def test_cli_invalid_data(runner):
    """Test CLI with invalid batch data."""
    result = runner.invoke(decode_batch, ["invalid_data"])

    assert result.exit_code == 1
    assert "Error decoding batch" in result.output


def test_cli_file_read_error(runner):
    """Test CLI with non-existent file."""
    result = runner.invoke(decode_batch, ["--file", "/nonexistent/file.json"])

    assert result.exit_code == 2  # Click returns 2 for file not found
    assert "No such file or directory" in result.output or "Error" in result.output


def test_cli_version(runner):
    """Test CLI version option."""
    result = runner.invoke(decode_batch, ["--version"])

    assert result.exit_code == 0
    # Should show version info


def test_cli_help(runner):
    """Test CLI help option."""
    result = runner.invoke(decode_batch, ["--help"])

    assert result.exit_code == 0
    assert "Decode EVC batch transaction data" in result.output
