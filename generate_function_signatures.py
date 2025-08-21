#!/usr/bin/env python3
"""Generate comprehensive function signature mappings for EVC and vault operations."""

from web3 import Web3

def generate_function_signatures():
    """Generate function signatures for common EVC and vault functions."""
    
    # ERC4626 Standard Functions
    erc4626_functions = [
        "asset()",
        "totalAssets()",
        "convertToShares(uint256)",
        "convertToAssets(uint256)",
        "maxDeposit(address)",
        "maxMint(address)",
        "maxWithdraw(address)",
        "maxRedeem(address)",
        "previewDeposit(uint256)",
        "previewMint(uint256)",
        "previewWithdraw(uint256)",
        "previewRedeem(uint256)",
        "deposit(uint256,address)",
        "mint(uint256,address)",
        "withdraw(uint256,address,address)",
        "redeem(uint256,address,address)",
    ]
    
    # EVC Specific Functions
    evc_functions = [
        "batch((address,address,uint256,bytes)[])",
        "call(address,address,uint256,bytes)",
        "enableController(address)",
        "disableController(address)",
        "enableCollateral(address)",
        "disableCollateral(address)",
        "reorderCollaterals(uint8,uint8)",
        "getAccountOwner(address)",
        "getCurrentOnBehalfOfAccount(address)",
        "getCollaterals(address)",
        "getControllers(address)",
        "isControllerEnabled(address,address)",
        "isCollateralEnabled(address,address)",
    ]
    
    # Vault Governance Functions
    vault_governance_functions = [
        "setCaps(uint256,uint256)",
        "setCaps(uint16,uint16)",  # Alternative signature found in data
        "setInterestRateModel(address)",
        "setGovernorAdmin(address)",
        "setFeeReceiver(address)",
        "setHookConfig(address,uint32)",
        "setInterestFee(uint16)",
        "setMaxLiquidationDiscount(uint16)",
        "setLiquidationCoolOffTime(uint16)",
        "setLTV(address,uint16,uint16,uint32)",
        "transferGovernance(address)",
        "setHookTarget(address)",
        "setOracle(address)",
        "setPriceOracle(address)",
        "setOracleRouter(address)",
        "clearBalanceForwarder(address)",
        "setBalanceForwarder(address)",
    ]
    
    # Oracle Functions
    oracle_functions = [
        "getPrice(address,address)",
        "getQuote(uint256,address,address)",
        "getQuotes(uint256,address,address[])",
        "govSetConfig(address,uint32)",
        "govSetResolvedVault(address,bool)",
        "govSetFallbackOracle(address,address)",
    ]
    
    # ERC20 Standard Functions
    erc20_functions = [
        "name()",
        "symbol()",
        "decimals()",
        "totalSupply()",
        "balanceOf(address)",
        "transfer(address,uint256)",
        "transferFrom(address,address,uint256)",
        "approve(address,uint256)",
        "allowance(address,address)",
    ]
    
    # Combine all functions
    all_functions = (
        erc4626_functions + 
        evc_functions + 
        vault_governance_functions + 
        oracle_functions + 
        erc20_functions
    )
    
    # Generate signatures
    signatures = {}
    governance_functions = set()
    
    for func_sig in all_functions:
        try:
            selector = Web3.keccak(text=func_sig)[:4].hex()
            
            # Parse function name and inputs
            func_name = func_sig.split('(')[0]
            inputs_str = func_sig[func_sig.find('(')+1:func_sig.rfind(')')]
            
            # Parse inputs
            inputs = []
            if inputs_str.strip():
                for i, input_type in enumerate(inputs_str.split(',')):
                    input_type = input_type.strip()
                    inputs.append({
                        "name": f"arg{i}",
                        "type": input_type
                    })
            
            # Special handling for known function names
            if func_name == "setCaps" and len(inputs) == 2:
                inputs[0]["name"] = "supplyCap"
                inputs[1]["name"] = "borrowCap"
            elif func_name == "setInterestRateModel" and len(inputs) == 1:
                inputs[0]["name"] = "newInterestRateModel"
            elif func_name == "setGovernorAdmin" and len(inputs) == 1:
                inputs[0]["name"] = "newGovernorAdmin"
            elif func_name == "setFeeReceiver" and len(inputs) == 1:
                inputs[0]["name"] = "newFeeReceiver"
            elif func_name == "setLTV" and len(inputs) == 4:
                inputs[0]["name"] = "collateral"
                inputs[1]["name"] = "borrowLTV"
                inputs[2]["name"] = "liquidationLTV"
                inputs[3]["name"] = "rampDuration"
            elif func_name == "setHookConfig" and len(inputs) == 2:
                inputs[0]["name"] = "hookTarget"
                inputs[1]["name"] = "hookedOps"
            elif func_name == "batch" and len(inputs) == 1:
                inputs[0]["name"] = "items"
            elif func_name == "call" and len(inputs) == 4:
                inputs[0]["name"] = "targetContract"
                inputs[1]["name"] = "onBehalfOfAccount"
                inputs[2]["name"] = "value"
                inputs[3]["name"] = "data"
            
            signatures[selector] = {
                "name": func_name,
                "inputs": inputs,
                "signature": func_sig
            }
            
            # Mark governance functions
            if func_name in [
                'setCaps', 'setGovernorAdmin', 'setFeeReceiver', 'setInterestRateModel',
                'setMaxLiquidationDiscount', 'setHookConfig', 'setInterestFee',
                'setLiquidationCoolOffTime', 'setLTV', 'govSetConfig', 'transferGovernance',
                'govSetResolvedVault', 'govSetFallbackOracle', 'setHookTarget', 'setOracle',
                'setPriceOracle', 'setOracleRouter'
            ]:
                governance_functions.add(func_name)
                
        except Exception as e:
            print(f"Error processing {func_sig}: {e}")
    
    return signatures, governance_functions

if __name__ == "__main__":
    signatures, governance_funcs = generate_function_signatures()
    
    print("Generated function signatures:")
    print("="*50)
    
    for selector, info in sorted(signatures.items()):
        gov_marker = " (GOVERNANCE)" if info["name"] in governance_funcs else ""
        print(f'{selector}: {info["name"]}{gov_marker}')
        print(f'  Signature: {info["signature"]}')
        if info["inputs"]:
            print(f'  Inputs: {[inp["name"] + ":" + inp["type"] for inp in info["inputs"]]}')
        print()
    
    print(f"\nTotal signatures: {len(signatures)}")
    print(f"Governance functions: {len(governance_funcs)}")


