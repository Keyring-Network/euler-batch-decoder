# EVC Batch Decoder

![CI Pipeline](https://github.com/Keyring-Network/euler-batch-decoder/workflows/CI%20Pipeline/badge.svg)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

A Python tool to decode and analyze Ethereum Vault Connector (EVC) batch operations. This tool converts complex batch transaction data into human-readable operations, making it easy to understand what governance changes and vault operations are being performed.

> **✨ Built with modern CI/CD**: Automated testing, linting, formatting, and type checking via GitHub Actions.  
> **🚀 Quality First**: 100% test coverage, perfect linting scores, and comprehensive type checking.

## Features

- **Decode EVC Batch Operations**: Parse batch transaction data and decode individual operations
- **Governance Analysis**: Identify and analyze governance operations like `setCaps`, `setLTV`, `setGovernorAdmin`, etc.
- **Pretty Output**: Rich, colorful terminal output with tables, trees, and panels
- **Multiple Input Formats**: Support for hex strings, JSON objects, files, and direct transaction hash loading
- **Nested Batch Support**: Handle nested batch operations within batch calls
- **Multiple Output Formats**: Pretty terminal output, JSON export, and README-style markdown
- **Contract Name Resolution**: Display human-readable contract names instead of just addresses

## Installation

```bash
# Clone the repository
cd evc-batch-decoder

# Install using uv (recommended)
uv pip install -e .

# The CLI tool will be available as 'evc-decode'
```

## Usage

### Command Line Interface

```bash
# Decode from hex string (--chain-id is required and selects the explorer links)
evc-decode --chain-id 42161 0xc16ae7a400000000000000000000000000000000...

# Decode from file
evc-decode --chain-id 42161 --file batch_data.json

# Decode from transaction hash (requires RPC)
evc-decode --chain-id 1 --tx-hash 0xabc123... --rpc-url https://eth.llamarpc.com

# Output as JSON
evc-decode --chain-id 42161 --json-output 0xc16ae7a400000000000000000000000000000000...

# Output in README markdown format, with vault names, oracle names and current caps
# read on chain (without --rpc-url the current caps show as "unknown")
evc-decode --chain-id 42161 --rpc-url https://arb1.arbitrum.io/rpc --readme-format 0xc16ae7a400000000000000000000000000000000...

# Read from stdin
cat batch_data.txt | evc-decode --chain-id 42161
```

### Python API

```python
from evc_batch_decoder import EVCBatchDecoder

decoder = EVCBatchDecoder(chain_id=42161)

# Decode batch data
batch_data = "0xc16ae7a400000000000000000000000000000000..."
batch_decoding = decoder.decode_batch_data(batch_data)

# Analyze the batch
analysis = decoder.analyze_batch(batch_decoding)

# Format and display results
decoder.format_output(batch_decoding, analysis)

# Get README-style output
readme_output = decoder.format_readme_style(batch_decoding, analysis)
print(readme_output)
```

## Utility Scripts

### Find Missing Selectors

Automatically identify unknown function selectors from batch data:

```bash
# From a batch file
python scripts/find_missing_selectors.py --file batch.json

# From raw hex
python scripts/find_missing_selectors.py 0xc16ae7a40000...

# From stdin
cat batch.json | python scripts/find_missing_selectors.py
```

The script will report which selectors are unknown and need to be added to the decoder. See [scripts/README.md](scripts/README.md) for more details.

## Supported Chains

| Chain ID | Network | Explorer |
|---|---|---|
| 1 | Ethereum | etherscan.io |
| 10 | Optimism | optimistic.etherscan.io |
| 137 | Polygon | polygonscan.com |
| 1923 | Swell | swellscan.io |
| 8453 | Base | basescan.org |
| 42161 | Arbitrum One | arbiscan.io |
| 43114 | Avalanche | snowtrace.io |
| 59144 | Linea | lineascan.build |

Any other chain ID is rejected. EVC, EVault factory and vault lens addresses come from
[euler-interfaces](https://github.com/euler-xyz/euler-interfaces); Optimism has no Euler deployment listed there.

## Cap Units

`setCaps` takes EVK `AmountCap` values: the low 6 bits are a decimal exponent and the high 10 bits a
mantissa scaled by 100, so the amount is `10**(raw & 63) * (raw >> 6) / 100` in the asset's smallest unit.
Zero means no cap. README output shows each cap as `raw [amount]` on both sides of the change, for example
`supplyCap (current): 6 [0] → 6410 [10000000000]`.

The left value is read with `caps()` when `--rpc-url` is given. A vault created after the snapshot block shows
`not deployed`. With `--tx-hash` the read uses the state at the end
of the previous block and is labelled `(previous-block snapshot, block N)`. Earlier transactions in the
transaction's block may change caps or deploy a vault, so this snapshot can differ from the transaction's
actual starting state. Exact starting values require transaction tracing or replay. Raw batch data has no
block, so the read uses the latest block and is labelled `(current)`. A later transaction may have changed it.

Names read from chain (vault and oracle `name()`) are made safe for markdown before they appear in README output:
backticks become quotes, square brackets become parentheses, whitespace and newlines collapse to single spaces,
non-printable characters are dropped and names longer than 64 characters are truncated.

## Supported Operations

The decoder recognizes and analyzes the following EVC and vault operations:

### Vault Governance Operations
- `setCaps` - Set supply and borrow caps
- `setGovernorAdmin` - Change governance admin
- `setFeeReceiver` - Update fee receiver address
- `setInterestRateModel` - Change interest rate model
- `setMaxLiquidationDiscount` - Set liquidation discount
- `setHookConfig` - Configure hooks
- `setInterestFee` - Set interest fee
- `setLiquidationCoolOffTime` - Set liquidation cooloff period
- `setLTV` - Configure loan-to-value ratios

### Router/Oracle Operations
- `govSetConfig` - Set oracle configurations
- `transferGovernance` - Transfer governance control
- `govSetResolvedVault` - Configure resolved vaults
- `govSetFallbackOracle` - Set fallback oracle

## Example

### Test Case

```
0xc16ae7a400000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000001400000000000000000000000008f23da78e3f31ab5deb75dc3282198bed630ffde00000000000000000000000069cc425b1e5f302e7db4e5d125ab984ec5186364000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000044d87f780f000000000000000000000000000000000000000000000000000000000000320d000000000000000000000000000000000000000000000000000000000000320d00000000000000000000000000000000000000000000000000000000000000000000000000000000ea534105c2ccc0582d82b285aa47a6b446383d4400000000000000000000000069cc425b1e5f302e7db4e5d125ab984ec5186364000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000044d87f780f000000000000000000000000000000000000000000000000000000000000320d000000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000
```

### Expected Result (README format)

```bash
evc-decode --chain-id 43114 --readme-format <batch_data>
```

Output:
```md
# Changes: 2 modified vaults
- [EVK Vault eUSDC-15](https://snowtrace.io/address/0x8f23Da78e3F31Ab5DEb75dC3282198bed630ffde)
  - supplyCap (current): unknown → 12813 [20000000000000]
  - borrowCap (current): unknown → 12813 [20000000000000]

- [EVK Vault exUSDC-7](https://snowtrace.io/address/0xea534105c2ccC0582D82B285aA47A6B446383d44)
  - supplyCap (current): unknown → 12813 [20000000000000]
  - borrowCap (current): unknown → 6 [0]

- 0 modified routers

# Items
- [EVK Vault eUSDC-15](https://snowtrace.io/address/0x8f23Da78e3F31Ab5DEb75dC3282198bed630ffde) `.setCaps(supplyCap=12813, borrowCap=12813)`, onBehalfOf=[0x69cC...186364](https://snowtrace.io/address/0x69cC425B1E5f302e7Db4E5d125ab984EC5186364) , value=0
- [EVK Vault exUSDC-7](https://snowtrace.io/address/0xea534105c2ccC0582D82B285aA47A6B446383d44) `.setCaps(supplyCap=12813, borrowCap=6)`, onBehalfOf=[0x69cC...186364](https://snowtrace.io/address/0x69cC425B1E5f302e7Db4E5d125ab984EC5186364) , value=0
```

### Pretty Terminal Output

```bash
evc-decode --chain-id 43114 <batch_data>
```

Output:
```
╭───────────────────────────────╮
│ 🧙‍♂️ EVC Batch Decoder Results │
╰───────────────────────────────╯
          Batch Summary          
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Metric                ┃ Value ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Total Items           │ 2     │
│ Governance Operations │ 2     │
│ Vault Changes         │ 2     │
│ Router Changes        │ 0     │
│ Unknown Operations    │ 0     │
│ Nested Batches        │ 0     │
└───────────────────────┴───────┘

📋 Batch Items
├── Item 0
│   ├── Target: 0x8f23da78e3f31ab5deb75dc3282198bed630ffde
│   ├── Value: 0
│   ├── Function: setCaps
│   └── Arguments:
│       ├── supplyCap: 12813
│       └── borrowCap: 12813
└── Item 1
    ├── Target: 0xea534105c2ccc0582d82b285aa47a6b446383d44
    ├── Value: 0
    ├── Function: setCaps
    └── Arguments:
        ├── supplyCap: 12813
        └── borrowCap: 6

╭──────────────────────────╮
│ 🔧 Configuration Changes │
╰──────────────────────────╯
Vault Changes:
  0x8f23da78e3f31ab5deb75dc3282198bed630ffde:
    • setCaps(supplyCap=12813, borrowCap=12813)
  0xea534105c2ccc0582d82b285aa47a6b446383d44:
    • setCaps(supplyCap=12813, borrowCap=6)

╭───────────────────────────────────────────╮
│ ✅ Batch decoding completed successfully! │
╰───────────────────────────────────────────╯
```

## Output Formats

The tool provides multiple output formats:

1. **Pretty Terminal Output** (default): Rich, colorful display with tables and trees
2. **JSON Output** (`--json-output`): Structured JSON for programmatic use
3. **README Format** (`--readme-format`): Markdown format with contract names and links

## Contract Name Resolution

The decoder includes a mapping of known contract addresses to human-readable names:

- **EVK Vault eUSDC-15**: `0x8f23da78e3f31ab5deb75dc3282198bed630ffde`
- **EVK Vault exUSDC-7**: `0xea534105c2ccc0582d82b285aa47a6b446383d44`

Contract names can be extended by modifying the `_load_contract_names()` method in the decoder.

## Development

```bash
# Clone and setup
git clone <repo>
cd evc-batch-decoder

# Install in development mode
uv pip install -e .

# Run tests
uv run python test_readme_case.py

# Test CLI
uv run evc-decode --help
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License