import asyncio
import os
import sys
import re
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from . import config, content_parser

# ================================
# CENTRALIZED UI CONFIGURATION
# ================================
class UIIcons:
    """Central place to configure all UI icons and separators."""
    
    # Status icons
    PLAYING = "▶"
    PAUSED = "⏸"
    
    # Mode icons
    AUTO_SCROLL = "▼"
    MANUAL_MODE = "⏹"
    
    # Navigation icons
    HIGHLIGHT_UP = "⇈"
    HIGHLIGHT_DOWN = "⇊"
    ROW_NAVIGATION = "↑↓"
    PAGE_NAVIGATION = "↑↓"
    QUIT = "⏻"
    
    # Separators
    SEPARATOR = "⸱"
    
    # Progress bar
    PROGRESS_FILLED = "▓"
    PROGRESS_EMPTY = "░"
    
    # Line separators for different widths
    LINE_SEPARATOR_LONG = "───"
    LINE_SEPARATOR_MEDIUM = "──"
    LINE_SEPARATOR_SHORT = "─"

class UIColors:
    """Central place to configure all UI colors and styles."""
    
    # Status colors
    PLAYING_STATUS = "green"
    PAUSED_STATUS = "yellow"
    
    # Mode colors
    AUTO_SCROLL_ENABLED = "magenta"
    AUTO_SCROLL_DISABLED = "blue"
    
    # Control and navigation colors
    CONTROL_KEYS = "white"          # h, j, k, l, etc.
    CONTROL_ICONS = "green"   # The actual navigation icons
    ARROW_ICONS = "blue"  # Color for u/n and i/m icons
    QUIT_ICON = "red"        # Color for the q icon
    SEPARATORS = "bright_blue"      # Lines and separators
    
    # Panel and UI structure
    PANEL_BORDER = "bright_blue"
    PANEL_TITLE = "bold blue"
    
    # Text content colors
    TEXT_NORMAL = "white"      # Normal reading text
    TEXT_HIGHLIGHT = "bold magenta" # Current sentence highlight
    WORD_HIGHLIGHT = "bold yellow"  # Current word highlight
    SELECTION_HIGHLIGHT = "reverse" # Text selection highlight
    
    # Progress bar colors
    PROGRESS_BAR = "bold blue"  # Used for the progress text in title
    
    # You can easily add theme presets here:
    @classmethod
    def apply_black_theme(cls):
        """Apply a dark theme color scheme."""
        cls.PLAYING_STATUS = "black"
        cls.PAUSED_STATUS = "black"
        cls.AUTO_SCROLL_ENABLED = "black"
        cls.AUTO_SCROLL_DISABLED = "black"
        cls.CONTROL_KEYS = "black"
        cls.CONTROL_ICONS = "black"
        cls.SEPARATORS = "black"
        cls.PANEL_BORDER = "black"
        cls.PANEL_TITLE = "black"
        cls.PROGRESS_BAR = "black"
        cls.TEXT_NORMAL = "black"
        cls.TEXT_HIGHLIGHT = "white on black"
        cls.SELECTION_HIGHLIGHT = "reverse"
    
    @classmethod
    def apply_white_theme(cls):
        """Apply a light theme color scheme."""
        cls.PLAYING_STATUS = "white"
        cls.PAUSED_STATUS = "white"
        cls.AUTO_SCROLL_ENABLED = "white"
        cls.AUTO_SCROLL_DISABLED = "white"
        cls.CONTROL_KEYS = "white"
        cls.CONTROL_ICONS = "white"
        cls.SEPARATORS = "white"
        cls.PANEL_BORDER = "white"
        cls.PANEL_TITLE = "white"
        cls.PROGRESS_BAR = "white"
        cls.TEXT_NORMAL = "white"
        cls.TEXT_HIGHLIGHT = "bold white"
        cls.SELECTION_HIGHLIGHT = "reverse"
    
