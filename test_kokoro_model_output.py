#!/usr/bin/env python3
"""
Test script to examine the actual output from the Kokoro TTS model to see what timing information is available.
"""

import asyncio
import os
import sys
from rich.console import Console

# Add the project root to the path so we can import lue modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lue.tts.kokoro_tts import KokoroTTS

async def examine_kokoro_output():
    """Examine the actual output from the Kokoro TTS model."""
    console = Console()
    tts = KokoroTTS(console, voice="af_heart", lang="a")
    
    # Initialize the TTS model
    print("Initializing Kokoro TTS model...")
    initialized = await tts.initialize()
    if not initialized:
        print("Failed to initialize Kokoro TTS model")
        return False
    
    # Test text
    test_text = "Hello world. This is a test."
    
    try:
        print(f"Testing with text: '{test_text}'")
        
        # Examine what the Kokoro pipeline actually returns
        print("\n=== Kokoro Pipeline Output ===")
        results = list(tts.pipeline(test_text, voice=tts.voice, split_pattern=None))
        
        print(f"Number of results: {len(results)}")
        
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"  Type: {type(result)}")
            print(f"  Length: {len(result) if hasattr(result, '__len__') else 'N/A'}")
            
            if isinstance(result, tuple) and len(result) >= 3:
                gs, ps, audio = result
                print(f"  gs (graphemes/text): {repr(gs)} (type: {type(gs)})")
                print(f"  ps (phonemes): {repr(ps)} (type: {type(ps)})")
                print(f"  audio: {type(audio)} with shape {getattr(audio, 'shape', 'N/A')}")
                
                # Check if there's any timing information in the phonemes or other data
                if hasattr(ps, '__dict__'):
                    print(f"  ps attributes: {list(ps.__dict__.keys())}")
                    for attr_name in ps.__dict__.keys():
                        attr_value = getattr(ps, attr_name)
                        print(f"    {attr_name}: {attr_value} (type: {type(attr_value)})")
                        if hasattr(attr_value, 'shape'):
                            print(f"      shape: {attr_value.shape}")
                
                # Check if there are any other attributes we might have missed
                print(f"  result attributes: {dir(result)}")
                
                # Look for any timing-related attributes
                timing_attrs = [attr for attr in dir(result) if 'time' in attr.lower() or 'dur' in attr.lower()]
                if timing_attrs:
                    print(f"  Timing-related attributes: {timing_attrs}")
                    for attr in timing_attrs:
                        try:
                            value = getattr(result, attr)
                            print(f"    {attr}: {value}")
                        except Exception as e:
                            print(f"    {attr}: Error accessing - {e}")
            else:
                print(f"  Unexpected result format: {result}")
                print(f"  Result attributes: {dir(result)}")
                
                # Look for any timing-related attributes in the result itself
                timing_attrs = [attr for attr in dir(result) if 'time' in attr.lower() or 'dur' in attr.lower()]
                if timing_attrs:
                    print(f"  Timing-related attributes: {timing_attrs}")
                    for attr in timing_attrs:
                        try:
                            value = getattr(result, attr)
                            print(f"    {attr}: {value}")
                        except Exception as e:
                            print(f"    {attr}: Error accessing - {e}")
        
        print("\n=== Detailed Phoneme Analysis ===")
        for i, result in enumerate(results):
            if isinstance(result, tuple) and len(result) >= 2:
                gs, ps = result[0], result[1]
                print(f"\nResult {i+1} phoneme data:")
                print(f"  ps type: {type(ps)}")
                if hasattr(ps, '__dict__'):
                    for key, value in ps.__dict__.items():
                        print(f"    {key}: {value} (type: {type(value)})")
                        if hasattr(value, 'shape'):
                            print(f"      shape: {value.shape}")
                        if hasattr(value, '__len__') and not isinstance(value, str):
                            try:
                                print(f"      length: {len(value)}")
                                if len(value) > 0 and len(value) < 10:
                                    print(f"      values: {list(value)}")
                            except:
                                pass
        
        print("\nTest completed!")
        return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(examine_kokoro_output())
    sys.exit(0 if result else 1)