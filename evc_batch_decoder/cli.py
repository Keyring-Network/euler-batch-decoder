"""Command-line interface for EVC Batch Decoder."""

from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.panel import Panel
from web3 import Web3

from .decoder import EVCBatchDecoder

console = Console()


@click.command()
@click.argument("batch_data", required=False)
@click.option("--file", "-f", type=click.File("r"), help="Read batch data from file")
@click.option("--json-output", "-j", is_flag=True, help="Output results as JSON")
@click.option("--readme-format", "-m", is_flag=True, help="Output in README markdown format")
@click.option("--tx-hash", "-t", help="Load batch data from transaction hash (requires RPC)")
@click.option("--rpc-url", "-r", help="RPC URL for loading transaction data and fetching metadata")
@click.option("--chain-id", "-c", type=int, default=43114, help="Chain ID (default: 43114 for Avalanche)")
@click.version_option()
def decode_batch(
    batch_data: str | None,
    file: click.File | None,
    json_output: bool,
    readme_format: bool,
    tx_hash: str | None,
    rpc_url: str | None,
    chain_id: int,
) -> None:
    """
    Decode EVC batch transaction data and display human-readable operations.

    BATCH_DATA can be:
    - Hex-encoded transaction data (with or without 0x prefix)
    - JSON object with 'data' field
    - Raw transaction calldata

    Examples:

        # Decode from hex string
        evc-decode 0x72e94bf6000000000000000000000000...

        # Decode from file
        evc-decode --file batch.json

        # Decode from transaction hash
        evc-decode --tx-hash 0xabc123... --rpc-url https://eth.llamarpc.com

        # Output as JSON
        evc-decode --json-output 0x72e94bf6000000000000000000000000...
    """

    decoder = EVCBatchDecoder(chain_id=chain_id)

    # Set up Web3 client if RPC URL provided
    w3_client: Web3 | None = None
    if rpc_url:
        try:
            w3_client = Web3(Web3.HTTPProvider(rpc_url))
            console.print(f"[green]Connected to RPC: {rpc_url}[/green]")
        except (ConnectionError, ValueError, TypeError, OSError, Exception) as e:  # pylint: disable=broad-exception-caught
            console.print(f"[yellow]Warning: Failed to connect to RPC: {e}[/yellow]")

    # Determine input source
    input_data = None

    if tx_hash:
        if not rpc_url:
            console.print("[red]Error: --rpc-url is required when using --tx-hash[/red]")
            sys.exit(1)
        try:
            if w3_client is None:
                console.print("[red]Error: Web3 client not initialized[/red]")
                sys.exit(1)
            tx = w3_client.eth.get_transaction(tx_hash)  # type: ignore
            input_data = tx["input"].hex() if hasattr(tx["input"], "hex") else tx["input"]
            console.print(f"[green]✓[/green] Loaded transaction data from {tx_hash}")
        except (ConnectionError, ValueError, KeyError, TypeError, Exception) as e:  # pylint: disable=broad-exception-caught
            console.print(f"[red]Error loading transaction: {e}[/red]")
            sys.exit(1)

    elif file:
        try:
            # Click.File objects act like regular file objects
            content = file.read()  # type: ignore
            # Try to parse as JSON first
            try:
                parsed = json.loads(content)
                input_data = parsed
            except json.JSONDecodeError:
                # Treat as raw hex string
                input_data = content.strip()
        except (OSError, IOError, UnicodeDecodeError, ValueError, TypeError) as e:
            console.print(f"[red]Error reading file: {e}[/red]")
            sys.exit(1)

    elif batch_data:
        input_data = batch_data

    else:
        # Try to read from stdin
        stdin_data = sys.stdin.read().strip()
        if stdin_data:
            input_data = stdin_data
        else:
            console.print("[red]Error: No batch data provided. Use --help for usage information.[/red]")
            sys.exit(1)

    try:
        # Decode the batch
        console.print("[dim]Decoding batch data...[/dim]")
        batch_decoding = decoder.decode_batch_data(input_data)

        # Analyze the batch
        console.print("[dim]Analyzing operations...[/dim]")
        analysis = decoder.analyze_batch(batch_decoding, w3_client)

        if json_output:
            # Output as JSON
            result = {
                "batch": {
                    "items": [
                        {
                            "target_contract": item.target_contract,
                            "data": item.data,
                            "value": item.value,
                            "decoded": item.decoded,
                            "nested_batch": item.nested_batch.__dict__ if item.nested_batch else None,
                        }
                        for item in batch_decoding.items
                    ],
                    "timelock_info": batch_decoding.timelock_info.__dict__ if batch_decoding.timelock_info else None,
                },
                "analysis": analysis,
            }
            console.print(json.dumps(result, indent=2, default=str))
        elif readme_format:
            # README markdown format
            readme_output = decoder.format_readme_style(batch_decoding, analysis)
            console.print(readme_output)
        else:
            # Pretty formatted output
            console.print()
            decoder.format_output(batch_decoding, analysis)

            # Success message
            console.print(
                Panel.fit("[bold green]✅ Batch decoding completed successfully![/bold green]", border_style="green")
            )

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        console.print(f"[red]❌ Error decoding batch: {e}[/red]")
        if "--debug" in sys.argv:
            import traceback  # pylint: disable=import-outside-toplevel

            console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    decode_batch()  # pylint: disable=no-value-for-parameter