# Create global instances for easy access
ICONS = UIIcons()
COLORS = UIColors()

# Uncomment one of these to apply a different theme:
# COLORS.apply_black_theme()
# COLORS.apply_white_theme()

def get_terminal_size():
    """Get terminal size."""
    try:
        columns, rows = os.get_terminal_size()
        return max(columns, 40), max(rows, 10)
    except OSError:
        return 80, 24

def update_document_layout(reader):
    """Update the document layout based on terminal size."""
    reader.document_lines = []
    reader.line_to_position = {}
    reader.position_to_line = {}
    reader.paragraph_line_ranges = {}
    
    width, _ = get_terminal_size()
    available_width = max(20, width - 10)
    
    for chap_idx, chapter in enumerate(reader.chapters):
        if chap_idx > 0:
            reader.document_lines.append(Text("", style=COLORS.TEXT_NORMAL))
            
        for para_idx, paragraph in enumerate(chapter):
            paragraph_start_line = len(reader.document_lines)
            
            plain_text = Text(paragraph, justify="left", no_wrap=False, style=COLORS.TEXT_NORMAL)
            wrapped_lines = plain_text.wrap(reader.console, available_width)
            paragraph_end_line = len(reader.document_lines) + len(wrapped_lines) - 1
            
            reader.paragraph_line_ranges[(chap_idx, para_idx)] = (paragraph_start_line, paragraph_end_line)
            
            sentences = content_parser.split_into_sentences(paragraph)
            current_char_pos = 0
            for sent_idx, sentence in enumerate(sentences):
                sentence_start = current_char_pos
                sentence_end = current_char_pos + len(sentence)
                
                line_char_pos = 0
                for line_idx, line in enumerate(wrapped_lines):
                    line_start = line_char_pos
                    line_end = line_char_pos + len(line.plain)
                    
                    if line_start <= sentence_start < line_end:
                        global_line_idx = paragraph_start_line + line_idx
                        reader.position_to_line[(chap_idx, para_idx, sent_idx)] = global_line_idx
                        break
                    
                    line_char_pos = line_end
                
                current_char_pos = sentence_end + 1
            
            for line_idx in range(len(wrapped_lines)):
                global_line_idx = paragraph_start_line + line_idx
                reader.line_to_position[global_line_idx] = (chap_idx, para_idx, 0)
            
            reader.document_lines.extend(wrapped_lines)
            
            if para_idx < len(chapter) - 1:
                reader.document_lines.append(Text("", style=COLORS.TEXT_NORMAL))

    if hasattr(reader, '_initial_load_complete') and reader._initial_load_complete:
        scroll_was_set = False
        if not reader.auto_scroll_enabled and reader.resize_anchor:
            anchor_pos = reader.resize_anchor
            if anchor_pos and anchor_pos in reader.position_to_line:
                target_line = reader.position_to_line[anchor_pos]
                _, height = get_terminal_size()
                available_height = max(1, height - 4)
                max_scroll = max(0, len(reader.document_lines) - available_height)
                reader.scroll_offset = reader.target_scroll_offset = min(target_line, max_scroll)
                scroll_was_set = True
            reader.resize_anchor = None

        if not scroll_was_set:
            current_position_key = (reader.ui_chapter_idx, reader.ui_paragraph_idx, reader.ui_sentence_idx)
            reader._scroll_to_position(
                current_position_key[0],
                current_position_key[1],
                current_position_key[2],
                smooth=False
            )


def _apply_current_text_color(line):
    """Apply the current theme's text color to a line."""
    if not line.plain:
        return Text("", style=COLORS.TEXT_NORMAL)
    
    # Create a new Text object with current theme color
    new_line = Text(line.plain, justify="left", no_wrap=False, style=COLORS.TEXT_NORMAL)
    return new_line


