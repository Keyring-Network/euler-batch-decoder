"""Chain configuration, AmountCap units and metadata rendering for README output."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import eth_abi
import pytest
from click.testing import CliRunner
from web3 import Web3

from evc_batch_decoder.cli import decode_batch
from evc_batch_decoder.decoder import (
    CHAIN_CONFIGS,
    MAX_NAME_LENGTH,
    BatchDecoding,
    BatchItem,
    EVCBatchDecoder,
    UnsupportedChainError,
    decode_amount_cap,
    format_amount_cap,
    markdown_safe_name,
)

VAULT = "0x3ab3e7c8c633a2cd01229ecdc1c242eeb10a1966"
NEW_VAULT = "0xaa7a1abbb3c11f43b29659cedb3782ed34a16494"
ORACLE = "0x876D2A4846B4Deb893b65335FDA6Ac1cb7Af258a"
ROUTER = "0x1e878daab1190c7bf2c3719d416945bc636e82ad"
SAFE = "0x69cC425B1E5f302e7Db4E5d125ab984EC5186364"


def _set_caps_call(supply_cap: int, borrow_cap: int) -> bytes:
    selector = Web3.keccak(text="setCaps(uint16,uint16)")[:4]
    return selector + eth_abi.encode(["uint16", "uint16"], [supply_cap, borrow_cap])


def _batch_hex(items: list[tuple[str, bytes]]) -> str:
    selector = Web3.keccak(text="batch((address,address,uint256,bytes)[])")[:4]
    encoded = eth_abi.encode(
        ["(address,address,uint256,bytes)[]"],
        [[(Web3.to_checksum_address(target), SAFE, 0, data) for target, data in items]],
    )
    return "0x" + (selector + encoded).hex()


@pytest.mark.parametrize(
    ("chain_id", "explorer"),
    [
        (1, "https://etherscan.io/address/"),
        (10, "https://optimistic.etherscan.io/address/"),
        (137, "https://polygonscan.com/address/"),
        (8453, "https://basescan.org/address/"),
        (42161, "https://arbiscan.io/address/"),
        (43114, "https://snowtrace.io/address/"),
        (59144, "https://lineascan.build/address/"),
    ],
)
def test_chain_explorer_links(chain_id: int, explorer: str) -> None:
    """Each supported chain links addresses to its own explorer."""
    decoder = EVCBatchDecoder(chain_id=chain_id)
    assert decoder.get_contract_link(VAULT).endswith(f"({explorer}{VAULT})")


def test_arbitrum_evc_is_named() -> None:
    """The Arbitrum EVC from euler-interfaces resolves to a name."""
    decoder = EVCBatchDecoder(chain_id=42161)
    assert decoder.get_contract_name("0x6302ef0F34100CDDFb5489fbcB6eE1AA95CD1066") == "EVC evc"


def test_every_configured_address_is_checksummed() -> None:
    """Configured addresses are valid checksummed addresses."""
    for config in CHAIN_CONFIGS.values():
        for address in config["addresses"].values():
            assert Web3.is_checksum_address(address)


@pytest.mark.parametrize("chain_id", [999, 43113, 0])
def test_unknown_chain_raises(chain_id: int) -> None:
    """No silent fallback to another chain's explorer."""
    with pytest.raises(UnsupportedChainError):
        EVCBatchDecoder(chain_id=chain_id)


def test_set_chain_to_unknown_raises() -> None:
    """Switching to an unknown chain fails too."""
    decoder = EVCBatchDecoder(chain_id=42161)
    with pytest.raises(UnsupportedChainError):
        decoder.set_chain(999)


@pytest.mark.parametrize(
    ("raw", "amount"),
    [
        (0, None),  # no cap
        (6, 0),  # mantissa 0
        (18, 0),
        (6410, 10_000_000_000),  # 100 * 10**10 / 100 = 10k at 6 decimals
        (6422, 10_000 * 10**18),  # 10k at 18 decimals
        (12813, 20_000_000_000_000),
    ],
)
def test_decode_amount_cap(raw: int, amount: int | None) -> None:
    """AmountCap resolves as 10**(raw & 63) * (raw >> 6) / 100."""
    assert decode_amount_cap(raw) == amount


