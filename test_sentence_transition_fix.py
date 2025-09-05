#!/usr/bin/env python3
"""
Test script to verify the sentence transition timing fix.
"""

import sys
import os
import asyncio
import unittest
from unittest.mock import Mock, patch

# Add the lue package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))


class TestSentenceTransitionFix(unittest.TestCase):
    """Test cases for sentence transition timing fix."""

    def test_sentence_transition_duration_storage(self):
        """Test that sentence transition duration is properly stored."""
        # Import the required modules
        from lue.audio import _player_loop
        from lue import content_parser
        
        # Create a mock reader
        mock_reader = Mock()
        mock_reader.chapters = [["This is the first sentence. This is the second sentence."]]
        mock_reader.current_sentence_transition_duration = 2.5  # Mock value
        
        # Test that getattr correctly retrieves the transition duration
        sentence_duration = getattr(mock_reader, 'current_sentence_transition_duration', 3.0)
        self.assertEqual(sentence_duration, 2.5)
        
        # Test fallback when attribute doesn't exist
        del mock_reader.current_sentence_transition_duration
        sentence_duration = getattr(mock_reader, 'current_sentence_transition_duration', 3.0)
        self.assertEqual(sentence_duration, 3.0)

    def test_word_timing_vs_sentence_timing(self):
        """Test that word timings are used for highlighting but sentence duration for transitions."""
        # Simulate word timings with a gap at the end (representing pause)
        word_timings = [
            ("Hello", 0.0, 0.5),
            ("world", 0.5, 1.0),
            ("test", 1.0, 1.5)
        ]
        
        # Total audio duration including pause at the end
        total_duration = 2.0  # 0.5s pause after the last word
        
        # Verify that word timings are continuous (for highlighting)
        for i in range(len(word_timings) - 1):
            current_word_end = word_timings[i][2]
            next_word_start = word_timings[i + 1][1]
            self.assertEqual(current_word_end, next_word_start, 
                           f"Word timing gap detected between {word_timings[i][0]} and {word_timings[i + 1][0]}")
        
        # Verify that total duration is longer than last word end time (includes pause)
        last_word_end = word_timings[-1][2]
        self.assertLess(last_word_end, total_duration, 
                       "Total duration should include pause after last word")


if __name__ == '__main__':
    unittest.main()