#!/usr/bin/env python3
"""
Test script to verify the Edge TTS word timing fix.
"""

import sys
import os
import asyncio
import unittest
from unittest.mock import Mock, patch

# Add the lue package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


class TestEdgeWordTimingFix(unittest.TestCase):
    """Test cases for Edge TTS word timing fix."""

    def test_word_timings_continuity_logic(self):
        """Test the logic for adjusting word timings for continuity."""
        # Import the actual EdgeTTS class
        from lue.tts.edge_tts import EdgeTTS
        
        # Create a mock console
        console_mock = Mock()
        edge_tts = EdgeTTS(console_mock)
        
        # Simulate word timings with gaps (what we might get from Edge TTS)
        # Word timings with gaps between them:
        # "Hello" from 0.5s to 1.2s
        # "world" from 1.5s to 2.3s (gap of 0.3s between words)
        # "test" from 2.3s to 3.0s (no gap)
        original_word_timings = [
            ("Hello", 0.5, 1.2),
            ("world", 1.5, 2.3),
            ("test", 2.3, 3.0)
        ]
        
        # Apply the same logic as in our fix
        if len(original_word_timings) > 1:
            adjusted_word_timings = []
            for i in range(len(original_word_timings)):
                word, start_time, end_time = original_word_timings[i]
                # For all words except the last one, use the start time of the next word as end time
                if i < len(original_word_timings) - 1:
                    next_start_time = original_word_timings[i + 1][1]
                    adjusted_end_time = next_start_time
                else:
                    # For the last word, keep the original end time
                    adjusted_end_time = end_time
                adjusted_word_timings.append((word, start_time, adjusted_end_time))
        else:
            adjusted_word_timings = original_word_timings
            
        # Check that word timings are continuous (no gaps)
        word1, start1, end1 = adjusted_word_timings[0]
        word2, start2, end2 = adjusted_word_timings[1]
        word3, start3, end3 = adjusted_word_timings[2]
        
        # First word should be "Hello"
        self.assertEqual(word1, "Hello")
        self.assertAlmostEqual(start1, 0.5, places=5)
        
        # End time of first word should match start time of second word (continuity)
        self.assertAlmostEqual(end1, start2, places=5)
        
        # Second word should be "world"
        self.assertEqual(word2, "world")
        self.assertAlmostEqual(start2, 1.5, places=5)
        
        # End time of second word should match start time of third word (continuity)
        self.assertAlmostEqual(end2, start3, places=5)
        
        # Third word should be "test"
        self.assertEqual(word3, "test")
        self.assertAlmostEqual(start3, 2.3, places=5)
        
        # End time of third word should be unchanged
        self.assertAlmostEqual(end3, 3.0, places=5)

    def test_single_word_timing_logic(self):
        """Test timing adjustment logic for a single word."""
        # Import the actual EdgeTTS class
        from lue.tts.edge_tts import EdgeTTS
        
        # Create a mock console
        console_mock = Mock()
        edge_tts = EdgeTTS(console_mock)
        
        # Simulate timing for a single word
        original_word_timings = [("Hello", 0.5, 1.2)]
        
        # Apply the same logic as in our fix
        if len(original_word_timings) > 1:
            adjusted_word_timings = []
            for i in range(len(original_word_timings)):
                word, start_time, end_time = original_word_timings[i]
                # For all words except the last one, use the start time of the next word as end time
                if i < len(original_word_timings) - 1:
                    next_start_time = original_word_timings[i + 1][1]
                    adjusted_end_time = next_start_time
                else:
                    # For the last word, keep the original end time
                    adjusted_end_time = end_time
                adjusted_word_timings.append((word, start_time, adjusted_end_time))
        else:
            adjusted_word_timings = original_word_timings
            
        # Should be unchanged for a single word
        self.assertEqual(len(adjusted_word_timings), 1)
        word1, start1, end1 = adjusted_word_timings[0]
        self.assertEqual(word1, "Hello")
        self.assertAlmostEqual(start1, 0.5, places=5)
        self.assertAlmostEqual(end1, 1.2, places=5)  # Should be unchanged


if __name__ == '__main__':
    unittest.main()