def test_format_amount_cap() -> None:
    """Caps render as raw plus resolved amount, or unknown."""
    assert format_amount_cap(6410) == "6410 [10000000000]"
    assert format_amount_cap(0) == "0 [unlimited]"
    assert format_amount_cap(None) == "unknown"


def _caps_batch(vault: str, supply_cap: int, borrow_cap: int) -> tuple[BatchDecoding, dict[str, Any]]:
    args = {"supplyCap": supply_cap, "borrowCap": borrow_cap}
    batch = BatchDecoding(
        items=[BatchItem(target_contract=vault, data="0x", decoded={"functionName": "setCaps", "args": args})]
    )
    analysis = {"vault_changes": {vault: [{"function": "setCaps", "args": args}]}, "router_changes": {}}
    return batch, analysis


def test_readme_caps_before_and_after_share_units() -> None:
    """Before and after are both `raw [amount]`, so the diff compares like with like."""
    decoder = EVCBatchDecoder(chain_id=42161)
    decoder.add_contract_metadata(VAULT, {"name": "EVK Vault eUSD₮0-8", "caps": {"supplyCap": 6, "borrowCap": 6}})
    batch, analysis = _caps_batch(VAULT, 6410, 6410)

    output = decoder.format_readme_style(batch, analysis)

    assert "  - supplyCap (current): 6 [0] → 6410 [10000000000]" in output
    assert "  - borrowCap (current): 6 [0] → 6410 [10000000000]" in output
    assert f"[EVK Vault eUSD₮0-8](https://arbiscan.io/address/{VAULT})" in output


def test_readme_caps_for_vault_created_in_same_batch() -> None:
    """A vault without code has no current caps."""
    decoder = EVCBatchDecoder(chain_id=42161)
    decoder.add_contract_metadata(NEW_VAULT, {"name": "EVK Vault x", "deployed": False})
    batch, analysis = _caps_batch(NEW_VAULT, 6422, 18)

    output = decoder.format_readme_style(batch, analysis)

    assert "  - supplyCap (current): not deployed → 6422 [10000000000000000000000]" in output
    assert "  - borrowCap (current): not deployed → 18 [0]" in output


def test_historical_undeployed_vault_is_scoped_to_snapshot_block() -> None:
    """An address without code at the snapshot block may be deployed earlier in the transaction's block."""
    decoder = EVCBatchDecoder(chain_id=42161)
    decoder.add_contract_metadata(NEW_VAULT, {"name": "EVK Vault x", "deployed": False})
    batch, analysis = _caps_batch(NEW_VAULT, 6422, 18)
    analysis["state_block"] = 122

    output = decoder.format_readme_style(batch, analysis)

    assert "borrowCap (previous-block snapshot, block 122): not deployed → 18 [0]" in output
    assert "Earlier transactions in the transaction's block may change caps or deploy a vault." in output
    assert "(before," not in output


def _mock_multicall(results: list[tuple[bool, bytes]]) -> Mock:
    w3 = Mock()
    w3.to_checksum_address.side_effect = Web3.to_checksum_address
    w3.eth.contract.return_value.functions.aggregate3.return_value.call.return_value = results
    return w3


def test_fetch_vault_metadata_reads_name_and_caps() -> None:
    """One multicall reads name() and caps() per vault; empty return data marks an undeployed vault."""
    decoder = EVCBatchDecoder(chain_id=42161)
    w3 = _mock_multicall(
        [
            (True, eth_abi.encode(["string"], ["EVK Vault eUSD₮0-8"])),
            (True, eth_abi.encode(["uint16", "uint16"], [6, 7])),
            (True, b""),
            (True, b""),
        ]
    )

    decoder.fetch_vault_metadata([VAULT, NEW_VAULT], w3)

    assert decoder.metadata[VAULT]["name"] == "EVK Vault eUSD₮0-8"
    assert decoder.metadata[VAULT]["caps"] == {"supplyCap": 6, "borrowCap": 7}
    assert decoder.metadata[NEW_VAULT]["deployed"] is False
    assert decoder.metadata[NEW_VAULT]["name"] == "EVK Vault 0xaa7a...a16494"


