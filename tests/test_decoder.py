"""Simple test script for the EVC batch decoder."""

from __future__ import annotations

import pytest

from evc_batch_decoder.decoder import EVCBatchDecoder


@pytest.fixture
def decoder() -> EVCBatchDecoder:
    """Create a decoder instance for testing."""
    return EVCBatchDecoder()


def test_simple_batch_decoding(decoder: EVCBatchDecoder) -> None:
    """Test decoding a simple batch operation."""
    # Test data: A simple setCaps function call
    # setCaps(supplyCap=1000, borrowCap=800)
    set_caps_data = (
        "0x0ac3e318"
        "0000000000000000000000000000000000000000000000000000000000000064"
        "000000000000000000000000000000000000000000000000000000000000003c"
    )  # setCaps selector + args

    result = decoder.decode_batch_data(set_caps_data)

    # Verify basic structure
    assert result.items
    assert len(result.items) == 1

    # Verify decoding worked
    item = result.items[0]
    assert item.decoded is not None

    # Verify function name and args were decoded
    decoded = item.decoded
    assert "functionName" in decoded
    assert "args" in decoded


def test_json_input_format(decoder: EVCBatchDecoder) -> None:
    """Test JSON input format."""
    json_data = {
        "data": "0x0ac3e3180000000000000000000000000000000000000000000000000000000000000064000000000000000000000000000000000000000000000000000000000000003c"
    }

    result = decoder.decode_batch_data(json_data)

    # Should successfully decode JSON format
    assert result.items
    assert len(result.items) == 1


def test_batch_analysis(decoder: EVCBatchDecoder) -> None:
    """Test batch analysis functionality."""
    set_caps_data = (
        "0x0ac3e318"
        "0000000000000000000000000000000000000000000000000000000000000064"
        "000000000000000000000000000000000000000000000000000000000000003c"
    )

    result = decoder.decode_batch_data(set_caps_data)
    analysis = decoder.analyze_batch(result)

    # Verify analysis structure
    assert "total_items" in analysis
    assert "governance_operations" in analysis
    assert "vault_changes" in analysis
    assert "router_changes" in analysis
    assert "unknown_operations" in analysis
    assert "nested_batches" in analysis

    # Verify counts
    assert analysis["total_items"] == len(result.items)
