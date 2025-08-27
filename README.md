# EVC Batch Decoder

![CI Pipeline](https://github.com/amc/euler-batch-decoder/workflows/CI%20Pipeline/badge.svg)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

A Python tool to decode and analyze Ethereum Vault Connector (EVC) batch operations. This tool converts complex batch transaction data into human-readable operations, making it easy to understand what governance changes and vault operations are being performed.

> **✨ Built with modern CI/CD**: Automated testing, linting, formatting, and type checking via GitHub Actions.

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
# Decode from hex string
evc-decode 0xc16ae7a400000000000000000000000000000000...

# Decode from file
evc-decode --file batch_data.json

# Decode from transaction hash (requires RPC)
evc-decode --tx-hash 0xabc123... --rpc-url https://eth.llamarpc.com

# Output as JSON
evc-decode --json-output 0xc16ae7a400000000000000000000000000000000...

# Output in README markdown format
evc-decode --readme-format 0xc16ae7a400000000000000000000000000000000...

# Read from stdin
cat batch_data.txt | evc-decode
```

### Python API

```python
from evc_batch_decoder import EVCBatchDecoder

decoder = EVCBatchDecoder()

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
evc-decode --readme-format <batch_data>
```

Output:
```md
# Changes: 2 modified vaults
- [EVK Vault eUSDC-15](https://snowtrace.io/address/0x8f23Da78e3F31Ab5DEb75dC3282198bed630ffde)
  - supplyCap → 12813 [20000000000000]
  - borrowCap → 12813 [20000000000000]

- [EVK Vault exUSDC-7](https://snowtrace.io/address/0xea534105c2ccC0582D82B285aA47A6B446383d44)
  - supplyCap → 12813 [20000000000000]
  - borrowCap → 6 [0]

- 0 modified routers

# Items
- [EVK Vault eUSDC-15](https://snowtrace.io/address/0x8f23Da78e3F31Ab5DEb75dC3282198bed630ffde) `.setCaps(supplyCap=12813, borrowCap=12813)`, onBehalfOf=[0x69cC...186364](https://snowtrace.io/address/0x69cC425B1E5f302e7Db4E5d125ab984EC5186364) , value=0
- [EVK Vault exUSDC-7](https://snowtrace.io/address/0xea534105c2ccC0582D82B285aA47A6B446383d44) `.setCaps(supplyCap=12813, borrowCap=6)`, onBehalfOf=[0x69cC...186364](https://snowtrace.io/address/0x69cC425B1E5f302e7Db4E5d125ab984EC5186364) , value=0
```

### Pretty Terminal Output

```bash
evc-decode <batch_data>
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