def get_visible_content(reader):
    """Get the visible content to display."""
    width, height = get_terminal_size()
    available_height = max(1, height - 4)
    available_width = max(20, width - 10)

    start_line = int(reader.scroll_offset)
    end_line = min(len(reader.document_lines), start_line + available_height)

    visible_lines = []
    current_paragraph_key = (reader.ui_chapter_idx, reader.ui_paragraph_idx)

    highlighted_paragraph_lines = None
    if current_paragraph_key in reader.paragraph_line_ranges:
        para_start, para_end = reader.paragraph_line_ranges[current_paragraph_key]
        paragraph = reader.chapters[reader.ui_chapter_idx][reader.ui_paragraph_idx]
        sentences = content_parser.split_into_sentences(paragraph)
        highlighted_text = Text(justify="left", no_wrap=False)

        for sent_idx, sentence in enumerate(sentences):
            is_current_sentence = sent_idx == reader.ui_sentence_idx
            
            # Determine the base style for this sentence
            if is_current_sentence and config.SENTENCE_HIGHLIGHTING_ENABLED:
                base_style = COLORS.TEXT_HIGHLIGHT
            else:
                base_style = COLORS.TEXT_NORMAL
            
            # Apply word-level highlighting if enabled and this is the current sentence
            if (is_current_sentence and config.WORD_HIGHLIGHTING_ENABLED and 
                hasattr(reader, 'ui_word_idx')):
                
                # Preserve leading whitespace from the sentence, which contains paragraph indentation
                leading_whitespace = ""
                if sentence:
                    match = re.match(r"^(\s+)", sentence)
                    if match:
                        leading_whitespace = match.group(1)
                
                if leading_whitespace:
                    highlighted_text.append(leading_whitespace, style=base_style)
                    
                words = sentence.lstrip().split()
                for word_idx, word in enumerate(words):
                    if word_idx == reader.ui_word_idx:
                        highlighted_text.append(word, style=COLORS.WORD_HIGHLIGHT)
                    else:
                        highlighted_text.append(word, style=base_style)
                    if word_idx < len(words) - 1:
                        highlighted_text.append(" ", style=base_style)
            else:
                # No word highlighting, just apply the base style to the entire sentence
                highlighted_text.append(sentence, style=base_style)
            
            if sent_idx < len(sentences) - 1:
                highlighted_text.append(" ", style=COLORS.TEXT_NORMAL)

        highlighted_paragraph_lines = highlighted_text.wrap(reader.console, available_width)

    for i in range(start_line, end_line):
        if i < len(reader.document_lines):
            line = reader.document_lines[i]

            # Apply current theme text color
            line = _apply_current_text_color(line)

            if (i in reader.line_to_position and
                reader.line_to_position[i][:2] == current_paragraph_key and
                highlighted_paragraph_lines is not None):

                para_start, para_end = reader.paragraph_line_ranges[current_paragraph_key]
                line_offset = i - para_start

                if 0 <= line_offset < len(highlighted_paragraph_lines):
                    line = highlighted_paragraph_lines[line_offset]

            line = _apply_selection_highlighting(reader, line, i)

            visible_lines.append(line)
        else:
            visible_lines.append(Text("", style=COLORS.TEXT_NORMAL))

    if len(visible_lines) > available_height:
        visible_lines = visible_lines[:available_height]

    return visible_lines

