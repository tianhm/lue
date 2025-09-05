#!/usr/bin/env python3
"""
Test script for precise word-level timing functionality in Lue.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add the lue package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from lue.tts.base import TTSBase
from lue.tts.edge_tts import EdgeTTS
from lue.tts.kokoro_tts import KokoroTTS


class TestPreciseWordTiming(unittest.TestCase):
    """Test cases for precise word-level timing functionality."""

    def test_base_tts_generate_audio_with_timing_default(self):
        """Test that base TTS class provides default implementation for generate_audio_with_timing."""
        # Create a mock TTS implementation
        class MockTTS(TTSBase):
            def __init__(self):
                super().__init__(Mock())
                self.initialized = True
            
            @property
            def name(self):
                return "mock"
            
            @property
            def output_format(self):
                return "mp3"
            
            async def initialize(self):
                return True
            
            async def generate_audio(self, text, output_path):
                # Create a mock audio file
                with open(output_path, 'w') as f:
                    f.write("mock audio data")
                return True
        
        mock_tts = MockTTS()
        
        # Test the default implementation
        import asyncio
        async def test_async():
            duration, word_timings = await mock_tts.generate_audio_with_timing("Hello world test", "/tmp/mock.mp3")
            # Should return some duration and word timings
            self.assertIsInstance(duration, (int, float))
            self.assertIsInstance(word_timings, list)
            
            # Should have timing information for each word
            self.assertEqual(len(word_timings), 3)  # "Hello", "world", "test"
            
            # Each timing should be a tuple of (word, start_time, end_time)
            for timing in word_timings:
                self.assertIsInstance(timing, tuple)
                self.assertEqual(len(timing), 3)
                word, start_time, end_time = timing
                self.assertIsInstance(word, str)
                self.assertIsInstance(start_time, (int, float))
                self.assertIsInstance(end_time, (int, float))
        
        asyncio.run(test_async())

    @patch('lue.tts.edge_tts.edge_tts')
    def test_edge_tts_generate_audio_with_timing(self, mock_edge_tts):
        """Test that Edge TTS provides word timing information."""
        # Mock the edge-tts library
        mock_communicate = Mock()
        mock_edge_tts.Communicate.return_value = mock_communicate
        
        # Mock the stream response with word boundary events
        async def mock_stream():
            yield {'type': 'WordBoundary', 'text': 'Hello', 'offset': 500000, 'duration': 1000000}
            yield {'type': 'WordBoundary', 'text': 'world', 'offset': 2000000, 'duration': 1000000}
            yield {'type': 'audio', 'data': b'mock audio data'}
        
        mock_communicate.stream = mock_stream
        
        # Create Edge TTS instance
        edge_tts = EdgeTTS(Mock())
        edge_tts.edge_tts = mock_edge_tts
        edge_tts.initialized = True
        
        # Test the method
        import asyncio
        async def test_async():
            duration, word_timings = await edge_tts.generate_audio_with_timing("Hello world", "/tmp/edge.mp3")
            
            # Should return duration and word timings
            self.assertGreater(duration, 0)
            self.assertIsInstance(word_timings, list)
            self.assertEqual(len(word_timings), 2)
            
            # Check timing information
            word1, start1, end1 = word_timings[0]
            word2, start2, end2 = word_timings[1]
            
            self.assertEqual(word1, 'Hello')
            self.assertEqual(word2, 'world')
            self.assertAlmostEqual(start1, 0.05)  # 500000 / 10000000
            self.assertAlmostEqual(end1, 0.15)   # (500000 + 1000000) / 10000000
            self.assertAlmostEqual(start2, 0.20) # 2000000 / 10000000
            self.assertAlmostEqual(end2, 0.30)   # (2000000 + 1000000) / 10000000
        
        asyncio.run(test_async())

    def test_kokoro_tts_generate_audio_with_timing(self):
        """Test that Kokoro TTS provides word timing information."""
        # This test would require the actual Kokoro library to be installed
        # We'll just verify the method exists
        kokoro_tts = KokoroTTS(Mock())
        self.assertTrue(hasattr(kokoro_tts, 'generate_audio_with_timing'))


if __name__ == '__main__':
    unittest.main()