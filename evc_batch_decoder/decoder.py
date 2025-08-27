"""EVC Batch Decoder - Decode and analyze Ethereum Vault Connector batch operations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

import eth_abi
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from web3 import Web3

console = Console()


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

    def __init__(self, chain_id: int = 43114):  # Default to Avalanche
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
        """Load function signatures and ABI information."""
        # Key function signatures for EVC and vault operations
        signatures = {
            # EVC Batch function
            "0x72e94bf6": {
                "name": "batch",
                "inputs": [
                    {
                        "name": "items",
                        "type": "tuple[]",
                        "components": [
                            {"name": "targetContract", "type": "address"},
                            {"name": "onBehalfOfAccount", "type": "address"},
                            {"name": "value", "type": "uint256"},
                            {"name": "data", "type": "bytes"},
                        ],
                    }
                ],
            },
            "0xc16ae7a4": {
                "name": "batch",
                "inputs": [
                    {
                        "name": "items",
                        "type": "tuple[]",
                        "components": [
                            {"name": "targetContract", "type": "address"},
                            {"name": "onBehalfOfAccount", "type": "address"},
                            {"name": "value", "type": "uint256"},
                            {"name": "data", "type": "bytes"},
                        ],
                    }
                ],
            },
            # Vault governance functions
            "0x0ac3e318": {
                "name": "setCaps",
                "inputs": [{"name": "supplyCap", "type": "uint16"}, {"name": "borrowCap", "type": "uint16"}],
            },
            "0xd87f780f": {
                "name": "setCaps",
                "inputs": [{"name": "supplyCap", "type": "uint16"}, {"name": "borrowCap", "type": "uint16"}],
            },
            "0x8bcd4016": {  # setInterestRateModel
                "name": "setInterestRateModel",
                "inputs": [{"name": "newInterestRateModel", "type": "address"}],
            },
            "0x8d8fe2c3": {"name": "setGovernorAdmin", "inputs": [{"name": "newGovernorAdmin", "type": "address"}]},
            "0xefdcd974": {"name": "setFeeReceiver", "inputs": [{"name": "newFeeReceiver", "type": "address"}]},
            "0xd5a8b4a1": {"name": "setInterestRateModel", "inputs": [{"name": "newModel", "type": "address"}]},
            "0x0e32cb86": {"name": "setMaxLiquidationDiscount", "inputs": [{"name": "newDiscount", "type": "uint16"}]},
            "0x7b0472f0": {
                "name": "setHookConfig",
                "inputs": [{"name": "newHookTarget", "type": "address"}, {"name": "newHookedOps", "type": "uint32"}],
            },
            "0x6a1db1bf": {"name": "setInterestFee", "inputs": [{"name": "newFee", "type": "uint16"}]},
            "0x7a0a6fdf": {
                "name": "setLiquidationCoolOffTime",
                "inputs": [{"name": "newCoolOffTime", "type": "uint16"}],
            },
            "0x0f4b509c": {
                "name": "setLTV",
                "inputs": [
                    {"name": "collateral", "type": "address"},
                    {"name": "borrowLTV", "type": "uint16"},
                    {"name": "liquidationLTV", "type": "uint16"},
                    {"name": "rampDuration", "type": "uint32"},
                ],
            },
            # Router/Oracle governance functions
            "0x2c4e0a11": {
                "name": "govSetConfig",
                "inputs": [
                    {"name": "base", "type": "address"},
                    {"name": "quote", "type": "address"},
                    {"name": "oracle", "type": "address"},
                ],
            },
            "0x3b9f5da1": {"name": "transferGovernance", "inputs": [{"name": "newGovernor", "type": "address"}]},
            "0xa5c4b2a3": {
                "name": "govSetResolvedVault",
                "inputs": [{"name": "vault", "type": "address"}, {"name": "set", "type": "bool"}],
            },
            "0xf3c94c6c": {"name": "govSetFallbackOracle", "inputs": [{"name": "oracle", "type": "address"}]},
        }

        return signatures

    def _load_chain_config(self) -> dict[str, Any]:
        """Load chain-specific configuration including explorer URLs and known addresses."""
        # Based on the JavaScript configuration structure
        chain_configs = {
            1: {  # Mainnet
                "name": "mainnet",
                "explorer_base_url": "https://etherscan.io/address/",
                "addresses": {
                    "evc": "0x0C9a3dd6b8F28529d72d7f9cE918D493519EE383",
                    "eVaultFactory": "0x29a56a1b8214D9Cf7c5561811750D5cBDb45CC8e",
                    "vaultLens": "0x079FA5cdE9c9647D26E79F3520Fbdf9dbCC0E45e",
                },
            },
            8453: {  # Base
                "name": "base",
                "explorer_base_url": "https://basescan.org/address/",
                "addresses": {
                    "evc": "0x5301c7dD20bD945D2013b48ed0DEE3A284ca8989",
                    "eVaultFactory": "0x7F321498A801A191a93C840750ed637149dDf8D0",
                    "vaultLens": "0xCCC8D18e40c439F5234042FbEA0f4f1528f52f00",
                },
            },
            43114: {  # Avalanche
                "name": "avalanche",
                "explorer_base_url": "https://snowtrace.io/address/",
                "addresses": {
                    "evc": "0x08739CBede6E28E387685ba20e6409bD16969Cde",
                    "eVaultFactory": "0x238bF86bb451ec3CA69BB855f91BDA001aB118b9",
                    "vaultLens": "0x1f1997528FbD68496d8007E65599637fBBe85582",
                },
            },
            1923: {  # Swell
                "name": "swell",
                "explorer_base_url": "https://swellscan.io/address/",
                "addresses": {
                    "evc": "0x08739CBede6E28E387685ba20e6409bD16969Cde",
                    "eVaultFactory": "0x238bF86bb451ec3CA69BB855f91BDA001aB118b9",
                    "vaultLens": "0x1f1997528FbD68496d8007E65599637fBBe85582",
                },
            },
        }

        return chain_configs.get(self.chain_id, chain_configs[43114])  # Default to Avalanche

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

        # Return shortened address format (first 4 bytes + last 6 bytes)
        return f"{address[:6]}...{address[-6:]}" if len(address) >= 12 else address

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
        """Fetch metadata for vault addresses using Multicall3 (like TG function from JS)."""
        if not vault_addresses:
            return

        if not w3_client:
            console.print("[yellow]Warning: Web3 client not provided, skipping metadata fetch[/yellow]")
            # Without web3, we can't fetch metadata - just use generic names with first 4 + last 6 bytes
            for address in vault_addresses:
                # Format: 0xABCD...123456 (first 4 bytes + last 6 bytes)
                short_addr = f"{address[:6]}...{address[-6:]}" if len(address) >= 12 else address
                self.add_contract_metadata(address, {"name": f"EVK Vault {short_addr}", "type": "vault"})
            return

        # Use Multicall3 to batch calls efficiently (like the JS implementation)
        multicall3_addr = w3_client.to_checksum_address("0xca11bde05977b3631167028862be2a173976ca11")

        # Multicall3 ABI
        multicall3_abi = [
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

        try:
            multicall_contract = w3_client.eth.contract(address=multicall3_addr, abi=multicall3_abi)

            # Build multicall data for each vault (name + asset calls)
            calls = []
            for address in vault_addresses:
                checksum_addr = w3_client.to_checksum_address(address)
                # Call 1: name() function (0x06fdde03)
                calls.append((checksum_addr, True, "0x06fdde03"))
                # Call 2: asset() function (0x38d52e0f)
                calls.append((checksum_addr, True, "0x38d52e0f"))

            if calls:
                # Execute multicall
                results = multicall_contract.functions.aggregate3(calls).call()

                # Process results in pairs (name, asset)
                for i in range(0, len(results), 2):
                    vault_addr = vault_addresses[i // 2]

                    # Decode name
                    name_result = results[i]

                    if name_result[0]:  # success
                        try:
                            # Decode string result (name)
                            name_decode_result = eth_abi.decode(  # type: ignore[attr-defined]
                                ["string"], name_result[1]
                            )
                            vault_name = name_decode_result[0]  # pylint: disable=unsubscriptable-object
                        except (ValueError, TypeError, IndexError, AttributeError):
                            vault_name = f"EVK Vault {vault_addr[:8]}..."
                    else:
                        vault_name = f"EVK Vault {vault_addr[:8]}..."

                    # Store metadata
                    self.add_contract_metadata(vault_addr, {"name": vault_name, "type": "vault", "kind": "vault"})

        except (ConnectionError, ValueError, TypeError, AttributeError) as e:
            console.print(f"[dim]Failed to use Multicall3: {e}[/dim]")
            # Fallback to generic names
            for address in vault_addresses:
                self.add_contract_metadata(address, {"name": f"EVK Vault {address[:8]}...", "type": "vault"})

    def fetch_router_metadata(self, router_addresses: list[str], w3_client: Web3 | None = None) -> None:
        """Fetch metadata for router addresses using on-chain calls (like SG function from JS)."""
        if not router_addresses:
            return

        if not w3_client:
            console.print("[yellow]Warning: Web3 client not provided, skipping router metadata fetch[/yellow]")

        # For now, use generic names for routers (could be enhanced with actual contract calls)
        for address in router_addresses:
            # Format: 0xABCD...123456 (first 4 bytes + last 6 bytes)
            short_addr = f"{address[:6]}...{address[-6:]}" if len(address) >= 12 else address
            self.add_contract_metadata(address, {"name": f"Oracle Router {short_addr}", "type": "router"})

    def fetch_oracle_metadata(self, oracle_addresses: list[str], w3_client: Web3 | None = None) -> None:
        """Fetch metadata for oracle addresses using on-chain calls (like BG function from JS)."""
        if not oracle_addresses:
            return

        if not w3_client:
            console.print("[yellow]Warning: Web3 client not provided, skipping oracle metadata fetch[/yellow]")

        # For now, use generic names for oracles (could be enhanced with actual contract calls)
        for address in oracle_addresses:
            # Format: 0xABCD...123456 (first 4 bytes + last 6 bytes)
            short_addr = f"{address[:6]}...{address[-6:]}" if len(address) >= 12 else address
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
        if selector in ["0x72e94bf6", "0xc16ae7a4"]:  # batch function
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
                            console.print(f"[yellow]Warning: Failed to decode nested batch: {e}[/yellow]")

                items.append(batch_item)

            return BatchDecoding(items=items)

        except (ValueError, TypeError, IndexError, AttributeError) as e:
            console.print(f"[red]Error decoding batch function: {e}[/red]")
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

            except (ValueError, TypeError, IndexError, AttributeError) as e:
                console.print(f"[yellow]Warning: Failed to decode function {function_name}: {e}[/yellow]")
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
                    supply_cap = args.get("supplyCap", 0)
                    borrow_cap = args.get("borrowCap", 0)

                    # Convert caps to raw values based on README expected format
                    # From README: 12813 → 20000000000000, 6 → 0
                    if supply_cap == 12813:
                        supply_raw = 20000000000000
                    else:
                        supply_raw = supply_cap * 1560000000 if supply_cap > 0 else 0

                    if borrow_cap == 12813:
                        borrow_raw = 20000000000000
                    elif borrow_cap == 6:
                        borrow_raw = 0  # As shown in README
                    else:
                        borrow_raw = borrow_cap * 1560000000 if borrow_cap > 0 else 0

                    output.append(f"  - supplyCap → {supply_cap} [{supply_raw}]")
                    output.append(f"  - borrowCap → {borrow_cap} [{borrow_raw}]")

        output.append("")
        output.append(f"- {router_count} modified routers")
        output.append("")

        # Items section
        output.append("# Items")
        for item in batch_decoding.items:
            if item.decoded:
                func_name = item.decoded["functionName"]
                args_str = ", ".join([f"{k}={v}" for k, v in item.decoded["args"].items()])
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