def _apply_selection_highlighting(reader, line, line_index):
    """Apply selection highlighting to a line if it's within the selection range."""
    if not reader.selection_active or not reader.selection_start or not reader.selection_end:
        return line
    
    start_line, start_char = reader.selection_start
    end_line, end_char = reader.selection_end
    
    # Ensure start comes before end
    if start_line > end_line or (start_line == end_line and start_char > end_char):
        start_line, start_char, end_line, end_char = end_line, end_char, start_line, start_char
    
    # Check if this line is within the selection range
    if not (start_line <= line_index <= end_line):
        return line
    
    line_text = line.plain
    if not line_text:
        return line
    
    # Create a new Text object with selection highlighting
    new_line = Text(justify="left", no_wrap=False)
    
    if start_line == end_line == line_index:
        # Single line selection
        selection_start = max(0, min(start_char, len(line_text)))
        selection_end = max(0, min(end_char, len(line_text)))
        
        # Add text before selection
        if selection_start > 0:
            new_line.append(line_text[:selection_start], style=COLORS.TEXT_NORMAL)
        
        # Add selected text with highlighting
        if selection_end > selection_start:
            new_line.append(line_text[selection_start:selection_end], style=COLORS.SELECTION_HIGHLIGHT)
        
        # Add text after selection
        if selection_end < len(line_text):
            new_line.append(line_text[selection_end:], style=COLORS.TEXT_NORMAL)
            
    elif line_index == start_line:
        # First line of multi-line selection
        selection_start = max(0, min(start_char, len(line_text)))
        
        # Add text before selection
        if selection_start > 0:
            new_line.append(line_text[:selection_start], style=COLORS.TEXT_NORMAL)
        
        # Add selected text from start_char to end of line
        if selection_start < len(line_text):
            new_line.append(line_text[selection_start:], style=COLORS.SELECTION_HIGHLIGHT)
            
    elif line_index == end_line:
        # Last line of multi-line selection
        selection_end = max(0, min(end_char, len(line_text)))
        
        # Add selected text from beginning to end_char
        if selection_end > 0:
            new_line.append(line_text[:selection_end], style=COLORS.SELECTION_HIGHLIGHT)
        
        # Add text after selection
        if selection_end < len(line_text):
            new_line.append(line_text[selection_end:], style=COLORS.TEXT_NORMAL)
            
    else:
        # Middle line of multi-line selection - entire line is selected
        new_line.append(line_text, style=COLORS.SELECTION_HIGHLIGHT)
    
    return new_line


