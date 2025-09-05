#!/usr/bin/env python3
"""
Test script to verify that both paragraph indentation is preserved AND highlighting works correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.text import Text
from rich.console import Console
from lue import ui, config

def test_highlighting_and_indentation():
    """Test that both indentation and highlighting work correctly."""
    print("Testing highlighting and indentation preservation...")
    
    # Create a mock reader object with the necessary attributes
    class MockReader:
        def __init__(self):
            self.ui_chapter_idx = 0
            self.ui_paragraph_idx = 0
            self.ui_sentence_idx = 0  # First sentence
            self.ui_word_idx = 1  # Second word
            self.chapters = [["    This is the first sentence. This is the second sentence. This is the third sentence."]]
            self.paragraph_line_ranges = {(0, 0): (0, 3)}
            self.document_lines = [
                Text("    This is the first", style="white"),
                Text("sentence. This is the second", style="white"),
                Text("sentence. This is the third", style="white"),
                Text("sentence.", style="white")
            ]
            self.line_to_position = {0: (0, 0, 0), 1: (0, 0, 0), 2: (0, 0, 0), 3: (0, 0, 0)}
            self.console = Console()
            self.scroll_offset = 0
            self.selection_active = False
            self.selection_start = None
            self.selection_end = None
    
    # Create mock reader instance
    mock_reader = MockReader()
    
    # Enable highlighting for test
    original_sentence_highlighting = config.SENTENCE_HIGHLIGHTING_ENABLED
    original_word_highlighting = config.WORD_HIGHLIGHTING_ENABLED
    config.SENTENCE_HIGHLIGHTING_ENABLED = True
    config.WORD_HIGHLIGHTING_ENABLED = True
    
    try:
        # Test the get_visible_content function
        visible_content = ui.get_visible_content(mock_reader)
        print("✓ get_visible_content executed successfully")
        
        # Check the indentation of each line
        print("\nLine formatting:")
        highlighting_found = False
        for i, line in enumerate(visible_content):
            is_indented = line.plain.startswith('    ')
            print(f"  Line {i}: {'Indented' if is_indented else 'Not indented'} - '{line.plain[:30]}...'")
            
            # Check if the line has highlighting
            has_highlighting = len(line.spans) > 0
            if has_highlighting:
                highlighting_found = True
                print(f"    Has {len(line.spans)} highlighted sections")
                for j, span in enumerate(line.spans):
                    print(f"      Span {j}: {span.style} from {span.start} to {span.end} ('{line.plain[span.start:span.end]}')")
            else:
                # Even if no spans, check if the line style is a highlight style
                line_style = str(line.style)
                if "magenta" in line_style or "yellow" in line_style:
                    highlighting_found = True
                    print(f"    Line has highlight style: {line_style}")
        
        # Verify that only the first line is indented (as expected in books)
        first_line_indented = visible_content[0].plain.startswith('    ')
        other_lines_indented = any(line.plain.startswith('    ') for line in visible_content[1:])
        
        # Verify that highlighting is applied
        if first_line_indented and not other_lines_indented:
            print("\n✓ Correctly preserved book-style indentation (only first line indented)")
        else:
            print("\n✗ Indentation not preserved correctly")
            
        if highlighting_found:
            print("✓ Highlighting is applied to content")
        else:
            print("✗ No highlighting detected")
            
        # Return success if both conditions are met
        return first_line_indented and not other_lines_indented and highlighting_found
            
    except Exception as e:
        print(f"✗ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Restore original config
        config.SENTENCE_HIGHLIGHTING_ENABLED = original_sentence_highlighting
        config.WORD_HIGHLIGHTING_ENABLED = original_word_highlighting

if __name__ == "__main__":
    success = test_highlighting_and_indentation()
    if success:
        print("\n✓ Highlighting and indentation test PASSED")
        sys.exit(0)
    else:
        print("\n✗ Highlighting and indentation test FAILED")
        sys.exit(1)