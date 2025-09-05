#!/usr/bin/env python3
"""
Test script to verify improved Kokoro TTS precise timing implementation.
"""

import asyncio
import os
import sys
import tempfile
from rich.console import Console

# Add the project root to the path so we can import lue modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lue.tts.kokoro_tts import KokoroTTS

async def test_kokoro_precise_timing():
    """Test Kokoro TTS precise timing implementation."""
    console = Console()
    tts = KokoroTTS(console, voice="af_heart", lang="a")
    
    # Initialize the TTS model
    print("Initializing Kokoro TTS model...")
    initialized = await tts.initialize()
    if not initialized:
        print("Failed to initialize Kokoro TTS model")
        return False
    
    # Test text with multiple sentences and varying lengths
    test_text = "Hello world. This is a test sentence with more words. Another sentence here."
    
    # Create a temporary file for output
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        output_path = tmp_file.name
    
    try:
        print(f"Generating audio with precise timing for: '{test_text}'")
        duration, word_timings = await tts.generate_audio_with_timing(test_text, output_path)
        
        print(f"Total audio duration: {duration:.3f} seconds")
        print(f"Number of word timings: {len(word_timings)}")
        
        print("\nWord timings:")
        for i, (word, start_time, end_time) in enumerate(word_timings):
            word_duration = end_time - start_time
            print(f"  {i+1:2d}. '{word}' - {start_time:.3f}s to {end_time:.3f}s (duration: {word_duration:.3f}s)")
        
        # Verify that timings are sequential and continuous
        if word_timings:
            print("\nTiming validation:")
            
            # Check that start times are sequential
            start_times = [start for word, start, end in word_timings]
            if start_times == sorted(start_times):
                print("✓ Word start times are sequential")
            else:
                print("✗ Word start times are not sequential")
                
            # Check continuity (no gaps or overlaps)
            continuity_issues = 0
            for i in range(len(word_timings) - 1):
                current_end = word_timings[i][2]
                next_start = word_timings[i+1][1]
                if abs(current_end - next_start) > 0.001:  # Allow for small floating point differences
                    continuity_issues += 1
                    print(f"  Warning: Gap/overlap between word {i+1} ('{word_timings[i][0]}') and {i+2} ('{word_timings[i+1][0]}'): {current_end:.3f}s vs {next_start:.3f}s")
            
            if continuity_issues == 0:
                print("✓ Word timings are continuous (no gaps or overlaps)")
            else:
                print(f"✗ Found {continuity_issues} continuity issues")
            
            # Check that the last word's end time is close to the total duration
            last_end_time = word_timings[-1][2]
            if abs(last_end_time - duration) <= 0.1:
                print(f"✓ Last word ends at {last_end_time:.3f}s, close to total duration {duration:.3f}s")
            else:
                print(f"✗ Last word ends at {last_end_time:.3f}s but total duration is {duration:.3f}s")
        
        # Verify that we have timing information for meaningful words
        original_words = [word for word in test_text.replace('.', '').replace(',', '').split() if word]
        timed_words = [word for word, _, _ in word_timings]
        
        print(f"\nOriginal words: {original_words}")
        print(f"Timed words: {timed_words}")
        
        print("\nTest completed!")
        return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up the temporary file
        if os.path.exists(output_path):
            os.unlink(output_path)

if __name__ == "__main__":
    result = asyncio.run(test_kokoro_precise_timing())
    sys.exit(0 if result else 1)