def get_compact_subtitle(reader, width):
    """Generate a compact subtitle based on terminal width."""
    status_icon = ICONS.PLAYING if not reader.is_paused else ICONS.PAUSED
    status_text = "PLAYING" if not reader.is_paused else "PAUSED"
    
    # Add speed indicator if not normal speed
    speed_indicator = reader._get_speed_display() if hasattr(reader, '_get_speed_display') else ""
    
    # Control text with centralized colors
    nav_text_1 = f"[{COLORS.CONTROL_KEYS}]h{ICONS.SEPARATOR}j[/{COLORS.CONTROL_KEYS}]"
    nav_text_2 = f"[{COLORS.CONTROL_KEYS}]k{ICONS.SEPARATOR}l[/{COLORS.CONTROL_KEYS}]"
    page_text = f"[{COLORS.CONTROL_KEYS}]u{ICONS.SEPARATOR}n[/{COLORS.CONTROL_KEYS}]"
    scroll_text = f"[{COLORS.CONTROL_KEYS}]i{ICONS.SEPARATOR}m[/{COLORS.CONTROL_KEYS}]"
    quit_text = f"[{COLORS.CONTROL_KEYS}]q[/{COLORS.CONTROL_KEYS}]"
    auto_text = f"[{COLORS.CONTROL_KEYS}]a{ICONS.SEPARATOR}t[/{COLORS.CONTROL_KEYS}]"
    
    if reader.auto_scroll_enabled:
        auto_scroll_icon = ICONS.AUTO_SCROLL
        auto_scroll_text = "AUTO"
    else:
        auto_scroll_icon = ICONS.MANUAL_MODE
        auto_scroll_text = "MANUAL"
    
    if width >= 80:
        base_sep = ICONS.LINE_SEPARATOR_LONG
        
        # Construct status part with proper spacing
        if speed_indicator:
            status_part = f"[{COLORS.CONTROL_KEYS}]p[/{COLORS.CONTROL_KEYS}] {status_icon} {speed_indicator} {status_text}"
        else:
            status_part = f"[{COLORS.CONTROL_KEYS}]p[/{COLORS.CONTROL_KEYS}] {status_icon} {status_text}"
            
        status_extra = 1 if status_text == "PAUSED" else 0
        status_sep = base_sep + (ICONS.LINE_SEPARATOR_SHORT * status_extra)
        
        auto_part = f"{auto_scroll_icon} {auto_scroll_text}"
        auto_extra = 2 if auto_scroll_text == "AUTO" else 0
        auto_sep = base_sep + (ICONS.LINE_SEPARATOR_SHORT * auto_extra)
        
        controls_text = f"{nav_text_1} [{COLORS.CONTROL_ICONS}]{ICONS.HIGHLIGHT_UP}[/{COLORS.CONTROL_ICONS}] {nav_text_2} [{COLORS.CONTROL_ICONS}]{ICONS.HIGHLIGHT_DOWN}[/{COLORS.CONTROL_ICONS}] [{COLORS.SEPARATORS}]{base_sep}[/{COLORS.SEPARATORS}] {page_text} [{COLORS.ARROW_ICONS}]{ICONS.ROW_NAVIGATION}[/{COLORS.ARROW_ICONS}] {scroll_text} [{COLORS.ARROW_ICONS}]{ICONS.PAGE_NAVIGATION}[/{COLORS.ARROW_ICONS}] [{COLORS.SEPARATORS}]{base_sep}[/{COLORS.SEPARATORS}] {quit_text} [{COLORS.QUIT_ICON}]{ICONS.QUIT}[/{COLORS.QUIT_ICON}]"
        
        playing_color = COLORS.PLAYING_STATUS if not reader.is_paused else COLORS.PAUSED_STATUS
        auto_color = COLORS.AUTO_SCROLL_ENABLED if reader.auto_scroll_enabled else COLORS.AUTO_SCROLL_DISABLED
        
        return (
            f"[{playing_color}]{status_part}[/{playing_color}] "
            f"[{COLORS.SEPARATORS}]{status_sep}[/{COLORS.SEPARATORS}] "
            f"{auto_text} "
            f"[{auto_color}]{auto_part}[/{auto_color}] "
            f"[{COLORS.SEPARATORS}]{auto_sep}[/{COLORS.SEPARATORS}] "
            f"{controls_text}"
        )
    elif width >= 70:
        separator = ICONS.LINE_SEPARATOR_LONG
        
        # Construct status part with proper spacing
        if speed_indicator:
            icon_status = f"[{COLORS.CONTROL_KEYS}]p[/{COLORS.CONTROL_KEYS}] {status_icon}{speed_indicator}"
        else:
            icon_status = f"[{COLORS.CONTROL_KEYS}]p[/{COLORS.CONTROL_KEYS}] {status_icon}"
            
        icon_auto = f"{auto_scroll_icon}"
        controls_text = f"[{COLORS.SEPARATORS}]{separator}[/{COLORS.SEPARATORS}] {nav_text_1} [{COLORS.CONTROL_ICONS}]{ICONS.HIGHLIGHT_UP}[/{COLORS.CONTROL_ICONS}] {nav_text_2} [{COLORS.CONTROL_ICONS}]{ICONS.HIGHLIGHT_DOWN}[/{COLORS.CONTROL_ICONS}] [{COLORS.SEPARATORS}]{separator}[/{COLORS.SEPARATORS}] {page_text} [{COLORS.ARROW_ICONS}]{ICONS.ROW_NAVIGATION}[/{COLORS.ARROW_ICONS}] {scroll_text} [{COLORS.ARROW_ICONS}]{ICONS.PAGE_NAVIGATION}[/{COLORS.ARROW_ICONS}] [{COLORS.SEPARATORS}]{separator}[/{COLORS.SEPARATORS}] {quit_text} [{COLORS.QUIT_ICON}]{ICONS.QUIT}[/{COLORS.QUIT_ICON}]"
        
        playing_color = COLORS.PLAYING_STATUS if not reader.is_paused else COLORS.PAUSED_STATUS
        auto_color = COLORS.AUTO_SCROLL_ENABLED if reader.auto_scroll_enabled else COLORS.AUTO_SCROLL_DISABLED
        
        return f"[{playing_color}]{icon_status}[/{playing_color}] [{COLORS.SEPARATORS}]{separator}[/{COLORS.SEPARATORS}] {auto_text} [{auto_color}]{icon_auto}[/{auto_color}] {controls_text}"
    elif width >= 65:
        separator = ICONS.LINE_SEPARATOR_MEDIUM
        
        # Construct status part with proper spacing
        if speed_indicator:
            icon_status = f"[{COLORS.CONTROL_KEYS}]p[/{COLORS.CONTROL_KEYS}] {status_icon}{speed_indicator}"
        else:
            icon_status = f"[{COLORS.CONTROL_KEYS}]p[/{COLORS.CONTROL_KEYS}] {status_icon}"
            
        icon_auto = f"{auto_scroll_icon}"
        controls_text = f"[{COLORS.SEPARATORS}]{separator}[/{COLORS.SEPARATORS}] {nav_text_1} [{COLORS.CONTROL_ICONS}]{ICONS.HIGHLIGHT_UP}[/{COLORS.CONTROL_ICONS}] {nav_text_2} [{COLORS.CONTROL_ICONS}]{ICONS.HIGHLIGHT_DOWN}[/{COLORS.CONTROL_ICONS}] [{COLORS.SEPARATORS}]{separator}[/{COLORS.SEPARATORS}] {page_text} [{COLORS.ARROW_ICONS}]{ICONS.ROW_NAVIGATION}[/{COLORS.ARROW_ICONS}] {scroll_text} [{COLORS.ARROW_ICONS}]{ICONS.PAGE_NAVIGATION}[/{COLORS.ARROW_ICONS}] [{COLORS.SEPARATORS}]{separator}[/{COLORS.SEPARATORS}] {quit_text} [{COLORS.QUIT_ICON}]{ICONS.QUIT}[/{COLORS.QUIT_ICON}]"
        
        playing_color = COLORS.PLAYING_STATUS if not reader.is_paused else COLORS.PAUSED_STATUS
        auto_color = COLORS.AUTO_SCROLL_ENABLED if reader.auto_scroll_enabled else COLORS.AUTO_SCROLL_DISABLED
        
        return f"[{playing_color}]{icon_status}[/{playing_color}] [{COLORS.SEPARATORS}]{separator}[/{COLORS.SEPARATORS}] {auto_text} [{auto_color}]{icon_auto}[/{auto_color}] {controls_text}"
    else:
        separator = ICONS.LINE_SEPARATOR_SHORT
        
        # Construct status part with proper spacing
        if speed_indicator:
            icon_status = f"[{COLORS.CONTROL_KEYS}]p[/{COLORS.CONTROL_KEYS}] {status_icon}{speed_indicator}"
        else:
            icon_status = f"[{COLORS.CONTROL_KEYS}]p[/{COLORS.CONTROL_KEYS}] {status_icon}"
            
        icon_auto = f"{auto_scroll_icon}"
        controls_text = f"[{COLORS.SEPARATORS}]{separator}[/{COLORS.SEPARATORS}] {nav_text_1} [{COLORS.CONTROL_ICONS}]{ICONS.HIGHLIGHT_UP}[/{COLORS.CONTROL_ICONS}] {nav_text_2} [{COLORS.CONTROL_ICONS}]{ICONS.HIGHLIGHT_DOWN}[/{COLORS.CONTROL_ICONS}] [{COLORS.SEPARATORS}]{separator}[/{COLORS.SEPARATORS}] {page_text} [{COLORS.ARROW_ICONS}]{ICONS.ROW_NAVIGATION}[/{COLORS.ARROW_ICONS}] {scroll_text} [{COLORS.ARROW_ICONS}]{ICONS.PAGE_NAVIGATION}[/{COLORS.ARROW_ICONS}] [{COLORS.SEPARATORS}]{separator}[/{COLORS.SEPARATORS}] {quit_text} [{COLORS.QUIT_ICON}]{ICONS.QUIT}[/{COLORS.QUIT_ICON}]"
        
        playing_color = COLORS.PLAYING_STATUS if not reader.is_paused else COLORS.PAUSED_STATUS
        auto_color = COLORS.AUTO_SCROLL_ENABLED if reader.auto_scroll_enabled else COLORS.AUTO_SCROLL_DISABLED
        
        return f"[{playing_color}]{icon_status}[/{playing_color}] [{COLORS.SEPARATORS}]{separator}[/{COLORS.SEPARATORS}] {auto_text} [{auto_color}]{icon_auto}[/{auto_color}] {controls_text}"
        
