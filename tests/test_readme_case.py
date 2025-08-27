"""Test the specific case from the README."""

from __future__ import annotations

import pytest

from evc_batch_decoder.decoder import EVCBatchDecoder


# Example batch with two setCaps operations on different vaults
@pytest.fixture
def batch_data_setcaps():
    return (
        "0xc16ae7a400000000000000000000000000000000000000000000000000000000000000"
        "200000000000000000000000000000000000000000000000000000000000000002000000"
        "000000000000000000000000000000000000000000000000000000004000000000000000"
        "000000000000000000000000000000000000000000000001400000000000000000000000"
        "008f23da78e3f31ab5deb75dc3282198bed630ffde00000000000000000000000069cc42"
        "5b1e5f302e7db4e5d125ab984ec518636400000000000000000000000000000000000000"
        "000000000000000000000000000000000000000000000000000000000000000000000000"
        "000000000000000080000000000000000000000000000000000000000000000000000000"
        "0000000044d87f780f000000000000000000000000000000000000000000000000000000"
        "000000320d00000000000000000000000000000000000000000000000000000000000032"
        "0d0000000000000000000000000000000000000000000000000000000000000000000000"
        "0000000000ea534105c2ccc0582d82b285aa47a6b446383d440000000000000000000000"
        "0069cc425b1e5f302e7db4e5d125ab984ec5186364000000000000000000000000000000"
        "000000000000000000000000000000000000000000000000000000000000000000000000"
        "000000000000000000000000800000000000000000000000000000000000000000000000"
        "000000000000000044d87f780f0000000000000000000000000000000000000000000000"
        "00000000000000320d000000000000000000000000000000000000000000000000000000"
        "000000000600000000000000000000000000000000000000000000000000000000"
    )


@pytest.fixture
def decoder():
    """Create a decoder instance for testing."""
    return EVCBatchDecoder(chain_id=43114)  # Avalanche for test case


@pytest.fixture
def test_metadata():
    """Mock test case metadata."""
    return {
        "0x8f23da78e3f31ab5deb75dc3282198bed630ffde": {
            "name": "EVK Vault eUSDC-15",
            "type": "vault",
            "symbol": "eUSDC-15",
        },
        "0xea534105c2ccc0582d82b285aa47a6b446383d44": {
            "name": "EVK Vault exUSDC-7",
            "type": "vault",
            "symbol": "exUSDC-7",
        },
    }


def test_readme_case(batch_data_setcaps: str, decoder: EVCBatchDecoder, test_metadata: dict) -> None:
    """Test the specific batch data from the README."""
    result = decoder.decode_batch_data(batch_data_setcaps)

    # Verify the expected results
    assert len(result.items) == 2, f"Expected 2 items, got {len(result.items)}"

    # Check first item
    item1 = result.items[0]
    assert item1.target_contract.lower() == "0x8f23da78e3f31ab5deb75dc3282198bed630ffde", (
        f"Wrong target contract: {item1.target_contract}"
    )
    assert item1.decoded is not None, "First item should be decoded"
    assert item1.decoded["functionName"] == "setCaps", f"Expected setCaps, got {item1.decoded['functionName']}"
    assert item1.decoded["args"]["supplyCap"] == 12813, (
        f"Expected supplyCap 12813, got {item1.decoded['args']['supplyCap']}"
    )
    assert item1.decoded["args"]["borrowCap"] == 12813, (
        f"Expected borrowCap 12813, got {item1.decoded['args']['borrowCap']}"
    )

    # Check second item
    item2 = result.items[1]
    assert item2.target_contract.lower() == "0xea534105c2ccc0582d82b285aa47a6b446383d44", (
        f"Wrong target contract: {item2.target_contract}"
    )
    assert item2.decoded is not None, "Second item should be decoded"
    assert item2.decoded["functionName"] == "setCaps", f"Expected setCaps, got {item2.decoded['functionName']}"
    assert item2.decoded["args"]["supplyCap"] == 12813, (
        f"Expected supplyCap 12813, got {item2.decoded['args']['supplyCap']}"
    )
    assert item2.decoded["args"]["borrowCap"] == 6, (
        f"Expected borrowCap 6, got {item2.decoded['args']['borrowCap']}"
    )

    # Analyze the batch (this will use generic names since no web3 client)
    analysis = decoder.analyze_batch(result)

    # Verify analysis structure
    assert "governance_operations" in analysis
    assert "vault_changes" in analysis
    assert len(analysis["governance_operations"]) >= 0
    assert len(analysis["vault_changes"]) >= 0

    # For testing purposes, add the expected metadata after analysis
    # This simulates what would happen with a real web3 client
    for address, metadata in test_metadata.items():
        decoder.add_contract_metadata(address, metadata)

    # Test README-style formatting
    readme_output = decoder.format_readme_style(result, analysis)
    assert readme_output  # Should produce some output
    assert "Changes:" in readme_output  # Should contain expected sections