def test_fetch_vault_metadata_rejects_short_multicall_result() -> None:
    """A result count mismatch keeps generic names instead of misattributing data."""
    decoder = EVCBatchDecoder(chain_id=42161)
    w3 = _mock_multicall([(True, eth_abi.encode(["string"], ["EVK Vault eUSD₮0-8"]))])

    decoder.fetch_vault_metadata([VAULT], w3)

    assert decoder.metadata[VAULT]["name"] == "EVK Vault 0x3ab3...0a1966"
    assert "caps" not in decoder.metadata[VAULT]


def test_oracle_names_annotate_items() -> None:
    """A resolved oracle name appears next to the oracle argument."""
    decoder = EVCBatchDecoder(chain_id=42161)
    decoder.fetch_oracle_metadata([ORACLE], _mock_multicall([(True, eth_abi.encode(["string"], ["ChainlinkOracle"]))]))
    args = {"base": VAULT, "quote": "0x0000000000000000000000000000000000000348", "oracle": ORACLE}
    batch = BatchDecoding(
        items=[
            BatchItem(
                target_contract=ROUTER,
                data="0x",
                on_behalf_of=SAFE,
                decoded={"functionName": "govSetConfig", "args": args},
            )
        ]
    )

    output = decoder.format_readme_style(batch, {"vault_changes": {}, "router_changes": {}})

    assert f"oracle={ORACLE} (ChainlinkOracle 0x876D...Af258a)" in output
    assert "quote=0x0000000000000000000000000000000000000348," in output


@pytest.mark.parametrize(
    ("selector", "name"),
    [
        ("0xc16ae7a4", "batch"),
        ("0xd87f780f", "setCaps"),
        ("0x4bca3d5b", "setLTV"),
        ("0x60cb90ef", "setInterestFee"),
        ("0x82ebd674", "setGovernorAdmin"),
        ("0x06c570c1", "govSetConfig"),
        ("0xd38bfff4", "transferGovernance"),
        ("0xeab49501", "govSetFallbackOracle"),
    ],
)
def test_selectors_match_canonical_signatures(selector: str, name: str) -> None:
    """Selectors are keccak-derived, so EVK calls such as setInterestFee decode by name."""
    decoder = EVCBatchDecoder(chain_id=42161)
    assert decoder.function_signatures[selector]["name"] == name


def test_cli_requires_chain_id() -> None:
    """Omitting --chain-id is a usage error, not a silent Avalanche default."""
    result = CliRunner().invoke(decode_batch, [_batch_hex([(VAULT, _set_caps_call(6410, 6410))])])
    assert result.exit_code == 2
    assert "--chain-id" in result.output


def test_cli_unknown_chain_exits() -> None:
    """An unsupported chain stops the CLI with the supported list."""
    result = CliRunner().invoke(decode_batch, ["--chain-id", "999", _batch_hex([(VAULT, _set_caps_call(1, 1))])])
    assert result.exit_code == 1
    assert "Unsupported chain ID 999" in result.output


def test_cli_readme_stdout_is_clean_and_unwrapped() -> None:
    """README output on stdout carries no status lines and no line-wrapped links."""
    result = CliRunner().invoke(
        decode_batch, ["--chain-id", "42161", "--readme-format", _batch_hex([(VAULT, _set_caps_call(6410, 6410))])]
    )

    assert result.exit_code == 0
    assert result.stdout.startswith("# Changes: 1 modified vaults\n")
    assert f"(https://arbiscan.io/address/{VAULT})" in result.stdout
    assert "Decoding batch data" not in result.stdout
    assert "Decoding batch data" in result.stderr
    assert "  - supplyCap (current): unknown → 6410 [10000000000]" in result.stdout


