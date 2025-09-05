#!/usr/bin/env python3
"""
Demo script showing how the improved Kokoro TTS word-level timing enhances word highlighting.
"""

import asyncio
import os
import sys
import tempfile
from rich.console import Console

# Add the project root to the path so we can import lue modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lue.tts.kokoro_tts import KokoroTTS

async def demo_word_highlighting():
    """Demo showing improved word highlighting with Kokoro TTS."""
    console = Console()
    tts = KokoroTTS(console, voice="af_heart", lang="a")
    
    # Initialize the TTS model
    print("Initializing Kokoro TTS model...")
    initialized = await tts.initialize()
    if not initialized:
        print("Failed to initialize Kokoro TTS model")
        return False
    
    # Test text with various punctuation and formatting
    test_text = "Hello, world! This is a test... with punctuation; and: colons. How does it work?"
    
    # Create a temporary file for output
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        output_path = tmp_file.name
    
    try:
        print(f"Testing with text: '{test_text}'")
        
        # Generate audio with timing
        duration, word_timings = await tts.generate_audio_with_timing(test_text, output_path)
        
        print(f"\nTotal audio duration: {duration:.3f} seconds")
        print(f"Number of words timed: {len(word_timings)}")
        
        print("\n=== Word Timing Results ===")
        for i, (word, start_time, end_time) in enumerate(word_timings):
            print(f"  {i+1:2d}. '{word}' - {start_time:.3f}s to {end_time:.3f}s")
        
        # Simulate word highlighting over time
        print("\n=== Simulated Word Highlighting ===")
        current_time = 0.0
        time_step = 0.2  # Update every 0.2 seconds
        
        while current_time <= duration:
            # Find the word that should be highlighted at this time
            highlighted_word = None
            for word, start_time, end_time in word_timings:
                if start_time <= current_time < end_time:
                    highlighted_word = word
                    break
            
            if highlighted_word:
                print(f"  {current_time:4.1f}s: Highlighting '{highlighted_word}'")
            else:
                print(f"  {current_time:4.1f}s: (no word)")
            
            current_time += time_step
        
        print("\n=== Benefits of Improved Timing ===")
        print("1. More accurate word boundaries from Kokoro's segmentation")
        print("2. Better synchronization between audio and visual highlighting")
        print("3. Proper handling of punctuation and special characters")
        print("4. Smoother user experience during TTS playback")
        
        print("\nDemo completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up the temporary file
        if os.path.exists(output_path):
            os.unlink(output_path)

if __name__ == "__main__":
    result = asyncio.run(demo_word_highlighting())
    sys.exit(0 if result else 1)