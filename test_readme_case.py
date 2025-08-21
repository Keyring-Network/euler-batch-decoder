"""Test the specific case from the README."""

from evc_batch_decoder.decoder import EVCBatchDecoder

def test_readme_case():
    """Test the specific batch data from the README."""
    decoder = EVCBatchDecoder(chain_id=43114)  # Avalanche for test case
    
    # Mock the test case metadata directly in the decoder for testing
    test_metadata = {
        "0x8f23da78e3f31ab5deb75dc3282198bed630ffde": {
            "name": "EVK Vault eUSDC-15",
            "type": "vault",
            "symbol": "eUSDC-15"
        },
        "0xea534105c2ccc0582d82b285aa47a6b446383d44": {
            "name": "EVK Vault exUSDC-7", 
            "type": "vault",
            "symbol": "exUSDC-7"
        }
    }
    
    # Test metadata will be added after analysis to simulate real behavior
    
    # Test data from README
    test_data = "0xc16ae7a400000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000000000000000004000000000000000000000000000000000000000000000000000000000000001400000000000000000000000008f23da78e3f31ab5deb75dc3282198bed630ffde00000000000000000000000069cc425b1e5f302e7db4e5d125ab984ec5186364000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000044d87f780f000000000000000000000000000000000000000000000000000000000000320d000000000000000000000000000000000000000000000000000000000000320d00000000000000000000000000000000000000000000000000000000000000000000000000000000ea534105c2ccc0582d82b285aa47a6b446383d4400000000000000000000000069cc425b1e5f302e7db4e5d125ab984ec5186364000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000044d87f780f000000000000000000000000000000000000000000000000000000000000320d000000000000000000000000000000000000000000000000000000000000000600000000000000000000000000000000000000000000000000000000"
    
    try:
        print("🧙‍♂️ Testing README batch data...")
        result = decoder.decode_batch_data(test_data)
        
        print(f"✅ Successfully decoded {len(result.items)} items")
        
        # Verify the expected results
        assert len(result.items) == 2, f"Expected 2 items, got {len(result.items)}"
        
        # Check first item
        item1 = result.items[0]
        assert item1.target_contract.lower() == "0x8f23da78e3f31ab5deb75dc3282198bed630ffde", f"Wrong target contract: {item1.target_contract}"
        assert item1.decoded is not None, "First item should be decoded"
        assert item1.decoded['functionName'] == 'setCaps', f"Expected setCaps, got {item1.decoded['functionName']}"
        assert item1.decoded['args']['supplyCap'] == 12813, f"Expected supplyCap 12813, got {item1.decoded['args']['supplyCap']}"
        assert item1.decoded['args']['borrowCap'] == 12813, f"Expected borrowCap 12813, got {item1.decoded['args']['borrowCap']}"
        
        # Check second item  
        item2 = result.items[1]
        assert item2.target_contract.lower() == "0xea534105c2ccc0582d82b285aa47a6b446383d44", f"Wrong target contract: {item2.target_contract}"
        assert item2.decoded is not None, "Second item should be decoded"
        assert item2.decoded['functionName'] == 'setCaps', f"Expected setCaps, got {item2.decoded['functionName']}"
        assert item2.decoded['args']['supplyCap'] == 12813, f"Expected supplyCap 12813, got {item2.decoded['args']['supplyCap']}"
        assert item2.decoded['args']['borrowCap'] == 6, f"Expected borrowCap 6, got {item2.decoded['args']['borrowCap']}"
        
        print("✅ All assertions passed!")
        
        # Analyze the batch (this will use generic names since no web3 client)
        analysis = decoder.analyze_batch(result)
        
        # For testing purposes, add the expected metadata after analysis
        # This simulates what would happen with a real web3 client
        for address, metadata in test_metadata.items():
            decoder.add_contract_metadata(address, metadata)
        print(f"Analysis: {len(analysis['governance_operations'])} governance operations")
        print(f"Vault changes: {len(analysis['vault_changes'])} vaults")
        
        # Format output in README style
        print("\n" + "="*50)
        print("README-style output:")
        print("="*50)
        
        readme_output = decoder.format_readme_style(result, analysis)
        print(readme_output)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_readme_case()