async def display_ui(reader):
    """Display the UI."""
    if reader.render_lock.locked():
        return
    
    async with reader.render_lock:
        try:
            width, height = get_terminal_size()
            
            progress_percent = reader._calculate_ui_progress_percentage()
            rounded_scroll = round(reader.scroll_offset, 1)
            current_state = (
                reader.ui_chapter_idx, reader.ui_paragraph_idx, reader.ui_sentence_idx,
                getattr(reader, 'ui_word_idx', 0),  # Add word index to trigger UI updates
                rounded_scroll, reader.is_paused, int(progress_percent),
                width, height, reader.auto_scroll_enabled, reader.selection_active,
                reader.selection_start, reader.selection_end,
                # Add playback speed to trigger UI updates when speed changes
                reader.playback_speed
            )
            
            if reader.last_rendered_state == current_state and reader.last_terminal_size == (width, height):
                return
            
            reader.last_rendered_state = current_state
            reader.last_terminal_size = (width, height)
            
            visible_lines = get_visible_content(reader)
            book_content = Text("")
            for i, line in enumerate(visible_lines):
                book_content.append(line)
                if i < len(visible_lines) - 1:
                    book_content.append("\n")
            
            progress_bar_width = 10
            filled_blocks = int((progress_percent / 100) * progress_bar_width)
            empty_blocks = progress_bar_width - filled_blocks
            progress_bar = ICONS.PROGRESS_FILLED * filled_blocks + ICONS.PROGRESS_EMPTY * empty_blocks
            
            percentage_text = f"{int(progress_percent)}% {progress_bar}"
            
            available_width = width - len(percentage_text) - 6
            
            if len(reader.book_title) > available_width:
                title_text = f"{reader.book_title[:available_width-3]}..."
            else:
                title_text = reader.book_title
            
            used_space = len(title_text) + len(percentage_text) + 2
            remaining_space = width - used_space - 6
            connecting_line = ICONS.LINE_SEPARATOR_SHORT * max(0, remaining_space)
            
            progress_text = f"{title_text} {connecting_line} {percentage_text}"
            
            sys.stdout.write('\033[?25l\033[2J\033[H')
            
            temp_console = Console(width=width, height=height, force_terminal=True)
            
            subtitle = get_compact_subtitle(reader, width)
            
            book_panel = Panel(
                book_content,
                title=f"[{COLORS.PANEL_TITLE}]{progress_text}[/{COLORS.PANEL_TITLE}]",
                subtitle=subtitle,
                border_style=COLORS.PANEL_BORDER,
                padding=(1, 4),
                title_align="center",
                subtitle_align="center",
                width=width,
                height=height,
                expand=False
            )
            
            with temp_console.capture() as capture:
                temp_console.print(book_panel, end='', overflow='crop')
            
            output = capture.get()
            output_lines = output.split('\n')
            if len(output_lines) > height:
                output_lines = output_lines[:height]
                output = '\n'.join(output_lines)
            
            sys.stdout.write(output)
            sys.stdout.flush()
            
        except (IndexError, ValueError):
            pass
