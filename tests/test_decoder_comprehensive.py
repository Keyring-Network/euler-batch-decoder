"""Comprehensive tests for the decoder module to achieve 100% coverage."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from eth_abi.exceptions import InsufficientDataBytes

from evc_batch_decoder.decoder import BatchDecoding, BatchItem, EVCBatchDecoder, TimelockInfo


@pytest.fixture
def decoder() -> EVCBatchDecoder:
    """Create a decoder instance for testing."""
    return EVCBatchDecoder()


@pytest.fixture
def decoder_mainnet() -> EVCBatchDecoder:
    """Create a decoder instance for mainnet."""
    return EVCBatchDecoder(chain_id=1)


@pytest.fixture
def mock_web3() -> Mock:
    """Create a mock Web3 instance."""
    return Mock()


class TestEVCBatchDecoder:
    """Comprehensive tests for EVCBatchDecoder."""

    def test_init_default_chain(self) -> None:
        """Test decoder initialization with default chain."""
        decoder = EVCBatchDecoder()
        assert decoder.chain_id == 43114  # Default Avalanche
        assert decoder.chain_config["name"] == "avalanche"

    def test_init_mainnet_chain(self) -> None:
        """Test decoder initialization with mainnet."""
        decoder = EVCBatchDecoder(chain_id=1)
        assert decoder.chain_id == 1
        assert decoder.chain_config["name"] == "mainnet"

    def test_init_unknown_chain(self) -> None:
        """Test decoder initialization with unknown chain."""
        decoder = EVCBatchDecoder(chain_id=999)
        assert decoder.chain_id == 999
        # Should fallback to Avalanche config
        assert decoder.chain_config["name"] == "avalanche"

    def test_load_function_signatures(self, decoder: EVCBatchDecoder) -> None:
        """Test function signature loading."""
        signatures = decoder._load_function_signatures()

        assert "0x72e94bf6" in signatures  # batch function
        assert "0x0ac3e318" in signatures  # setCaps function
        assert signatures["0x0ac3e318"]["name"] == "setCaps"

    def test_load_chain_config(self, decoder: EVCBatchDecoder) -> None:
        """Test chain configuration loading."""
        config = decoder._load_chain_config()

        assert "name" in config
        assert "explorer_base_url" in config
        assert "addresses" in config

    def test_get_contract_name_with_metadata(self, decoder: EVCBatchDecoder) -> None:
        """Test getting contract name with existing metadata."""
        test_address = "0x1234567890123456789012345678901234567890"
        decoder.add_contract_metadata(test_address, {"name": "Test Contract"})

        name = decoder.get_contract_name(test_address)
        assert name == "Test Contract"

    def test_get_contract_name_system_address(self, decoder_mainnet: EVCBatchDecoder) -> None:
        """Test getting contract name for known system addresses."""
        evc_address = "0x0C9a3dd6b8F28529d72d7f9cE918D493519EE383"  # Mainnet EVC

        name = decoder_mainnet.get_contract_name(evc_address)
        assert "EVC" in name

    def test_get_contract_name_short_address(self, decoder: EVCBatchDecoder) -> None:
        """Test getting contract name for unknown address (should return shortened)."""
        test_address = "0x1234567890123456789012345678901234567890"

        name = decoder.get_contract_name(test_address)
        assert name == "0x1234...567890"

    def test_get_contract_name_short_address_too_short(self, decoder: EVCBatchDecoder) -> None:
        """Test getting contract name for very short address."""
        test_address = "0x12345"

        name = decoder.get_contract_name(test_address)
        assert name == test_address

    def test_get_contract_link(self, decoder: EVCBatchDecoder) -> None:
        """Test getting contract link."""
        test_address = "0x1234567890123456789012345678901234567890"

        link = decoder.get_contract_link(test_address)
        assert test_address in link
        assert "https://" in link
        assert "[" in link and "](" in link  # Markdown link format

    def test_add_contract_metadata(self, decoder: EVCBatchDecoder) -> None:
        """Test adding contract metadata."""
        test_address = "0x1234567890123456789012345678901234567890"
        metadata = {"name": "Test Contract", "type": "vault"}

        decoder.add_contract_metadata(test_address, metadata)
        assert test_address.lower() in decoder.metadata
        assert decoder.metadata[test_address.lower()]["name"] == "Test Contract"

    def test_set_chain(self, decoder: EVCBatchDecoder) -> None:
        """Test setting chain ID."""
        original_chain = decoder.chain_id
        decoder.set_chain(1)

        assert decoder.chain_id == 1
        assert decoder.chain_id != original_chain
        assert decoder.chain_config["name"] == "mainnet"

    def test_decode_batch_data_dict_format(self, decoder: EVCBatchDecoder) -> None:
        """Test decoding batch data from dictionary format."""
        data = {"data": "0x0ac3e31803e80320"}

        result = decoder.decode_batch_data(data)
        assert isinstance(result, BatchDecoding)
        assert len(result.items) == 1

    def test_decode_batch_data_dict_format_invalid(self, decoder: EVCBatchDecoder) -> None:
        """Test decoding batch data from dictionary without 'data' field."""
        data = {"invalid": "0x0ac3e31803e80320"}

        with pytest.raises(ValueError, match="Dictionary input must contain 'data' field"):
            decoder.decode_batch_data(data)

    def test_decode_batch_data_json_string(self, decoder: EVCBatchDecoder) -> None:
        """Test decoding batch data from JSON string."""
        data = '{"data": "0x0ac3e31803e80320"}'

        result = decoder.decode_batch_data(data)
        assert isinstance(result, BatchDecoding)
        assert len(result.items) == 1

    def test_decode_batch_data_bytes_format(self, decoder: EVCBatchDecoder) -> None:
        """Test decoding batch data from bytes format."""
        data = bytes.fromhex("0ac3e31803e80320")

        result = decoder.decode_batch_data(data)
        assert isinstance(result, BatchDecoding)
        assert len(result.items) == 1

    def test_decode_batch_data_no_0x_prefix(self, decoder: EVCBatchDecoder) -> None:
        """Test decoding batch data without 0x prefix."""
        data = "0ac3e31803e80320"

        result = decoder.decode_batch_data(data)
        assert isinstance(result, BatchDecoding)
        assert len(result.items) == 1

    def test_decode_batch_data_too_short(self, decoder: EVCBatchDecoder) -> None:
        """Test decoding batch data that's too short."""
        data = "0x123"

        with pytest.raises(ValueError, match="Data too short to contain function selector"):
            decoder.decode_batch_data(data)

    def test_decode_batch_function_error_handling(self, decoder: EVCBatchDecoder) -> None:
        """Test batch function error handling."""
        # Test with batch selector but invalid data
        batch_data = "0x72e94bf6"  # Just the batch selector, no data

        with pytest.raises((ValueError, IndexError, TypeError, InsufficientDataBytes)):  # Should raise decoding error
            decoder.decode_batch_data(batch_data)

    def test_decode_function_call_with_unknown_selector(self, decoder: EVCBatchDecoder) -> None:
        """Test decoding function call with unknown selector."""
        data = bytes.fromhex("12345678")  # Unknown selector

        result = decoder._decode_function_call(data)
        assert result is not None
        assert result["functionName"] == "unknown"
        assert result["selector"] == "0x12345678"

    def test_decode_function_call_too_short(self, decoder: EVCBatchDecoder) -> None:
        """Test decoding function call with data too short."""
        data = bytes.fromhex("12")  # Too short (only 1 byte, need at least 4)

        result = decoder._decode_function_call(data)
        assert result is None

    def test_decode_function_call_with_args_decode_error(self, decoder: EVCBatchDecoder) -> None:
        """Test decoding function call where argument decoding fails."""
        # Use setCaps selector but with invalid argument data
        data = bytes.fromhex("0ac3e31812")  # setCaps selector + invalid args (too short)

        result = decoder._decode_function_call(data)
        assert result is not None
        assert result["functionName"] == "setCaps"
        assert "error" in result

    def test_fetch_vault_metadata_no_addresses(self, decoder: EVCBatchDecoder) -> None:
        """Test fetching vault metadata with no addresses."""
        decoder.fetch_vault_metadata([])
        # Should not raise any errors

    def test_fetch_vault_metadata_no_web3_client(self, decoder: EVCBatchDecoder) -> None:
        """Test fetching vault metadata without web3 client."""
        addresses = ["0x1234567890123456789012345678901234567890"]

        decoder.fetch_vault_metadata(addresses)

        # Should add generic metadata
        assert addresses[0].lower() in decoder.metadata
        assert "EVK Vault" in decoder.metadata[addresses[0].lower()]["name"]

    @patch("evc_batch_decoder.decoder.console")
    def test_fetch_vault_metadata_with_web3_multicall_success(
        self, mock_console, decoder: EVCBatchDecoder, mock_web3: Mock
    ) -> None:
        """Test fetching vault metadata with web3 client (successful multicall)."""
        addresses = ["0x1234567890123456789012345678901234567890"]

        # Mock multicall contract and response
        mock_contract = Mock()
        mock_web3.eth.contract.return_value = mock_contract
        mock_web3.to_checksum_address.side_effect = lambda x: x

        # Mock successful multicall response
        mock_contract.functions.aggregate3.return_value.call.return_value = [
            (
                True,
                (
                    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x20"
                    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b"
                    b"Test Vault"
                ),
            ),
            (
                True,
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12\x34\x56\x78\x90\x12\x34\x56\x78\x90\x12\x34\x56\x78\x90\x12\x34\x56\x78\x90",
            ),
        ]

        decoder.fetch_vault_metadata(addresses, mock_web3)

        # Should have added metadata
        assert addresses[0].lower() in decoder.metadata

    def test_fetch_vault_metadata_with_web3_multicall_failure(self, decoder: EVCBatchDecoder, mock_web3: Mock) -> None:
        """Test fetching vault metadata with web3 client (multicall failure)."""
        addresses = ["0x1234567890123456789012345678901234567890"]

        # Mock multicall failure
        mock_web3.eth.contract.side_effect = Exception("Multicall failed")
        mock_web3.to_checksum_address.side_effect = lambda x: x

        decoder.fetch_vault_metadata(addresses, mock_web3)

        # Should fallback to generic names
        assert addresses[0].lower() in decoder.metadata
        assert "EVK Vault" in decoder.metadata[addresses[0].lower()]["name"]

    def test_fetch_router_metadata(self, decoder: EVCBatchDecoder) -> None:
        """Test fetching router metadata."""
        addresses = ["0x1234567890123456789012345678901234567890"]

        decoder.fetch_router_metadata(addresses)

        # Should add generic metadata
        assert addresses[0].lower() in decoder.metadata
        assert "Oracle Router" in decoder.metadata[addresses[0].lower()]["name"]

    def test_fetch_oracle_metadata(self, decoder: EVCBatchDecoder) -> None:
        """Test fetching oracle metadata."""
        addresses = ["0x1234567890123456789012345678901234567890"]

        decoder.fetch_oracle_metadata(addresses)

        # Should add generic metadata
        assert addresses[0].lower() in decoder.metadata
        assert "Oracle" in decoder.metadata[addresses[0].lower()]["name"]

    def test_analyze_batch_with_nested_batch(self, decoder: EVCBatchDecoder) -> None:
        """Test analyzing batch with nested batch items."""
        # Create a batch with nested batch
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
                )
            ]
        )

        analysis = decoder.analyze_batch(main_batch)

        assert analysis["nested_batches"] == 1
        assert analysis["total_items"] == 1

    def test_analyze_batch_governance_functions(self, decoder: EVCBatchDecoder) -> None:
        """Test analyzing batch with governance functions."""
        batch = BatchDecoding(
            items=[
                BatchItem(
                    target_contract="0x1234567890123456789012345678901234567890",
                    data="0x0ac3e31803e80320",
                    decoded={"functionName": "setCaps", "args": {"supplyCap": 1000, "borrowCap": 800}},
                )
            ]
        )

        analysis = decoder.analyze_batch(batch)

        assert len(analysis["governance_operations"]) == 1
        assert analysis["governance_operations"][0]["function"] == "setCaps"
        assert len(analysis["vault_changes"]) == 1

    def test_analyze_batch_router_governance_functions(self, decoder: EVCBatchDecoder) -> None:
        """Test analyzing batch with router governance functions."""
        batch = BatchDecoding(
            items=[
                BatchItem(
                    target_contract="0x1234567890123456789012345678901234567890",
                    data="0x2c4e0a11",
                    decoded={
                        "functionName": "govSetConfig",
                        "args": {"base": "0x123", "quote": "0x456", "oracle": "0x789"},
                    },
                )
            ]
        )

        analysis = decoder.analyze_batch(batch)

        assert len(analysis["governance_operations"]) == 1
        assert analysis["governance_operations"][0]["function"] == "govSetConfig"
        assert len(analysis["router_changes"]) == 1

    def test_analyze_batch_unknown_operations(self, decoder: EVCBatchDecoder) -> None:
        """Test analyzing batch with unknown operations."""
        batch = BatchDecoding(
            items=[
                BatchItem(
                    target_contract="0x1234567890123456789012345678901234567890",
                    data="0x12345678abcd",
                    decoded={"functionName": "unknown", "selector": "0x12345678", "args": {}},
                )
            ]
        )

        analysis = decoder.analyze_batch(batch)

        assert len(analysis["unknown_operations"]) == 1
        assert analysis["unknown_operations"][0]["selector"] == "0x12345678"

    @patch("evc_batch_decoder.decoder.console")
    def test_format_output_with_timelock(self, mock_console, decoder: EVCBatchDecoder) -> None:
        """Test formatting output with timelock information."""
        batch = BatchDecoding(
            items=[
                BatchItem(
                    target_contract="0x1234567890123456789012345678901234567890",
                    data="0x0ac3e31803e80320",
                    decoded={"functionName": "setCaps", "args": {"supplyCap": 1000, "borrowCap": 800}},
                )
            ],
            timelock_info=TimelockInfo(delay=3600),
        )

        analysis = {
            "total_items": 1,
            "governance_operations": [],
            "vault_changes": {},
            "router_changes": {},
            "unknown_operations": [],
            "nested_batches": 0,
        }

        decoder.format_output(batch, analysis)

        # Should call console.print with timelock info
        mock_console.print.assert_called()

    def test_format_readme_style_with_vault_changes(self, decoder: EVCBatchDecoder) -> None:
        """Test README-style formatting with vault changes."""
        batch = BatchDecoding(
            items=[
                BatchItem(
                    target_contract="0x1234567890123456789012345678901234567890",
                    data="0x0ac3e31803e80320",
                    decoded={"functionName": "setCaps", "args": {"supplyCap": 12813, "borrowCap": 6}},
                )
            ]
        )

        analysis = {
            "vault_changes": {
                "0x1234567890123456789012345678901234567890": [
                    {"function": "setCaps", "args": {"supplyCap": 12813, "borrowCap": 6}}
                ]
            },
            "router_changes": {},
        }

        output = decoder.format_readme_style(batch, analysis)

        assert "Changes:" in output
        assert "supplyCap → 12813" in output
        assert "borrowCap → 6" in output
        assert "Items" in output

    def test_import_error_handling(self) -> None:
        """Test import error handling."""
        # This test verifies the import error handling in the try/except block
        # The actual import errors are hard to test in pytest, but we can verify
        # the structure is in place
        import evc_batch_decoder.decoder as decoder_module

        # The module should have the necessary imports or raise ImportError
        assert hasattr(decoder_module, "EVCBatchDecoder")
        assert hasattr(decoder_module, "console")


