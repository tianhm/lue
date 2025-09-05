#!/usr/bin/env python3
"""
Simple test script for word-level timing functionality in Lue.
"""

import sys
import os
import asyncio

# Add the lue package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from lue.tts.base import TTSBase


def test_base_tts_default_timing():
    """Test that base TTS class provides default implementation for generate_audio_with_timing."""
    # Create a mock TTS implementation
    class MockTTS(TTSBase):
        def __init__(self):
            super().__init__(None)
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
            # Create a mock audio file with WAV header to simulate a valid audio file
            import struct
            # Create a minimal WAV file header (44 bytes)
            riff = b'RIFF'
            filesize = 44 + 1000  # 44 bytes header + 1000 bytes of "audio" data
            wave = b'WAVE'
            fmt = b'fmt '
            fmt_chunk_size = 16
            audio_format = 1  # PCM
            num_channels = 1
            sample_rate = 22050
            bits_per_sample = 16
            byte_rate = sample_rate * num_channels * bits_per_sample // 8
            block_align = num_channels * bits_per_sample // 8
            data = b'data'
            data_size = 1000
            
            with open(output_path, 'wb') as f:
                f.write(riff)
                f.write(struct.pack('<I', filesize - 8))
                f.write(wave)
                f.write(fmt)
                f.write(struct.pack('<I', fmt_chunk_size))
                f.write(struct.pack('<H', audio_format))
                f.write(struct.pack('<H', num_channels))
                f.write(struct.pack('<I', sample_rate))
                f.write(struct.pack('<I', byte_rate))
                f.write(struct.pack('<H', block_align))
                f.write(struct.pack('<H', bits_per_sample))
                f.write(data)
                f.write(struct.pack('<I', data_size))
                # Write some mock audio data
                f.write(b'\x00' * data_size)
            return True
    
    async def run_test():
        mock_tts = MockTTS()
        duration, word_timings = await mock_tts.generate_audio_with_timing("Hello world test", "/tmp/mock.wav")
        
        # Should return some duration and word timings
        print(f"Duration: {duration}")
        print(f"Word timings: {word_timings}")
        
        # Should have timing information for each word
        assert len(word_timings) == 3, f"Expected 3 word timings, got {len(word_timings)}"
        
        # Each timing should be a tuple of (word, start_time, end_time)
        for timing in word_timings:
            assert isinstance(timing, tuple), f"Expected tuple, got {type(timing)}"
            assert len(timing) == 3, f"Expected tuple of length 3, got {len(timing)}"
            word, start_time, end_time = timing
            assert isinstance(word, str), f"Expected string, got {type(word)}"
            assert isinstance(start_time, (int, float)), f"Expected number, got {type(start_time)}"
            assert isinstance(end_time, (int, float)), f"Expected number, got {type(end_time)}"
        
        print("Base TTS timing test passed!")

    asyncio.run(run_test())


if __name__ == '__main__':
    test_base_tts_default_timing()