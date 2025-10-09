# Decoder Scripts

Utility scripts for working with the EVC Batch Decoder.

## find_missing_selectors.py

Automatically identifies missing function selectors from batch transaction data.

### Usage

**From a SafeBatchBuilder JSON file:**
```bash
python scripts/find_missing_selectors.py --file batch.json
```

**From raw hex data:**
```bash
python scripts/find_missing_selectors.py 0xc16ae7a40000...
```

**From stdin (pipe):**
```bash
cat batch.json | python scripts/find_missing_selectors.py
```

### Output

The script will:
1. Extract all function selectors from the batch data
2. Check which ones are already in the decoder
3. Report missing selectors that need to be added
4. Provide hints on how to identify them

### Example Output

```
✅ Parsed SafeBatchBuilder JSON (chain 43114)

🔍 Analyzing batch data (5432 characters)...

📊 Found 5 unique function selector(s) in batch data

✅ Known selectors:
   0x4bca3d5b → setLTV
   0x06c570c1 → govSetConfig

❌ Missing selectors (need to be added to decoder):
   0xb4113ba7
   0xd1a3a308

💡 To identify these selectors:
   1. Search EVault ABI: cat euler-interfaces/abis/EVault.json | jq '.[] | select(.type == "function")' | grep -A 10 <pattern>
   2. Use cast: cast sig "functionName(type1,type2)"
   3. Check EulerRouter ABI if it's an oracle/router function

📝 Example decoder entry:
   "0xb4113ba7": {"name": "functionName", "inputs": [{"name": "param", "type": "address"}]},
```

### Workflow

1. **Get batch data** from a failed PR comment or deployment logs
2. **Run the script** to identify missing selectors
3. **Use the hints** to find the function names (search ABIs, use `cast sig`, etc.)
4. **Add to decoder** in `evc_batch_decoder/decoder.py`
5. **Re-run** to verify all selectors are now known

### Tips

- The script automatically filters out false positives (data that looks like selectors but isn't)
- Exit code 0 = all selectors known, 1 = missing selectors found
- Can be integrated into CI/CD to catch missing selectors automatically