@patch("evc_batch_decoder.cli.Web3")
def test_cli_never_prints_rpc_url(mock_web3: Mock) -> None:
    """RPC URLs often embed API keys, so the CLI must not echo them."""
    mock_web3.return_value = Mock()
    secret_url = "https://arb-mainnet.example/v2/SECRET_API_KEY"

    result = CliRunner().invoke(
        decode_batch,
        [
            "--chain-id",
            "42161",
            "--rpc-url",
            secret_url,
            "--readme-format",
            _batch_hex([(VAULT, _set_caps_call(1, 1))]),
        ],
    )

    assert result.exit_code == 0
    assert "SECRET_API_KEY" not in result.output


def test_fetch_vault_metadata_reads_at_state_block() -> None:
    """Vault reads use the given snapshot block."""
    decoder = EVCBatchDecoder(chain_id=42161)
    w3 = _mock_multicall(
        [(True, eth_abi.encode(["string"], ["v"])), (True, eth_abi.encode(["uint16", "uint16"], [6, 7]))]
    )

    decoder.fetch_vault_metadata([VAULT], w3, 122)

    w3.eth.contract.return_value.functions.aggregate3.return_value.call.assert_called_once_with(block_identifier=122)


def test_fetch_vault_metadata_defaults_to_latest_block() -> None:
    """Without a state block the vault reads use the latest block."""
    decoder = EVCBatchDecoder(chain_id=42161)
    w3 = _mock_multicall(
        [(True, eth_abi.encode(["string"], ["v"])), (True, eth_abi.encode(["uint16", "uint16"], [6, 7]))]
    )

    decoder.fetch_vault_metadata([VAULT], w3)

    w3.eth.contract.return_value.functions.aggregate3.return_value.call.assert_called_once_with(
        block_identifier="latest"
    )


def _mock_cli_web3(mock_web3: Mock, tx: dict[str, Any] | None) -> Mock:
    w3 = _mock_multicall(
        [
            (True, eth_abi.encode(["string"], ["EVK Vault eUSD₮0-8"])),
            (True, eth_abi.encode(["uint16", "uint16"], [6, 6])),
        ]
    )
    w3.eth.get_transaction.return_value = tx
    mock_web3.return_value = w3
    return w3


@pytest.mark.parametrize("transaction_index", [0, 1])
@patch("evc_batch_decoder.cli.Web3")
def test_cli_tx_hash_labels_caps_as_previous_block_snapshot(mock_web3: Mock, transaction_index: int) -> None:
    """Even a later transaction's historical caps describe a snapshot, not its exact starting state."""
    # At block 122 the caps are 6. For index 1, an earlier transaction in block 123 may
    # already have changed them to 12813; the snapshot read cannot include that change.
    w3 = _mock_cli_web3(
        mock_web3,
        {
            "input": _batch_hex([(VAULT, _set_caps_call(6410, 6410))]),
            "blockNumber": 123,
            "transactionIndex": transaction_index,
        },
    )

    result = CliRunner().invoke(
        decode_batch,
        ["--chain-id", "42161", "--rpc-url", "https://rpc.example", "--tx-hash", "0xabc", "--readme-format"],
    )

    assert result.exit_code == 0, result.output
    w3.eth.contract.return_value.functions.aggregate3.return_value.call.assert_called_once_with(block_identifier=122)
    assert "  - supplyCap (previous-block snapshot, block 122): 6 [0] → 6410 [10000000000]" in result.stdout
    assert "  - borrowCap (previous-block snapshot, block 122): 6 [0] → 6410 [10000000000]" in result.stdout
    assert "Historical caps use the snapshot at the end of block 122." in result.stdout
    assert "Earlier transactions in the transaction's block may change caps or deploy a vault." in result.stdout
    assert "(before," not in result.stdout
    assert "(current)" not in result.stdout


