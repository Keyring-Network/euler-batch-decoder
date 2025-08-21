#!/usr/bin/env python3
"""Update the decoder with comprehensive function signatures."""

import json

# Generated comprehensive function signatures
COMPREHENSIVE_SIGNATURES = {
    "0x01e1d114": {"name": "totalAssets", "inputs": []},
    "0x06fdde03": {"name": "name", "inputs": []},
    "0x07a2d13a": {"name": "convertToAssets", "inputs": [{"name": "shares", "type": "uint256"}]},
    "0x095ea7b3": {"name": "approve", "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}]},
    "0x0a28a477": {"name": "previewWithdraw", "inputs": [{"name": "assets", "type": "uint256"}]},
    "0x0b6e46fe": {"name": "enableController", "inputs": [{"name": "controller", "type": "address"}]},
    "0x11be0de5": {"name": "enableCollateral", "inputs": [{"name": "collateral", "type": "address"}]},
    "0x18160ddd": {"name": "totalSupply", "inputs": []},
    "0x18503a1e": {"name": "getCurrentOnBehalfOfAccount", "inputs": [{"name": "account", "type": "address"}]},
    "0x1f8b5215": {"name": "call", "inputs": [{"name": "targetContract", "type": "address"}, {"name": "onBehalfOfAccount", "type": "address"}, {"name": "value", "type": "uint256"}, {"name": "data", "type": "bytes"}]},
    "0x212bf316": {"name": "setCaps", "inputs": [{"name": "supplyCap", "type": "uint256"}, {"name": "borrowCap", "type": "uint256"}]},
    "0x23b872dd": {"name": "transferFrom", "inputs": [{"name": "from", "type": "address"}, {"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}]},
    "0x313ce567": {"name": "decimals", "inputs": []},
    "0x38d52e0f": {"name": "asset", "inputs": []},
    "0x3c0b5bcb": {"name": "govSetFallbackOracle", "inputs": [{"name": "asset", "type": "address"}, {"name": "oracle", "type": "address"}]},
    "0x402d267d": {"name": "maxDeposit", "inputs": [{"name": "receiver", "type": "address"}]},
    "0x442b172c": {"name": "getAccountOwner", "inputs": [{"name": "account", "type": "address"}]},
    "0x47cfdac4": {"name": "isControllerEnabled", "inputs": [{"name": "account", "type": "address"}, {"name": "controller", "type": "address"}]},
    "0x4bca3d5b": {"name": "setLTV", "inputs": [{"name": "collateral", "type": "address"}, {"name": "borrowLTV", "type": "uint16"}, {"name": "liquidationLTV", "type": "uint16"}, {"name": "rampDuration", "type": "uint32"}]},
    "0x4cdad506": {"name": "previewRedeem", "inputs": [{"name": "shares", "type": "uint256"}]},
    "0x4d69ee0e": {"name": "setOracleRouter", "inputs": [{"name": "newOracleRouter", "type": "address"}]},
    "0x530e784f": {"name": "setPriceOracle", "inputs": [{"name": "newPriceOracle", "type": "address"}]},
    "0x5d21b300": {"name": "setHookTarget", "inputs": [{"name": "newHookTarget", "type": "address"}]},
    "0x60cb90ef": {"name": "setInterestFee", "inputs": [{"name": "newInterestFee", "type": "uint16"}]},
    "0x6e553f65": {"name": "deposit", "inputs": [{"name": "assets", "type": "uint256"}, {"name": "receiver", "type": "address"}]},
    "0x70a08231": {"name": "balanceOf", "inputs": [{"name": "account", "type": "address"}]},
    "0x75c038b7": {"name": "disableCollateral", "inputs": [{"name": "collateral", "type": "address"}]},
    "0x77e33316": {"name": "getQuotes", "inputs": [{"name": "inAmount", "type": "uint256"}, {"name": "base", "type": "address"}, {"name": "quotes", "type": "address[]"}]},
    "0x7adbf973": {"name": "setOracle", "inputs": [{"name": "newOracle", "type": "address"}]},
    "0x82ebd674": {"name": "setGovernorAdmin", "inputs": [{"name": "newGovernorAdmin", "type": "address"}]},
    "0x85c92cbe": {"name": "clearBalanceForwarder", "inputs": [{"name": "account", "type": "address"}]},
    "0x8bcd4016": {"name": "setInterestRateModel", "inputs": [{"name": "newInterestRateModel", "type": "address"}]},
    "0x94bf804d": {"name": "mint", "inputs": [{"name": "shares", "type": "uint256"}, {"name": "receiver", "type": "address"}]},
    "0x95d89b41": {"name": "symbol", "inputs": []},
    "0x9ca1ff80": {"name": "govSetConfig", "inputs": [{"name": "configAddress", "type": "address"}, {"name": "config", "type": "uint32"}]},
    "0x9e716d58": {"name": "isCollateralEnabled", "inputs": [{"name": "account", "type": "address"}, {"name": "collateral", "type": "address"}]},
    "0xa4d25d1e": {"name": "getCollaterals", "inputs": [{"name": "account", "type": "address"}]},
    "0xa9059cbb": {"name": "transfer", "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}]},
    "0xac41865a": {"name": "getPrice", "inputs": [{"name": "base", "type": "address"}, {"name": "quote", "type": "address"}]},
    "0xae68676c": {"name": "getQuote", "inputs": [{"name": "inAmount", "type": "uint256"}, {"name": "base", "type": "address"}, {"name": "quote", "type": "address"}]},
    "0xaf06d3cf": {"name": "setLiquidationCoolOffTime", "inputs": [{"name": "newLiquidationCoolOffTime", "type": "uint16"}]},
    "0xb3d7f6b9": {"name": "previewMint", "inputs": [{"name": "shares", "type": "uint256"}]},
    "0xb4113ba7": {"name": "setMaxLiquidationDiscount", "inputs": [{"name": "newMaxLiquidationDiscount", "type": "uint16"}]},
    "0xb460af94": {"name": "withdraw", "inputs": [{"name": "assets", "type": "uint256"}, {"name": "receiver", "type": "address"}, {"name": "owner", "type": "address"}]},
    "0xba087652": {"name": "redeem", "inputs": [{"name": "shares", "type": "uint256"}, {"name": "receiver", "type": "address"}, {"name": "owner", "type": "address"}]},
    "0xc16ae7a4": {"name": "batch", "inputs": [{"name": "items", "type": "(address,address,uint256,bytes)[]"}]},
    "0xc63d75b6": {"name": "maxMint", "inputs": [{"name": "receiver", "type": "address"}]},
    "0xc6e6f592": {"name": "convertToShares", "inputs": [{"name": "assets", "type": "uint256"}]},
    "0xce96cb77": {"name": "maxWithdraw", "inputs": [{"name": "owner", "type": "address"}]},
    "0xd1a3a308": {"name": "setHookConfig", "inputs": [{"name": "hookTarget", "type": "address"}, {"name": "hookedOps", "type": "uint32"}]},
    "0xd38bfff4": {"name": "transferGovernance", "inputs": [{"name": "newGovernance", "type": "address"}]},
    "0xd6c02926": {"name": "govSetResolvedVault", "inputs": [{"name": "vault", "type": "address"}, {"name": "set", "type": "bool"}]},
    "0xd87f780f": {"name": "setCaps", "inputs": [{"name": "supplyCap", "type": "uint16"}, {"name": "borrowCap", "type": "uint16"}]},
    "0xd905777e": {"name": "maxRedeem", "inputs": [{"name": "owner", "type": "address"}]},
    "0xdd62ed3e": {"name": "allowance", "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}]},
    "0xe72146de": {"name": "setBalanceForwarder", "inputs": [{"name": "newBalanceForwarder", "type": "address"}]},
    "0xef2355e5": {"name": "reorderCollaterals", "inputs": [{"name": "index1", "type": "uint8"}, {"name": "index2", "type": "uint8"}]},
    "0xef8b30f7": {"name": "previewDeposit", "inputs": [{"name": "assets", "type": "uint256"}]},
    "0xefdcd974": {"name": "setFeeReceiver", "inputs": [{"name": "newFeeReceiver", "type": "address"}]},
    "0xf4fc3570": {"name": "disableController", "inputs": [{"name": "controller", "type": "address"}]},
    "0xfd6046d7": {"name": "getControllers", "inputs": [{"name": "account", "type": "address"}]},
    # Add the old selectors we've seen
    "0x0ac3e318": {"name": "setCaps", "inputs": [{"name": "supplyCap", "type": "uint256"}, {"name": "borrowCap", "type": "uint256"}]},
    "0x72e94bf6": {"name": "batch", "inputs": [{"name": "items", "type": "(address,address,uint256,bytes)[]"}]},
    "0x8d8fe2c3": {"name": "setGovernorAdmin", "inputs": [{"name": "newGovernorAdmin", "type": "address"}]},
}

GOVERNANCE_FUNCTIONS = {
    'setCaps', 'setGovernorAdmin', 'setFeeReceiver', 'setInterestRateModel',
    'setMaxLiquidationDiscount', 'setHookConfig', 'setInterestFee',
    'setLiquidationCoolOffTime', 'setLTV', 'govSetConfig', 'transferGovernance',
    'govSetResolvedVault', 'govSetFallbackOracle', 'setHookTarget', 'setOracle',
    'setPriceOracle', 'setOracleRouter'
}

# Generate the Python code for the updated _load_function_signatures method
def generate_updated_method():
    print('    def _load_function_signatures(self) -> Dict[str, Dict[str, Any]]:')
    print('        """Load comprehensive function signatures for EVC and vault operations."""')
    print('        return {')
    
    for selector, info in sorted(COMPREHENSIVE_SIGNATURES.items()):
        print(f'            "{selector}": {{')
        print(f'                "name": "{info["name"]}",')
        print(f'                "inputs": {json.dumps(info["inputs"])}')
        print('            },')
    
    print('        }')
    print()

if __name__ == "__main__":
    generate_updated_method()
    print(f"Total function signatures: {len(COMPREHENSIVE_SIGNATURES)}")
    print(f"Governance functions: {len(GOVERNANCE_FUNCTIONS)}")


