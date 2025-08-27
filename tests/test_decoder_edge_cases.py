"""Test decoder edge cases for 100% coverage."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from evc_batch_decoder.decoder import BatchDecoding, BatchItem, EVCBatchDecoder


@pytest.fixture
def decoder():
    """Create a decoder instance for testing."""
    return EVCBatchDecoder()


class TestDecoderEdgeCases:
    """Test edge cases in the decoder for full coverage."""

    def test_fetch_vault_metadata_multicall_decode_error(self, decoder):
        """Test vault metadata fetching with multicall decode error."""
        addresses = ["0x1234567890123456789012345678901234567890"]
        mock_web3 = Mock()

        # Mock successful multicall but decode failure
        mock_contract = Mock()
        mock_web3.eth.contract.return_value = mock_contract
        mock_web3.to_checksum_address.side_effect = lambda x: x

        # Mock successful multicall response but invalid decode data
        mock_contract.functions.aggregate3.return_value.call.return_value = [
            (True, b"invalid_data"),  # Invalid data that will cause decode error
            (False, b""),  # Failed second call
        ]

        decoder.fetch_vault_metadata(addresses, mock_web3)

        # Should still add metadata (fallback to generic name)
        assert addresses[0].lower() in decoder.metadata

    def test_fetch_vault_metadata_multicall_failed_response(self, decoder):
        """Test vault metadata fetching with failed multicall response."""
        addresses = ["0x1234567890123456789012345678901234567890"]
        mock_web3 = Mock()

        # Mock successful multicall but failed response
        mock_contract = Mock()
        mock_web3.eth.contract.return_value = mock_contract
        mock_web3.to_checksum_address.side_effect = lambda x: x

        # Mock failed multicall response
        mock_contract.functions.aggregate3.return_value.call.return_value = [
            (False, b""),  # Failed first call
            (False, b""),  # Failed second call
        ]

        decoder.fetch_vault_metadata(addresses, mock_web3)

        # Should add generic metadata
        assert addresses[0].lower() in decoder.metadata
        assert "EVK Vault" in decoder.metadata[addresses[0].lower()]["name"]

    def test_analyze_batch_with_oracle_address_collection(self, decoder):
        """Test batch analysis that collects oracle addresses."""
        batch = BatchDecoding(
            items=[
                BatchItem(
                    target_contract="0x1234567890123456789012345678901234567890",
                    data="0x2c4e0a11",
                    decoded={
                        "functionName": "govSetConfig",
                        "args": {
                            "base": "0x123",
                            "quote": "0x456",
                            "oracle": "0x7890123456789012345678901234567890123456",
                        },
                    },
                )
            ]
        )

        # This should collect the oracle address
        analysis = decoder.analyze_batch(batch)

        # Verify oracle metadata was attempted to be fetched (generic name added)
        oracle_addr = "0x7890123456789012345678901234567890123456"
        assert oracle_addr.lower() in decoder.metadata

    def test_format_output_with_nested_batch_items(self, decoder):
        """Test format output with nested batch items."""
        nested_batch = BatchDecoding(
            items=[
                BatchItem(
                    target_contract="0x1234567890123456789012345678901234567890",
                    data="0x0ac3e31803e80320",
                    decoded={"functionName": "setCaps", "args": {"supplyCap": 1000, "borrowCap": 800}},
                )
            ]
        )

        main_batch = BatchDecoding(
            items=[
                BatchItem(
                    target_contract="0x1234567890123456789012345678901234567890",
                    data="0x0ac3e31803e80320",
                    nested_batch=nested_batch,
                    decoded={"functionName": "batch", "args": {}},
                )
            ]
        )

        analysis = {
            "total_items": 1,
            "governance_operations": [],
            "vault_changes": {},
            "router_changes": {},
            "unknown_operations": [],
            "nested_batches": 1,
        }

        # Should not raise any errors
        decoder.format_output(main_batch, analysis)

    def test_format_output_with_unknown_operations(self, decoder):
        """Test format output with unknown operations."""
        batch = BatchDecoding(
            items=[
                BatchItem(
                    target_contract="0x1234567890123456789012345678901234567890",
                    data="0x12345678abcd",
                    decoded={"functionName": "unknown", "selector": "0x12345678", "args": {}},
                )
            ]
        )

        analysis = {
            "total_items": 1,
            "governance_operations": [],
            "vault_changes": {},
            "router_changes": {},
            "unknown_operations": [
                {"index": 0, "target": batch.items[0].target_contract, "selector": "0x12345678", "data_length": 6}
            ],
            "nested_batches": 0,
        }

        # Should not raise any errors and cover unknown operations branch
        decoder.format_output(batch, analysis)

    def test_format_output_with_governance_changes(self, decoder):
        """Test format output with vault and router changes."""
        batch = BatchDecoding(
            items=[
                BatchItem(
                    target_contract="0x1234567890123456789012345678901234567890",
                    data="0x0ac3e31803e80320",
                    decoded={"functionName": "setCaps", "args": {"supplyCap": 1000, "borrowCap": 800}},
                )
            ]
        )

        analysis = {
            "total_items": 1,
            "governance_operations": [
                {"index": 0, "function": "setCaps", "target": batch.items[0].target_contract, "args": {}}
            ],
            "vault_changes": {
                batch.items[0].target_contract: [{"function": "setCaps", "args": {"supplyCap": 1000, "borrowCap": 800}}]
            },
            "router_changes": {"0xabcd1234": [{"function": "govSetConfig", "args": {"base": "0x123"}}]},
            "unknown_operations": [],
            "nested_batches": 0,
        }

        # Should cover both vault and router changes branches
        decoder.format_output(batch, analysis)

    def test_decode_batch_data_with_actual_batch_selector(self, decoder):
        """Test decoding with actual batch selector but minimal data."""
        # Test the branch where selector matches batch but decoding might fail
        batch_data = "0x72e94bf6"  # batch selector only, no calldata

        with pytest.raises((ValueError, IndexError, TypeError)):  # Should raise decoding error
            decoder.decode_batch_data(batch_data)

    def test_format_readme_style_with_complex_caps(self, decoder):
        """Test README formatting with different cap values."""
        batch = BatchDecoding(
            items=[
                BatchItem(
                    target_contract="0x1234567890123456789012345678901234567890",
                    data="0x0ac3e31803e80320",
                    decoded={"functionName": "setCaps", "args": {"supplyCap": 6, "borrowCap": 12813}},
                )
            ]
        )

        analysis = {
            "vault_changes": {
                "0x1234567890123456789012345678901234567890": [
                    {"function": "setCaps", "args": {"supplyCap": 6, "borrowCap": 12813}}
                ]
            },
            "router_changes": {},
        }

        output = decoder.format_readme_style(batch, analysis)

        # Should handle different cap value transformations
        assert "supplyCap → 6" in output
        assert "borrowCap → 12813" in output

    def test_decode_single_function_with_raw_data(self, decoder):
        """Test decode single function that results in raw data display."""
        batch = BatchDecoding(
            items=[
                BatchItem(
                    target_contract="0x1234567890123456789012345678901234567890",
                    data="0x12345678",
                    decoded=None,  # No decoded info, should show raw data
                )
            ]
        )

        analysis = {
            "total_items": 1,
            "governance_operations": [],
            "vault_changes": {},
            "router_changes": {},
            "unknown_operations": [],
            "nested_batches": 0,
        }

        # Should handle items without decoded info (raw data branch)
        decoder.format_output(batch, analysis)

    @patch("evc_batch_decoder.decoder.console")
    def test_fetch_metadata_with_warning_output(self, mock_console, decoder):
        """Test metadata fetching that produces console warnings."""
        # Test the warning output branches in metadata fetching
        addresses = ["0x1234567890123456789012345678901234567890"]

        # Without web3 client - should produce warnings
        decoder.fetch_vault_metadata(addresses, None)
        decoder.fetch_router_metadata(addresses, None)
        decoder.fetch_oracle_metadata(addresses, None)

        # Should have called console.print with warnings
        assert mock_console.print.call_count >= 3
