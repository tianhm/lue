#!/usr/bin/env python3
"""
Test script to verify timing continuity in Kokoro TTS word-level timing implementation.
"""

import asyncio
import os
import sys
import tempfile
from rich.console import Console

# Add the project root to the path so we can import lue modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lue.tts.kokoro_tts import KokoroTTS

async def test_timing_continuity():
    """Test timing continuity in Kokoro TTS word-level timing implementation."""
    console = Console()
    tts = KokoroTTS(console, voice="af_heart", lang="a")
    
    # Initialize the TTS model
    print("Initializing Kokoro TTS model...")
    initialized = await tts.initialize()
    if not initialized:
        print("Failed to initialize Kokoro TTS model")
        return False
    
    # Test text with multiple sentences
    test_text = "First. Second sentence with more words. Last."
    
    # Create a temporary file for output
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        output_path = tmp_file.name
    
    try:
        print(f"Testing with text: '{test_text}'")
        
        # Generate audio with timing
        duration, word_timings = await tts.generate_audio_with_timing(test_text, output_path)
        
        print(f"Speech duration: {duration:.6f} seconds")
        print(f"Number of word timings: {len(word_timings)}")
        
        print("\n=== Word Timings with Continuity Check ===")
        for i, (word, start_time, end_time) in enumerate(word_timings):
            print(f"  {i+1:2d}. '{word}' - {start_time:.6f}s to {end_time:.6f}s (duration: {end_time-start_time:.6f}s)")
            
            # Check continuity with next word
            if i < len(word_timings) - 1:
                next_word, next_start, next_end = word_timings[i+1]
                if abs(end_time - next_start) > 1e-9:  # Check for continuity
                    print(f"      WARNING: Gap/overlap with next word: {end_time:.6f}s vs {next_start:.6f}s (diff: {abs(end_time - next_start):.9f}s)")
                else:
                    print(f"      ✓ Continuous with next word")
        
        # Verify that the last word's end time equals the speech duration
        if word_timings:
            last_end_time = word_timings[-1][2]
            print(f"\n=== Duration Verification ===")
            print(f"Last word end time: {last_end_time:.6f}s")
            print(f"Speech duration: {duration:.6f}s")
            if abs(last_end_time - duration) < 1e-9:
                print("✓ Speech duration matches last word end time")
            else:
                print(f"✗ MISMATCH: Difference of {abs(last_end_time - duration):.9f}s")
        
        print("\nTest completed successfully!")
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
    result = asyncio.run(test_timing_continuity())
    sys.exit(0 if result else 1)