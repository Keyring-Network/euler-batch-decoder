#!/usr/bin/env python3
"""
Script to find missing function selectors from batch data.

Usage:
    python scripts/find_missing_selectors.py <hex_data>
    python scripts/find_missing_selectors.py --file batch.json
    cat batch.json | python scripts/find_missing_selectors.py
"""

import json
import re
import sys
from pathlib import Path


def extract_selectors_from_hex(hex_data: str) -> set[str]:
    """Extract all 4-byte function selectors from batch data."""
    # Remove 0x prefix if present
    if hex_data.startswith("0x"):
        hex_data = hex_data[2:]
    
    selectors = set()
    
    # EVC batch function selectors to skip (these are container functions, not the inner calls)
    evc_batch_selectors = {"0xc16ae7a4"}
    
    # Function selectors in EVC batch data appear after specific length indicators
    # Length: 00000044 (68 bytes) = 4-byte selector + 64 bytes params (common for single param functions)
    # Length: 00000064 (100 bytes) = 4-byte selector + 96 bytes params
    # Length: 00000084 (132 bytes) = 4-byte selector + 128 bytes params
    # Length: 00000024 (36 bytes) = 4-byte selector + 32 bytes params
    
    # Pattern: Look for common data lengths followed by what looks like a function selector
    # Valid selectors typically start with non-zero bytes and aren't all zeros/ones
    patterns = [
        r"00000024([0-9a-f]{8})",  # 36 bytes (1 param)
        r"00000044([0-9a-f]{8})",  # 68 bytes (2 params)  
        r"00000064([0-9a-f]{8})",  # 100 bytes (3 params)
        r"00000084([0-9a-f]{8})",  # 132 bytes (4 params)
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, hex_data, re.IGNORECASE):
            selector = f"0x{match.group(1)}"
            
            # Skip if it's an EVC batch selector
            if selector in evc_batch_selectors:
                continue
                
            # Skip if it looks like data (all zeros, sequential, etc.)
            if selector in ["0x00000000", "0x00000001", "0x00000020", "0x00000080"]:
                continue
            
            # Function selectors typically have at least one non-zero byte in first 2 bytes
            first_byte = int(selector[2:4], 16)
            if first_byte > 0:
                selectors.add(selector)
    
    return selectors


def load_known_selectors() -> dict[str, str]:
    """Load known selectors by parsing the decoder.py file."""
    # Find decoder.py file
    script_dir = Path(__file__).parent
    decoder_file = script_dir.parent / "evc_batch_decoder" / "decoder.py"
    
    if not decoder_file.exists():
        print(f"Warning: Could not find decoder.py at {decoder_file}")
        return {}
    
    # Parse the file to extract selectors
    known = {}
    content = decoder_file.read_text()
    
    # Find all selector definitions like: "0x12345678": {"name": "functionName", ...}
    pattern = r'"(0x[0-9a-f]{8})":\s*\{\s*"name":\s*"([^"]+)"'
    for match in re.finditer(pattern, content, re.IGNORECASE):
        selector = match.group(1)
        name = match.group(2)
        known[selector] = name
    
    return known


def main():
    # Parse input
    if len(sys.argv) > 1:
        if sys.argv[1] == "--file":
            if len(sys.argv) < 3:
                print("Error: --file requires a filename")
                sys.exit(1)
            with open(sys.argv[2]) as f:
                content = f.read()
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print(__doc__)
            sys.exit(0)
        else:
            content = sys.argv[1]
    else:
        # Read from stdin
        content = sys.stdin.read().strip()
    
    if not content:
        print("Error: No input provided")
        print(__doc__)
        sys.exit(1)
    
    # Try to parse as JSON first (SafeBatchBuilder format)
    hex_data = None
    try:
        data = json.loads(content)
        if "transactions" in data and len(data["transactions"]) > 0:
            # SafeBatchBuilder format
            hex_data = data["transactions"][0]["data"]
            print(f"✅ Parsed SafeBatchBuilder JSON (chain {data.get('chainId', 'unknown')})")
        elif "data" in data:
            # Simple transaction format
            hex_data = data["data"]
            print("✅ Parsed transaction JSON")
    except json.JSONDecodeError:
        # Assume it's raw hex
        hex_data = content.strip()
        if not hex_data.startswith("0x"):
            hex_data = "0x" + hex_data
        print("✅ Using raw hex input")
    
    if not hex_data:
        print("Error: Could not extract hex data from input")
        sys.exit(1)
    
    print(f"\n🔍 Analyzing batch data ({len(hex_data)} characters)...\n")
    
    # Extract selectors
    found_selectors = extract_selectors_from_hex(hex_data)
    print(f"📊 Found {len(found_selectors)} unique function selector(s) in batch data\n")
    
    # Load known selectors
    known_selectors = load_known_selectors()
    
    # Categorize
    missing = []
    known = []
    
    for selector in sorted(found_selectors):
        if selector in known_selectors:
            known.append((selector, known_selectors[selector]))
        else:
            missing.append(selector)
    
    # Display results
    if known:
        print("✅ Known selectors:")
        for selector, name in known:
            print(f"   {selector} → {name}")
        print()
    
    if missing:
        print("❌ Missing selectors (need to be added to decoder):")
        for selector in missing:
            print(f"   {selector}")
        print()
        print("💡 To identify these selectors:")
        print("   1. Search EVault ABI: cat euler-interfaces/abis/EVault.json | jq '.[] | select(.type == \"function\")' | grep -A 10 <pattern>")
        print("   2. Use cast: cast sig \"functionName(type1,type2)\"")
        print("   3. Check EulerRouter ABI if it's an oracle/router function")
        print()
        print("📝 Example decoder entry:")
        for selector in missing[:1]:  # Show example for first missing
            print(f'   "{selector}": {{"name": "functionName", "inputs": [{{"name": "param", "type": "address"}}]}},')
    else:
        print("🎉 All selectors are already in the decoder!")
    
    # Exit code
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()

