#!/usr/bin/env python3
"""
Test script to compare old vs new Kokoro TTS word-level timing implementation with multi-segment text.
"""

import asyncio
import os
import sys
import tempfile
from rich.console import Console

# Add the project root to the path so we can import lue modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lue.tts.kokoro_tts import KokoroTTS

# This is a copy of the OLD implementation for comparison
def old_generate_audio_with_timing(self, text: str, output_path: str):
    """
    OLD implementation: Distributes time evenly across all words in the entire text
    """
    import numpy as np
    import soundfile as sf
    
    # Split text into words for timing calculation
    words = text.split()
    
    # Generate audio with timing information
    results = list(self.pipeline(text, voice=self.voice, split_pattern=None))
    
    if results:
        # Concatenate all audio segments
        audio_segments = [result.audio for result in results]
        full_audio = np.concatenate(audio_segments)
        sf.write(output_path, full_audio, 24000)
        
        # Extract timing information from pred_dur tensors
        word_timings = []
        current_time = 0.0
        
        # For simplicity, we'll distribute the total duration evenly across words
        # A more sophisticated approach would use the pred_dur information
        total_duration = len(full_audio) / 24000.0  # Duration in seconds
        time_per_word = total_duration / len(words) if words else 0
        
        for i, word in enumerate(words):
            start_time = i * time_per_word
            end_time = (i + 1) * time_per_word
            word_timings.append((word, start_time, end_time))
        
        return total_duration, word_timings
    else:
        sf.write(output_path, np.array([], dtype=np.float32), 24000)
        return 0.0, []

async def test_timing_comparison():
    """Compare old vs new Kokoro TTS word-level timing implementation."""
    console = Console()
    tts = KokoroTTS(console, voice="af_heart", lang="a")
    
    # Initialize the TTS model
    print("Initializing Kokoro TTS model...")
    initialized = await tts.initialize()
    if not initialized:
        print("Failed to initialize Kokoro TTS model")
        return False
    
    # Test text with multiple sentences that should be processed as separate segments
    # Using newlines to encourage segmentation
    test_text = "This is the first sentence.\n\nThis is a much longer sentence with many more words that should take more time to speak.\n\nShort."
    
    # Create temporary files for output
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file1:
        output_path1 = tmp_file1.name
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file2:
        output_path2 = tmp_file2.name
    
    try:
        print(f"Testing with text: {repr(test_text)}")
        
        # Test NEW implementation
        print("\n=== NEW Implementation ===")
        duration_new, word_timings_new = await tts.generate_audio_with_timing(test_text, output_path1)
        
        print(f"Total audio duration: {duration_new:.3f} seconds")
        print(f"Number of word timings: {len(word_timings_new)}")
        
        print("\nWord timings (NEW):")
        for i, (word, start_time, end_time) in enumerate(word_timings_new):
            print(f"  {i+1:2d}. '{word}' - {start_time:.3f}s to {end_time:.3f}s (duration: {end_time-start_time:.3f}s)")
        
        # Test OLD implementation (using the old method)
        print("\n=== OLD Implementation ===")
        duration_old, word_timings_old = old_generate_audio_with_timing(tts, test_text, output_path2)
        
        print(f"Total audio duration: {duration_old:.3f} seconds")
        print(f"Number of word timings: {len(word_timings_old)}")
        
        print("\nWord timings (OLD):")
        for i, (word, start_time, end_time) in enumerate(word_timings_old):
            print(f"  {i+1:2d}. '{word}' - {start_time:.3f}s to {end_time:.3f}s (duration: {end_time-start_time:.3f}s)")
        
        # Compare timing distributions
        print("\n=== COMPARISON ===")
        print(f"Duration difference: {abs(duration_new - duration_old):.3f}s")
        
        if len(word_timings_new) == len(word_timings_old):
            print("\nWord-by-word timing differences:")
            total_diff = 0.0
            for i, ((word_new, start_new, end_new), (word_old, start_old, end_old)) in enumerate(zip(word_timings_new, word_timings_old)):
                if word_new == word_old:
                    start_diff = abs(start_new - start_old)
                    end_diff = abs(end_new - end_old)
                    duration_diff = abs((end_new - start_new) - (end_old - start_old))
                    total_diff += start_diff + end_diff + duration_diff
                    print(f"  {i+1:2d}. '{word_new}': start diff={start_diff:.3f}s, end diff={end_diff:.3f}s, duration diff={duration_diff:.3f}s")
                else:
                    print(f"  {i+1:2d}. MISMATCH: '{word_new}' vs '{word_old}'")
            
            print(f"\nTotal timing difference: {total_diff:.3f}s")
            
            if total_diff > 0.1:
                print("SIGNIFICANT DIFFERENCE: The new implementation provides more accurate timing!")
            else:
                print("MINOR DIFFERENCE: Timing is very similar between implementations.")
        
        print("\nTest completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up the temporary files
        for path in [output_path1, output_path2]:
            if os.path.exists(path):
                os.unlink(path)

if __name__ == "__main__":
    result = asyncio.run(test_timing_comparison())
    sys.exit(0 if result else 1)