class TestDataClasses:
    """Test the data classes."""

    def test_batch_item_creation(self) -> None:
        """Test BatchItem creation."""
        item = BatchItem(target_contract="0x123", data="0xabcd")

        assert item.target_contract == "0x123"
        assert item.data == "0xabcd"
        assert item.value == 0  # Default value
        assert item.on_behalf_of == "0x0000000000000000000000000000000000000000"  # Default
        assert item.decoded is None
        assert item.nested_batch is None

    def test_timelock_info_creation(self) -> None:
        """Test TimelockInfo creation."""
        info = TimelockInfo(delay=3600)

        assert info.delay == 3600

    def test_batch_decoding_creation(self) -> None:
        """Test BatchDecoding creation."""
        items = [BatchItem(target_contract="0x123", data="0xabcd")]
        decoding = BatchDecoding(items=items)

        assert len(decoding.items) == 1
        assert decoding.timelock_info is None

    def test_batch_decoding_with_timelock(self) -> None:
        """Test BatchDecoding creation with timelock."""
        items = [BatchItem(target_contract="0x123", data="0xabcd")]
        timelock = TimelockInfo(delay=3600)
        decoding = BatchDecoding(items=items, timelock_info=timelock)

        assert len(decoding.items) == 1
        assert decoding.timelock_info is not None
        assert decoding.timelock_info.delay == 3600
