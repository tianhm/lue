#!/usr/bin/env python3
"""
Integration test for Edge TTS word timing functionality.
"""

import sys
import os
import asyncio

# Add the lue package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from lue.tts.edge_tts import EdgeTTS
from rich.console import Console


async def test_edge_tts_timing():
    """Test Edge TTS word timing integration."""
    try:
        # Create Edge TTS instance
        console = Console()
        edge_tts = EdgeTTS(console)
        
        # Initialize the TTS model
        initialized = await edge_tts.initialize()
        if not initialized:
            print("Edge TTS initialization failed")
            return
            
        print("Edge TTS initialized successfully")
        
        # Test generating audio with timing
        text = "Hello world, this is a test of word timing."
        output_file = "/tmp/edge_timing_test.mp3"
        
        duration, word_timings = await edge_tts.generate_audio_with_timing(text, output_file)
        
        print(f"Audio duration: {duration:.3f} seconds")
        print(f"Number of words: {len(word_timings)}")
        print("Word timings:")
        for i, (word, start, end) in enumerate(word_timings):
            print(f"  {i+1:2d}. '{word}' from {start:.3f}s to {end:.3f}s (duration: {end-start:.3f}s)")
        
        # Verify the output file exists
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"Output file created: {output_file} ({file_size} bytes)")
            # Clean up
            os.remove(output_file)
        else:
            print("ERROR: Output file was not created")
            
        print("Edge TTS timing test completed successfully!")
        
    except Exception as e:
        print(f"Error during Edge TTS timing test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(test_edge_tts_timing())