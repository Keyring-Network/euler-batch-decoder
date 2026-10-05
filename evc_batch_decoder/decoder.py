"""EVC Batch Decoder - Decode and analyze Ethereum Vault Connector batch operations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

import eth_abi
from eth_abi.exceptions import DecodingError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from web3 import Web3

# Pretty output goes to stdout; status and warning messages go to stderr so they never mix
# into README or JSON output.
console = Console()
status_console = Console(stderr=True)

# Euler EVC, EVault factory and vault lens addresses come from euler-xyz/euler-interfaces
# (addresses/<chainId>/CoreAddresses.json and LensAddresses.json). Optimism has no Euler
# deployment listed there, so it carries no known addresses.
CHAIN_CONFIGS: dict[int, dict[str, Any]] = {
    1: {
        "name": "mainnet",
        "explorer_base_url": "https://etherscan.io/address/",
        "addresses": {
            "evc": "0x0C9a3dd6b8F28529d72d7f9cE918D493519EE383",
            "eVaultFactory": "0x29a56a1b8214D9Cf7c5561811750D5cBDb45CC8e",
            "vaultLens": "0x4A7Bc3bf4db4dD6eEE1b2c27A7C9e35A6fD14bDE",
        },
    },
    10: {
        "name": "optimism",
        "explorer_base_url": "https://optimistic.etherscan.io/address/",
        "addresses": {},
    },
    137: {
        "name": "polygon",
        "explorer_base_url": "https://polygonscan.com/address/",
        "addresses": {
            "evc": "0x90811DacA4BD23Fc79A87FBdff7522bED2d24B4B",
            "eVaultFactory": "0xB1771a13e2a13fCafA89B00335915E732B9466b7",
            "vaultLens": "0x0979a2c164C132B79d78835A23D4A1EFeD4dee50",
        },
    },
    1923: {
        "name": "swell",
        "explorer_base_url": "https://swellscan.io/address/",
        "addresses": {
            "evc": "0x08739CBede6E28E387685ba20e6409bD16969Cde",
            "eVaultFactory": "0x238bF86bb451ec3CA69BB855f91BDA001aB118b9",
            "vaultLens": "0x1f1997528FbD68496d8007E65599637fBBe85582",
        },
    },
    8453: {
        "name": "base",
        "explorer_base_url": "https://basescan.org/address/",
        "addresses": {
            "evc": "0x5301c7dD20bD945D2013b48ed0DEE3A284ca8989",
            "eVaultFactory": "0x7F321498A801A191a93C840750ed637149dDf8D0",
            "vaultLens": "0x69a7584e4bC126a9C7fE2CCd0172bFdFa5D31f7c",
        },
    },
    42161: {
        "name": "arbitrum",
        "explorer_base_url": "https://arbiscan.io/address/",
        "addresses": {
            "evc": "0x6302ef0F34100CDDFb5489fbcB6eE1AA95CD1066",
            "eVaultFactory": "0x78Df1CF5bf06a7f27f2ACc580B934238C1b80D50",
            "vaultLens": "0xef639A4BD79Bf08523ADa43E6aD1b1222fBEC288",
        },
    },
    43114: {
        "name": "avalanche",
        "explorer_base_url": "https://snowtrace.io/address/",
        "addresses": {
            "evc": "0xddcbe30A761Edd2e19bba930A977475265F36Fa1",
            "eVaultFactory": "0xaf4B4c18B17F6a2B32F6c398a3910bdCD7f26181",
            "vaultLens": "0x2B4A17Acaa8b0d5c022bb20C17aB562A238297EF",
        },
    },
    59144: {
        "name": "linea",
        "explorer_base_url": "https://lineascan.build/address/",
        "addresses": {
            "evc": "0xd8CeCEe9A04eA3d941a959F68fb4486f23271d09",
            "eVaultFactory": "0x84711986Fd3BF0bFe4a8e6d7f4E22E67f7f27F04",
            "vaultLens": "0x59693978F5A8156573B090fEaB5b24c5D51a07D4",
        },
    },
}


MULTICALL3_ADDRESS = "0xca11bde05977b3631167028862be2a173976ca11"
MULTICALL3_ABI: list[dict[str, Any]] = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "target", "type": "address"},
                    {"name": "allowFailure", "type": "bool"},
                    {"name": "callData", "type": "bytes"},
                ],
                "name": "calls",
                "type": "tuple[]",
            }
        ],
        "name": "aggregate3",
        "outputs": [
            {
                "components": [{"name": "success", "type": "bool"}, {"name": "returnData", "type": "bytes"}],
                "name": "returnData",
                "type": "tuple[]",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    }
]


BATCH_SELECTOR = "0xc16ae7a4"  # EVC batch((address,address,uint256,bytes)[])
NAME_SELECTOR = "0x06fdde03"  # name()
CAPS_SELECTOR = "0x18e22d98"  # caps() on an EVault: raw (supplyCap, borrowCap) AmountCaps


def short_address(address: str) -> str:
    """Shorten an address to its first 4 and last 6 bytes, e.g. 0xABCD...123456."""
    return f"{address[:6]}...{address[-6:]}" if len(address) >= 12 else address


class UnsupportedChainError(ValueError):
    """Raised when the decoder has no explorer or address configuration for a chain."""

    def __init__(self, chain_id: int):
        supported = ", ".join(str(known) for known in sorted(CHAIN_CONFIGS))
        super().__init__(f"Unsupported chain ID {chain_id}. Supported chain IDs: {supported}")
        self.chain_id = chain_id


def decode_amount_cap(raw: int) -> int | None:
    """Resolve an EVK AmountCap to an amount in the asset's smallest unit.

    The low 6 bits are a decimal exponent and the high 10 bits a mantissa scaled by 100,
    so amount = 10**exponent * mantissa / 100. Zero means no cap and resolves to None.
    """
    if raw == 0:
        return None
    exponent: int = raw & 63
    mantissa: int = raw >> 6
    return int(10**exponent * mantissa // 100)


def format_amount_cap(raw: int | None) -> str:
    """Render a cap as `raw [resolved amount]`, the same units before and after a change."""
    if raw is None:
        return "unknown"
    amount = decode_amount_cap(raw)
    return f"{raw} [{'unlimited' if amount is None else amount}]"


@dataclass
class BatchItem:
    """Represents a single item in a batch operation."""

    target_contract: str
    data: str
    value: int = 0
    on_behalf_of: str = "0x0000000000000000000000000000000000000000"
    decoded: dict[str, Any] | None = None
    nested_batch: BatchDecoding | None = None


@dataclass
class TimelockInfo:
    """Information about timelock delays."""

    delay: int


@dataclass
class BatchDecoding:
    """Complete batch decoding result."""

    items: list[BatchItem]
    timelock_info: TimelockInfo | None = None


class EVCBatchDecoder:
    """Main decoder class for EVC batch operations."""

    def __init__(self, chain_id: int):
        self.w3 = Web3()
        self.chain_id = chain_id
        self.function_signatures = self._load_function_signatures()
        self.chain_config = self._load_chain_config()
        self.metadata: dict[str, Any] = {}  # Will be populated dynamically
        self.governance_functions = {
            "setCaps",
            "setGovernorAdmin",
            "setFeeReceiver",
            "setInterestRateModel",
            "setMaxLiquidationDiscount",
            "setHookConfig",
            "setInterestFee",
            "setLiquidationCoolOffTime",
            "setLTV",
            "govSetConfig",
            "transferGovernance",
            "govSetResolvedVault",
            "govSetFallbackOracle",
        }

    def _load_function_signatures(self) -> dict[str, dict[str, Any]]:
        """Build the selector table from canonical signatures so every selector matches its ABI."""
        signatures: dict[str, list[tuple[str, str]]] = {
            # EVC batch
            "batch": [("items", "(address,address,uint256,bytes)[]")],
            # Vault governance
            "setCaps": [("supplyCap", "uint16"), ("borrowCap", "uint16")],
            "setGovernorAdmin": [("newGovernorAdmin", "address")],
            "setFeeReceiver": [("newFeeReceiver", "address")],
            "setInterestRateModel": [("newModel", "address")],
            "setMaxLiquidationDiscount": [("newDiscount", "uint16")],
            "setHookConfig": [("newHookTarget", "address"), ("newHookedOps", "uint32")],
            "setInterestFee": [("newFee", "uint16")],
            "setLiquidationCoolOffTime": [("newCoolOffTime", "uint16")],
            "setLTV": [
                ("collateral", "address"),
                ("borrowLTV", "uint16"),
                ("liquidationLTV", "uint16"),
                ("rampDuration", "uint32"),
            ],
            # Router governance
            "govSetConfig": [("base", "address"), ("quote", "address"), ("oracle", "address")],
            "transferGovernance": [("newGovernor", "address")],
            "govSetResolvedVault": [("vault", "address"), ("set", "bool")],
            "govSetFallbackOracle": [("fallbackOracle", "address")],
        }

        table: dict[str, dict[str, Any]] = {}
        for name, params in signatures.items():
            canonical = f"{name}({','.join(param_type for _, param_type in params)})"
            selector = "0x" + Web3.keccak(text=canonical).hex().removeprefix("0x")[:8]
            table[selector] = {
                "name": name,
                "inputs": [{"name": param_name, "type": param_type} for param_name, param_type in params],
            }
        return table

    def _load_chain_config(self) -> dict[str, Any]:
        """Return the explorer URL and known Euler addresses for the configured chain.

        Raises UnsupportedChainError for a chain without a configuration, so a batch is never
        rendered with another chain's explorer links.
        """
        if self.chain_id not in CHAIN_CONFIGS:
            raise UnsupportedChainError(self.chain_id)
        return CHAIN_CONFIGS[self.chain_id]

    def get_contract_name(self, address: str) -> str:
        """Get the human-readable name for a contract address."""
        normalized_addr = address.lower()

        # Check if we have metadata for this address
        if normalized_addr in self.metadata:
            metadata = self.metadata[normalized_addr]
            if "name" in metadata:
                return str(metadata["name"])

        # Check if it's a known system address
        for addr_name, addr_value in self.chain_config.get("addresses", {}).items():
            if addr_value.lower() == normalized_addr:
                return f"EVC {addr_name}"

        return short_address(address)

    def get_contract_link(self, address: str) -> str:
        """Get a markdown link for a contract address."""
        name = self.get_contract_name(address)
        explorer_url = f"{self.chain_config['explorer_base_url']}{address}"
        return f"[{name}]({explorer_url})"

    def add_contract_metadata(self, address: str, metadata: dict[str, Any]) -> None:
        """Add metadata for a contract address."""
        self.metadata[address.lower()] = metadata

    def set_chain(self, chain_id: int) -> None:
        """Set the chain ID and reload chain configuration."""
        self.chain_id = chain_id
        self.chain_config = self._load_chain_config()

    def fetch_vault_metadata(self, vault_addresses: list[str], w3_client: Web3 | None = None) -> None:
        """Fetch each vault's name and current caps through Multicall3.

        A call that succeeds with empty return data hit an address without code, which means
        the vault is created later in the same deployment and has no current caps.
        """
        if not vault_addresses:
            return

        for address in vault_addresses:
            self.add_contract_metadata(address, {"name": f"EVK Vault {short_address(address)}", "type": "vault"})

        if not w3_client:
            status_console.print("[yellow]Warning: Web3 client not provided, skipping metadata fetch[/yellow]")
            return

        try:
            multicall_contract = w3_client.eth.contract(
                address=w3_client.to_checksum_address(MULTICALL3_ADDRESS), abi=MULTICALL3_ABI
            )
            calls = []
            for address in vault_addresses:
                checksum_addr = w3_client.to_checksum_address(address)
                calls.append((checksum_addr, True, NAME_SELECTOR))
                calls.append((checksum_addr, True, CAPS_SELECTOR))
            results = list(multicall_contract.functions.aggregate3(calls).call())
            if len(results) != len(calls):
                raise ValueError(f"Multicall3 returned {len(results)} results for {len(calls)} calls")
        except (ConnectionError, ValueError, TypeError, AttributeError, Exception) as e:  # pylint: disable=broad-exception-caught
            status_console.print(f"[dim]Failed to use Multicall3: {e}[/dim]")
            return

        for index, address in enumerate(vault_addresses):
            name_ok, name_data = results[2 * index]
            caps_ok, caps_data = results[2 * index + 1]
            metadata = self.metadata[address.lower()]
            metadata["kind"] = "vault"

            if name_ok and not name_data:
                metadata["deployed"] = False
                continue

            if name_ok:
                try:
                    metadata["name"] = str(eth_abi.decode(["string"], name_data)[0])  # type: ignore[attr-defined]
                    metadata["resolved"] = True
                except (ValueError, TypeError, IndexError, AttributeError, DecodingError):
                    pass

            if caps_ok:
                try:
                    supply_cap, borrow_cap = eth_abi.decode(["uint16", "uint16"], caps_data)  # type: ignore[attr-defined]
                    metadata["caps"] = {"supplyCap": supply_cap, "borrowCap": borrow_cap}
                except (ValueError, TypeError, IndexError, AttributeError, DecodingError):
                    pass

    def fetch_router_metadata(self, router_addresses: list[str], w3_client: Web3 | None = None) -> None:
        """Fetch metadata for router addresses using on-chain calls (like SG function from JS)."""
        if not router_addresses:
            return

        if not w3_client:
            status_console.print("[yellow]Warning: Web3 client not provided, skipping router metadata fetch[/yellow]")

        # For now, use generic names for routers (could be enhanced with actual contract calls)
        for address in router_addresses:
            self.add_contract_metadata(address, {"name": f"Oracle Router {short_address(address)}", "type": "router"})

    def fetch_oracle_metadata(self, oracle_addresses: list[str], w3_client: Web3 | None = None) -> None:
        """Fetch oracle adapter names via name() on each oracle, through Multicall3."""
        if not oracle_addresses:
            return

        names: dict[str, str] = {}
        if not w3_client:
            status_console.print("[yellow]Warning: Web3 client not provided, skipping oracle metadata fetch[/yellow]")
        else:
            try:
                multicall_contract = w3_client.eth.contract(
                    address=w3_client.to_checksum_address(MULTICALL3_ADDRESS), abi=MULTICALL3_ABI
                )
                calls = [(w3_client.to_checksum_address(address), True, NAME_SELECTOR) for address in oracle_addresses]
                results = list(multicall_contract.functions.aggregate3(calls).call())
                for address, (success, return_data) in zip(oracle_addresses, results, strict=True):
                    if not success:
                        continue
                    try:
                        names[address] = eth_abi.decode(["string"], return_data)[0]  # type: ignore[attr-defined]
                    except (ValueError, TypeError, IndexError, AttributeError, DecodingError):
                        continue
            except (ConnectionError, ValueError, TypeError, AttributeError, Exception) as e:  # pylint: disable=broad-exception-caught
                status_console.print(f"[dim]Failed to fetch oracle names: {e}[/dim]")

        for address in oracle_addresses:
            short_addr = short_address(address)
            if address in names:
                self.add_contract_metadata(
                    address, {"name": f"{names[address]} {short_addr}", "type": "oracle", "resolved": True}
                )
            else:
                self.add_contract_metadata(address, {"name": f"Oracle {short_addr}", "type": "oracle"})

    def decode_batch_data(self, data: str | bytes | dict[str, Any]) -> BatchDecoding:
        """Decode batch data from various input formats."""

        # Handle different input formats
        if isinstance(data, dict):
            if "data" in data:
                hex_data = data["data"]
            else:
                raise ValueError("Dictionary input must contain 'data' field")
        elif isinstance(data, str):
            if data.startswith("[") or data.startswith("{"):
                # JSON input
                parsed = json.loads(data)
                hex_data = parsed.get("data", data)
            else:
                hex_data = data
        else:
            hex_data = data.hex() if isinstance(data, bytes) else str(data)

        # Ensure hex format
        if not hex_data.startswith("0x"):
            hex_data = "0x" + hex_data

        hex_data = hex_data.lower()

        # Extract function selector
        if len(hex_data) < 10:
            raise ValueError("Data too short to contain function selector")

        selector = hex_data[:10]
        calldata = hex_data[10:]

        # Check if this is a batch function call
        if selector == BATCH_SELECTOR:
            return self._decode_batch_function(calldata)
        else:
            # Single function call - wrap it in a batch structure
            return self._decode_single_function(hex_data)

    def _decode_batch_function(self, calldata: str) -> BatchDecoding:
        """Decode the batch function calldata."""
        try:
            # Decode the batch items array
            calldata_bytes = bytes.fromhex(calldata)

            # The batch function takes an array of structs
            # Each struct has: (address targetContract, address onBehalfOfAccount, uint256 value, bytes data)
            decoded_result = eth_abi.decode(  # type: ignore[attr-defined]
                ["(address,address,uint256,bytes)[]"], calldata_bytes
            )
            decoded_data = decoded_result[0]  # pylint: disable=unsubscriptable-object

            items = []
            for item_data in decoded_data:  # pylint: disable=not-an-iterable
                target_contract, on_behalf_of, value, data = item_data

                batch_item = BatchItem(
                    target_contract=target_contract, data=data.hex(), value=value, on_behalf_of=on_behalf_of
                )

                # Try to decode the function call in the data
                if len(data) >= 4:
                    batch_item.decoded = self._decode_function_call(data)

                    # Check for nested batch calls
                    if batch_item.decoded and batch_item.decoded.get("functionName") == "batch":
                        try:
                            nested_batch = self._decode_batch_function(data[4:].hex())
                            batch_item.nested_batch = nested_batch
                        except (ValueError, TypeError, IndexError, AttributeError) as e:
                            status_console.print(f"[yellow]Warning: Failed to decode nested batch: {e}[/yellow]")

                items.append(batch_item)

            return BatchDecoding(items=items)

        except (ValueError, TypeError, IndexError, AttributeError) as e:
            status_console.print(f"[red]Error decoding batch function: {e}[/red]")
            raise

    def _decode_single_function(self, hex_data: str) -> BatchDecoding:
        """Decode a single function call and wrap it in batch structure."""
        data_bytes = bytes.fromhex(hex_data[2:])  # Remove 0x prefix

        batch_item = BatchItem(
            target_contract="0x0000000000000000000000000000000000000000",  # Unknown
            data=hex_data,
            value=0,
        )

        batch_item.decoded = self._decode_function_call(data_bytes)

        return BatchDecoding(items=[batch_item])

    def _decode_function_call(self, data: bytes) -> dict[str, Any] | None:
        """Decode a function call from its calldata."""
        if len(data) < 4:
            return None

        selector = data[:4].hex()
        selector_with_prefix = "0x" + selector

        if selector_with_prefix in self.function_signatures:
            sig_info = self.function_signatures[selector_with_prefix]
            function_name = sig_info["name"]
            inputs = sig_info["inputs"]

            try:
                # Decode the function arguments
                if inputs:
                    input_types = [inp["type"] for inp in inputs]
                    decoded_args = eth_abi.decode(input_types, data[4:])  # type: ignore[attr-defined]

                    # Create args dictionary
                    args = {}
                    for i, inp in enumerate(inputs):
                        value = decoded_args[i]  # pylint: disable=unsubscriptable-object
                        # Convert bytes to hex string for addresses and bytes
                        if inp["type"] == "address":
                            value = Web3.to_checksum_address(value)
                        elif inp["type"].startswith("bytes"):
                            value = value.hex() if isinstance(value, bytes) else value
                        args[inp["name"]] = value
                else:
                    args = {}

                return {"functionName": function_name, "selector": selector_with_prefix, "args": args}

            except (ValueError, TypeError, IndexError, AttributeError, DecodingError) as e:
                status_console.print(f"[yellow]Warning: Failed to decode function {function_name}: {e}[/yellow]")
                return {"functionName": function_name, "selector": selector_with_prefix, "args": {}, "error": str(e)}
        else:
            return {"functionName": "unknown", "selector": selector_with_prefix, "args": {}, "raw_data": data.hex()}

    def analyze_batch(self, batch_decoding: BatchDecoding, w3_client: Web3 | None = None) -> dict[str, Any]:
        """Analyze the batch for governance operations and generate insights."""
        analysis: dict[str, Any] = {
            "total_items": len(batch_decoding.items),
            "governance_operations": [],
            "vault_changes": {},
            "router_changes": {},
            "unknown_operations": [],
            "nested_batches": 0,
        }

        # Collect addresses that need metadata (like the JavaScript version)
        vault_addresses: set[str] = set()
        router_addresses: set[str] = set()
        oracle_addresses: set[str] = set()

        def collect_addresses_from_items(items: list[BatchItem]) -> None:
            for item in items:
                if item.nested_batch:
                    collect_addresses_from_items(item.nested_batch.items)

                if item.decoded:
                    func_name = item.decoded.get("functionName", "unknown")

                    # Collect addresses that need metadata based on function type
                    if func_name in [
                        "setCaps",
                        "setGovernorAdmin",
                        "setFeeReceiver",
                        "setInterestRateModel",
                        "setMaxLiquidationDiscount",
                        "setHookConfig",
                        "setInterestFee",
                        "setLiquidationCoolOffTime",
                        "setLTV",
                    ]:
                        vault_addresses.add(item.target_contract)

                    elif func_name in [
                        "govSetConfig",
                        "transferGovernance",
                        "govSetResolvedVault",
                        "govSetFallbackOracle",
                    ]:
                        router_addresses.add(item.target_contract)

                    # setLTV collateral is a vault too; fetch it so the item can show its name
                    if func_name == "setLTV" and "collateral" in item.decoded.get("args", {}):
                        vault_addresses.add(item.decoded["args"]["collateral"])

                    # Collect oracle addresses from function arguments
                    if func_name == "govSetConfig" and "oracle" in item.decoded.get("args", {}):
                        oracle_addresses.add(item.decoded["args"]["oracle"])

        # Collect all addresses that need metadata
        collect_addresses_from_items(batch_decoding.items)

        # Fetch metadata for collected addresses (like the JavaScript version)
        if vault_addresses:
            self.fetch_vault_metadata(list(vault_addresses), w3_client)
        if router_addresses:
            self.fetch_router_metadata(list(router_addresses), w3_client)
        if oracle_addresses:
            self.fetch_oracle_metadata(list(oracle_addresses), w3_client)

        # Now analyze the items
        for i, item in enumerate(batch_decoding.items):
            if item.nested_batch:
                analysis["nested_batches"] = cast(int, analysis["nested_batches"]) + 1
                # Recursively analyze nested batch
                nested_analysis = self.analyze_batch(item.nested_batch, w3_client)
                cast(list[Any], analysis["governance_operations"]).extend(nested_analysis["governance_operations"])

            if item.decoded:
                func_name = item.decoded.get("functionName", "unknown")

                if func_name in self.governance_functions:
                    cast(list[Any], analysis["governance_operations"]).append(
                        {
                            "index": i,
                            "function": func_name,
                            "target": item.target_contract,
                            "args": item.decoded.get("args", {}),
                        }
                    )

                    # Track changes by contract
                    if func_name in [
                        "setCaps",
                        "setGovernorAdmin",
                        "setFeeReceiver",
                        "setInterestRateModel",
                        "setMaxLiquidationDiscount",
                        "setHookConfig",
                        "setInterestFee",
                        "setLiquidationCoolOffTime",
                        "setLTV",
                    ]:
                        vault_changes = cast(dict[str, Any], analysis["vault_changes"])
                        if item.target_contract not in vault_changes:
                            vault_changes[item.target_contract] = []
                        vault_changes[item.target_contract].append(
                            {"function": func_name, "args": item.decoded.get("args", {})}
                        )

                    elif func_name in [
                        "govSetConfig",
                        "transferGovernance",
                        "govSetResolvedVault",
                        "govSetFallbackOracle",
                    ]:
                        router_changes = cast(dict[str, Any], analysis["router_changes"])
                        if item.target_contract not in router_changes:
                            router_changes[item.target_contract] = []
                        router_changes[item.target_contract].append(
                            {"function": func_name, "args": item.decoded.get("args", {})}
                        )

                elif func_name == "unknown":
                    cast(list[Any], analysis["unknown_operations"]).append(
                        {
                            "index": i,
                            "target": item.target_contract,
                            "selector": item.decoded.get("selector", ""),
                            "data_length": len(item.data) // 2 - 1,  # Convert hex length to bytes
                        }
                    )

        return analysis

    def _format_arg(self, value: Any) -> str:
        """Render an argument, naming an address whose name was resolved on chain."""
        if isinstance(value, str) and Web3.is_address(value):
            metadata = self.metadata.get(value.lower(), {})
            if metadata.get("resolved"):
                return f"{value} ({metadata['name']})"
        return str(value)

    def format_readme_style(self, batch_decoding: BatchDecoding, analysis: dict[str, Any]) -> str:
        """Format output in the README expected style."""
        output = []

        # Changes section
        vault_count = len(analysis["vault_changes"])
        router_count = len(analysis["router_changes"])

        output.append(f"# Changes: {vault_count} modified vaults")

        # Vault changes
        for vault_addr, changes in analysis["vault_changes"].items():
            vault_link = self.get_contract_link(vault_addr)
            output.append(f"- {vault_link}")

            for change in changes:
                if change["function"] == "setCaps":
                    args = change["args"]
                    vault_metadata = self.metadata.get(vault_addr.lower(), {})
                    current_caps = vault_metadata.get("caps", {})
                    for cap_name in ("supplyCap", "borrowCap"):
                        if vault_metadata.get("deployed") is False:
                            before = "not deployed"
                        else:
                            before = format_amount_cap(current_caps.get(cap_name))
                        after = format_amount_cap(args.get(cap_name, 0))
                        output.append(f"  - {cap_name}: {before} → {after}")

        output.append("")
        output.append(f"- {router_count} modified routers")
        output.append("")

        # Items section
        output.append("# Items")
        for item in batch_decoding.items:
            if item.decoded:
                func_name = item.decoded["functionName"]
                args_str = ", ".join(f"{k}={self._format_arg(v)}" for k, v in item.decoded["args"].items())
                target_link = self.get_contract_link(item.target_contract)
                behalf_link = self.get_contract_link(item.on_behalf_of)
                output.append(
                    f"- {target_link} `.{func_name}({args_str})`, onBehalfOf={behalf_link} , value={item.value}"
                )

        return "\n".join(output)

    def format_output(self, batch_decoding: BatchDecoding, analysis: dict[str, Any]) -> None:
        """Format and display the decoded batch information."""

        # Main header
        console.print(Panel.fit("[bold blue]🧙‍♂️ EVC Batch Decoder Results[/bold blue]", border_style="blue"))

        # Summary table
        summary_table = Table(title="Batch Summary", show_header=True, header_style="bold magenta")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")

        summary_table.add_row("Total Items", str(analysis["total_items"]))
        summary_table.add_row("Governance Operations", str(len(analysis["governance_operations"])))
        summary_table.add_row("Vault Changes", str(len(analysis["vault_changes"])))
        summary_table.add_row("Router Changes", str(len(analysis["router_changes"])))
        summary_table.add_row("Unknown Operations", str(len(analysis["unknown_operations"])))
        summary_table.add_row("Nested Batches", str(analysis["nested_batches"]))

        console.print(summary_table)
        console.print()

        # Timelock information
        if batch_decoding.timelock_info:
            console.print(
                Panel(
                    f"[bold green]⏱️  TIMELOCK DELAY: {batch_decoding.timelock_info.delay} seconds[/bold green]",
                    border_style="green",
                )
            )
            console.print()

        # Detailed items
        if batch_decoding.items:
            items_tree = Tree("[bold]📋 Batch Items[/bold]")

            for i, item in enumerate(batch_decoding.items):
                item_node = items_tree.add(f"[bold]Item {i}[/bold]")
                item_node.add(f"[dim]Target:[/dim] {item.target_contract}")
                item_node.add(f"[dim]Value:[/dim] {item.value}")

                if item.decoded:
                    func_name = item.decoded.get("functionName", "unknown")
                    if func_name in self.governance_functions:
                        item_node.add(f"[green]Function:[/green] {func_name}")
                    else:
                        item_node.add(f"[yellow]Function:[/yellow] {func_name}")

                    args = item.decoded.get("args", {})
                    if args:
                        args_node = item_node.add("[dim]Arguments:[/dim]")
                        for arg_name, arg_value in args.items():
                            args_node.add(f"{arg_name}: {arg_value}")
                else:
                    item_node.add(f"[red]Raw Data:[/red] {item.data[:20]}...")

                if item.nested_batch:
                    nested_node = item_node.add("[bold magenta]Nested Batch:[/bold magenta]")
                    for j, nested_item in enumerate(item.nested_batch.items):
                        nested_item_node = nested_node.add(f"Nested Item {j}")
                        if nested_item.decoded:
                            nested_item_node.add(f"Function: {nested_item.decoded.get('functionName', 'unknown')}")

            console.print(items_tree)
            console.print()

        # Governance changes summary
        if analysis["vault_changes"] or analysis["router_changes"]:
            console.print(Panel.fit("[bold]🔧 Configuration Changes[/bold]", border_style="yellow"))

            if analysis["vault_changes"]:
                console.print("[bold]Vault Changes:[/bold]")
                for vault_addr, changes in analysis["vault_changes"].items():
                    console.print(f"  [cyan]{vault_addr}[/cyan]:")
                    for change in changes:
                        args_str = ", ".join([f"{k}={v}" for k, v in change["args"].items()])
                        console.print(f"    • {change['function']}({args_str})")
                console.print()

            if analysis["router_changes"]:
                console.print("[bold]Router Changes:[/bold]")
                for router_addr, changes in analysis["router_changes"].items():
                    console.print(f"  [cyan]{router_addr}[/cyan]:")
                    for change in changes:
                        args_str = ", ".join([f"{k}={v}" for k, v in change["args"].items()])
                        console.print(f"    • {change['function']}({args_str})")
                console.print()

        # Unknown operations
        if analysis["unknown_operations"]:
            console.print(Panel.fit("[bold red]❓ Unknown Operations[/bold red]", border_style="red"))
            for op in analysis["unknown_operations"]:
                console.print(f"  Item {op['index']}: {op['selector']} → {op['target']} ({op['data_length']} bytes)")
            console.print()
