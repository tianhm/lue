#!/usr/bin/env python3
"""
Test script to show how Kokoro TTS segments text and how our implementation handles them.
"""

import asyncio
import os
import sys
import tempfile
from rich.console import Console

# Add the project root to the path so we can import lue modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lue.tts.kokoro_tts import KokoroTTS

async def test_kokoro_segments():
    """Test how Kokoro TTS segments text and our timing implementation."""
    console = Console()
    tts = KokoroTTS(console, voice="af_heart", lang="a")
    
    # Initialize the TTS model
    print("Initializing Kokoro TTS model...")
    initialized = await tts.initialize()
    if not initialized:
        print("Failed to initialize Kokoro TTS model")
        return False
    
    # Test text that should be segmented
    test_text = "First sentence. Second sentence with more words. Third."
    
    try:
        print(f"Testing with text: '{test_text}'")
        
        # Manually call the pipeline to see how it segments the text
        print("\n=== Kokoro Pipeline Segmentation ===")
        results = list(tts.pipeline(test_text, voice=tts.voice, split_pattern=None))
        
        print(f"Number of segments: {len(results)}")
        for i, (gs, ps, audio) in enumerate(results):
            segment_duration = len(audio) / 24000.0
            words = gs.split() if gs else []
            print(f"  Segment {i+1}: '{gs}' ({len(words)} words, {segment_duration:.3f}s)")
        
        # Show how our new implementation processes these segments
        print("\n=== Our New Implementation Processing ===")
        word_timings = []
        current_time = 0.0
        
        for i, (gs, ps, audio) in enumerate(results):
            segment_duration = len(audio) / 24000.0
            segment_words = gs.split() if gs else []
            
            print(f"  Processing segment {i+1}: '{gs}' ({segment_duration:.3f}s)")
            
            if segment_words:
                time_per_word = segment_duration / len(segment_words)
                print(f"    {len(segment_words)} words, {time_per_word:.3f}s per word")
                
                for j, word in enumerate(segment_words):
                    start_time = current_time + j * time_per_word
                    end_time = current_time + (j + 1) * time_per_word
                    word_timings.append((word, start_time, end_time))
                    print(f"      '{word}' at {start_time:.3f}s - {end_time:.3f}s")
            
            current_time += segment_duration
            print(f"    Segment ends at {current_time:.3f}s")
        
        print(f"\nTotal duration: {current_time:.3f}s")
        print(f"Total word timings: {len(word_timings)}")
        
        print("\n=== Final Word Timings ===")
        for i, (word, start_time, end_time) in enumerate(word_timings):
            print(f"  {i+1:2d}. '{word}' - {start_time:.3f}s to {end_time:.3f}s")
        
        print("\nTest completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_kokoro_segments())
    sys.exit(0 if result else 1)