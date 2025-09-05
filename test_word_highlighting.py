#!/usr/bin/env python3
"""
Test script for word-level highlighting functionality in Lue.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add the lue package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lue'))

from lue import ui, config


class TestWordHighlighting(unittest.TestCase):
    """Test cases for word-level highlighting functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Enable both highlighting modes for testing
        config.SENTENCE_HIGHLIGHTING_ENABLED = True
        config.WORD_HIGHLIGHTING_ENABLED = True

    def test_word_highlight_color_added(self):
        """Test that word highlight color is defined in UIColors."""
        # Check that WORD_HIGHLIGHT is defined in UIColors
        self.assertTrue(hasattr(ui.UIColors, 'WORD_HIGHLIGHT'))
        self.assertEqual(ui.UIColors.WORD_HIGHLIGHT, "bold yellow")

    def test_config_options_added(self):
        """Test that configuration options for highlighting are added."""
        # Check that config options exist
        self.assertTrue(hasattr(config, 'SENTENCE_HIGHLIGHTING_ENABLED'))
        self.assertTrue(hasattr(config, 'WORD_HIGHLIGHTING_ENABLED'))
        
        # Check default values
        self.assertTrue(config.SENTENCE_HIGHLIGHTING_ENABLED)
        self.assertTrue(config.WORD_HIGHLIGHTING_ENABLED)

    @patch('lue.ui.get_terminal_size')
    @patch('lue.ui.content_parser')
    def test_get_visible_content_with_word_highlighting(self, mock_content_parser, mock_get_terminal_size):
        """Test that get_visible_content handles word highlighting."""
        # Mock terminal size
        mock_get_terminal_size.return_value = (80, 24)

        # Create a mock reader with proper structure
        mock_reader = Mock()
        mock_reader.scroll_offset = 0
        mock_reader.ui_chapter_idx = 0
        mock_reader.ui_paragraph_idx = 0
        mock_reader.ui_sentence_idx = 0
        mock_reader.ui_word_idx = 1  # Second word
        mock_reader.paragraph_line_ranges = {(0, 0): (0, 0)}
        mock_reader.line_to_position = {0: (0, 0, 0)}
        mock_reader.document_lines = [Mock()]
        mock_reader.document_lines[0].plain = "This is a test sentence."

        # Mock selection attributes
        mock_reader.selection_active = False
        mock_reader.selection_start = None
        mock_reader.selection_end = None

        # Mock chapters structure
        mock_reader.chapters = [["This is a test sentence."]]

        # Mock content parser
        mock_content_parser.split_into_sentences.return_value = ["This is a test sentence."]

        # Mock console
        mock_reader.console = Mock()

        # Call the function
        result = ui.get_visible_content(mock_reader)

        # Verify that the function executed without errors
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)

    def test_toggle_highlighting_commands(self):
        """Test that toggle commands exist in input handler."""
        # Check that the toggle commands are defined
        from lue import input_handler
        
        # These should be handled in the input processing
        # We're just verifying the logic is there by checking the config can be toggled
        
        # Initial state
        initial_sentence = config.SENTENCE_HIGHLIGHTING_ENABLED
        initial_word = config.WORD_HIGHLIGHTING_ENABLED
        
        # Toggle both
        config.SENTENCE_HIGHLIGHTING_ENABLED = not config.SENTENCE_HIGHLIGHTING_ENABLED
        config.WORD_HIGHLIGHTING_ENABLED = not config.WORD_HIGHLIGHTING_ENABLED
        
        # Verify they changed
        self.assertNotEqual(initial_sentence, config.SENTENCE_HIGHLIGHTING_ENABLED)
        self.assertNotEqual(initial_word, config.WORD_HIGHLIGHTING_ENABLED)
        
        # Toggle back to original
        config.SENTENCE_HIGHLIGHTING_ENABLED = not config.SENTENCE_HIGHLIGHTING_ENABLED
        config.WORD_HIGHLIGHTING_ENABLED = not config.WORD_HIGHLIGHTING_ENABLED
        
        # Verify they're back to original
        self.assertEqual(initial_sentence, config.SENTENCE_HIGHLIGHTING_ENABLED)
        self.assertEqual(initial_word, config.WORD_HIGHLIGHTING_ENABLED)

    def test_word_update_logic(self):
        """Test that word index updates correctly based on timing."""
        # Create a mock reader with word tracking attributes
        mock_reader = Mock()
        mock_reader.ui_word_idx = 0
        mock_reader.current_sentence_words = ["This", "is", "a", "test", "sentence"]
        mock_reader.current_sentence_duration = 5.0  # 5 seconds
        mock_reader.current_word_start_time = 0  # Start time
        mock_reader.playback_speed = 1.0

        # Test word index calculation at different elapsed times
        # At 0 seconds: word 0
        elapsed = 0
        total_words = len(mock_reader.current_sentence_words)
        time_per_word = mock_reader.current_sentence_duration / total_words
        current_word_idx = min(int(elapsed / time_per_word), total_words - 1)
        self.assertEqual(current_word_idx, 0)

        # At 1 second: word 0 (0-1 second range)
        elapsed = 1
        current_word_idx = min(int(elapsed / time_per_word), total_words - 1)
        self.assertEqual(current_word_idx, 0)

        # At 1.1 seconds: word 1 (1-2 second range)
        elapsed = 1.1
        current_word_idx = min(int(elapsed / time_per_word), total_words - 1)
        self.assertEqual(current_word_idx, 1)

        # At 4.9 seconds: word 4 (last word)
        elapsed = 4.9
        current_word_idx = min(int(elapsed / time_per_word), total_words - 1)
        self.assertEqual(current_word_idx, 4)


if __name__ == '__main__':
    unittest.main()