@patch("evc_batch_decoder.cli.Web3")
def test_cli_pending_tx_hash_reads_current_caps(mock_web3: Mock) -> None:
    """A pending transaction has no block, so its caps are the latest state and labelled current."""
    w3 = _mock_cli_web3(mock_web3, {"input": _batch_hex([(VAULT, _set_caps_call(6410, 6410))]), "blockNumber": None})

    result = CliRunner().invoke(
        decode_batch,
        ["--chain-id", "42161", "--rpc-url", "https://rpc.example", "--tx-hash", "0xabc", "--readme-format"],
    )

    assert result.exit_code == 0, result.output
    w3.eth.contract.return_value.functions.aggregate3.return_value.call.assert_called_once_with(
        block_identifier="latest"
    )
    assert "  - supplyCap (current): 6 [0] → 6410 [10000000000]" in result.stdout
    assert "previous-block snapshot" not in result.stdout
    assert "Historical caps" not in result.stdout


@patch("evc_batch_decoder.cli.Web3")
def test_cli_raw_data_labels_caps_current(mock_web3: Mock) -> None:
    """Raw batch data has no block, so its caps are read at the latest block and labelled current."""
    w3 = _mock_cli_web3(mock_web3, None)

    result = CliRunner().invoke(
        decode_batch,
        [
            "--chain-id",
            "42161",
            "--rpc-url",
            "https://rpc.example",
            "--readme-format",
            _batch_hex([(VAULT, _set_caps_call(6410, 6410))]),
        ],
    )

    assert result.exit_code == 0, result.output
    w3.eth.get_transaction.assert_not_called()
    w3.eth.contract.return_value.functions.aggregate3.return_value.call.assert_called_once_with(
        block_identifier="latest"
    )
    assert "  - supplyCap (current): 6 [0] → 6410 [10000000000]" in result.stdout
    assert "before" not in result.stdout
    assert "previous-block snapshot" not in result.stdout
    assert "Historical caps" not in result.stdout


HOSTILE_NAME = "Evil` `.drain()`\n- [click](https://evil.example)\r\n\t\x00" + "A" * 200


def test_markdown_safe_name_neutralises_hostile_name() -> None:
    """Backticks, brackets, newlines and control characters cannot escape the README line or code span."""
    safe = markdown_safe_name(HOSTILE_NAME)

    assert len(safe) == MAX_NAME_LENGTH
    assert safe.endswith("…")
    assert not any(char in safe for char in "`[]\n\r\t\x00")
    assert safe.startswith("Evil' '.drain()' - (click)(https://evil.example) AAAA")


def test_hostile_names_keep_readme_items_on_one_line() -> None:
    """Hostile vault and oracle names stay inside their item, code span and link text."""
    decoder = EVCBatchDecoder(chain_id=42161)
    decoder.fetch_oracle_metadata([ORACLE], _mock_multicall([(True, eth_abi.encode(["string"], [HOSTILE_NAME]))]))
    decoder.fetch_vault_metadata(
        [VAULT],
        _mock_multicall(
            [(True, eth_abi.encode(["string"], [HOSTILE_NAME])), (True, eth_abi.encode(["uint16", "uint16"], [6, 6]))]
        ),
    )
    args = {"base": VAULT, "quote": "0x0000000000000000000000000000000000000348", "oracle": ORACLE}
    batch = BatchDecoding(
        items=[
            BatchItem(
                target_contract=ROUTER,
                data="0x",
                on_behalf_of=SAFE,
                decoded={"functionName": "govSetConfig", "args": args},
            ),
            BatchItem(target_contract=VAULT, data="0x", decoded={"functionName": "setCaps", "args": {}}),
        ]
    )

    output = decoder.format_readme_style(batch, {"vault_changes": {}, "router_changes": {}})
    items = output.split("# Items\n", 1)[1].split("\n")

    assert len(items) == 2
    for line in items:
        assert line.startswith("- [")
        assert line.count("`") == 2
        assert "](https://evil.example)" not in line
    assert f"[{markdown_safe_name(HOSTILE_NAME)}](https://arbiscan.io/address/{VAULT})" in items[1]
