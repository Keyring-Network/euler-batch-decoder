"""Simple test script for the EVC batch decoder."""

from evc_batch_decoder.decoder import EVCBatchDecoder

def test_simple_batch():
    """Test decoding a simple batch operation."""
    decoder = EVCBatchDecoder()
    
    # Test data: A simple setCaps function call
    # setCaps(supplyCap=1000, borrowCap=800)
    set_caps_data = "0x0ac3e31803e803200"  # setCaps selector + encoded args
    
    try:
        result = decoder.decode_batch_data(set_caps_data)
        print("✅ Successfully decoded batch data")
        print(f"Items: {len(result.items)}")
        
        if result.items and result.items[0].decoded:
            decoded = result.items[0].decoded
            print(f"Function: {decoded.get('functionName')}")
            print(f"Args: {decoded.get('args')}")
        
        # Analyze the batch
        analysis = decoder.analyze_batch(result)
        print(f"Governance operations: {len(analysis['governance_operations'])}")
        
        # Format output
        decoder.format_output(result, analysis)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_json_input():
    """Test JSON input format."""
    decoder = EVCBatchDecoder()
    
    json_data = {
        "data": "0x0ac3e31803e80320"
    }
    
    try:
        result = decoder.decode_batch_data(json_data)
        print("✅ Successfully decoded JSON input")
        return True
    except Exception as e:
        print(f"❌ JSON test error: {e}")
        return False

if __name__ == "__main__":
    print("🧙‍♂️ Testing EVC Batch Decoder")
    print("=" * 40)
    
    print("\n1. Testing simple batch decoding...")
    test_simple_batch()
    
    print("\n2. Testing JSON input...")
    test_json_input()
    
    print("\n✨ Tests completed!")
