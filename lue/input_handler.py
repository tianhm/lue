import sys
import select
import asyncio
import subprocess

def process_input(reader):
    """Process user input from stdin."""
    try:
        if select.select([sys.stdin], [], [], 0)[0]:
            data = sys.stdin.read(1)
            
            if not data:
                return
            
            if data == '\x1b':
                reader.mouse_sequence_buffer = data
                reader.mouse_sequence_active = True
                return
            elif reader.mouse_sequence_active:
                reader.mouse_sequence_buffer += data
                
                if reader.mouse_sequence_buffer.startswith('\x1b[<') and (data == 'M' or data == 'm'):
                    sequence = reader.mouse_sequence_buffer
                    reader.mouse_sequence_buffer = ''
                    reader.mouse_sequence_active = False
                    
                    if len(sequence) > 3:
                        mouse_part = sequence[3:]
                        if mouse_part.endswith('M') or mouse_part.endswith('m'):
                            try:
                                parts = mouse_part[:-1].split(';')
                                if len(parts) >= 3:
                                    button = int(parts[0])
                                    x_pos = int(parts[1])
                                    y_pos = int(parts[2])
                                    
                                    if mouse_part.endswith('M'):
                                        if button == 0:
                                            if reader._is_click_on_progress_bar(x_pos, y_pos):
                                                if reader._handle_progress_bar_click(x_pos, y_pos):
                                                    return
                                            
                                            if not reader._is_click_on_text(x_pos, y_pos):
                                                return

                                            # Cancel any pending restart task before killing audio
                                            if hasattr(reader, 'pending_restart_task') and reader.pending_restart_task and not reader.pending_restart_task.done():
                                                reader.pending_restart_task.cancel()
                                            
                                            _kill_audio_immediately(reader)
                                            reader.loop.call_soon_threadsafe(reader._post_command_sync, ('click_jump', (x_pos, y_pos)))
                                        elif button == 64:
                                            if reader.auto_scroll_enabled:
                                                reader.auto_scroll_enabled = False
                                            reader.loop.call_soon_threadsafe(reader._post_command_sync, 'wheel_scroll_up')
                                        elif button == 65:
                                            if reader.auto_scroll_enabled:
                                                reader.auto_scroll_enabled = False
                                            reader.loop.call_soon_threadsafe(reader._post_command_sync, 'wheel_scroll_down')
                                    return
                            except (ValueError, IndexError):
                                pass
                    return
                
                elif reader.mouse_sequence_buffer.startswith('\x1b[') and len(reader.mouse_sequence_buffer) >= 3 and data in 'ABCD':
                    sequence = reader.mouse_sequence_buffer
                    reader.mouse_sequence_buffer = ''
                    reader.mouse_sequence_active = False
                    
                    _kill_audio_immediately(reader)
                    cmd = None
                    if data == 'C':
                        cmd = 'next_sentence'
                    elif data == 'D':
                        cmd = 'prev_sentence'
                    elif data == 'B':
                        cmd = 'next_paragraph'
                    elif data == 'A':
                        cmd = 'prev_paragraph'
                    
                    if cmd:
                        reader.loop.call_soon_threadsafe(reader._post_command_sync, cmd)
                    return
                
                return
            
            reader.mouse_sequence_buffer = ''
            reader.mouse_sequence_active = False
            
            if data == 'q':
                reader.running = False
                reader.command_received_event.set()
                return
            
            cmd = None
            if data == 'p':
                cmd = 'pause'
            elif data == 'h':
                cmd = 'prev_paragraph'
            elif data == 'j':
                cmd = 'prev_sentence'
            elif data == 'k':
                cmd = 'next_sentence'
            elif data == 'l':
                cmd = 'next_paragraph'
            elif data == 'i':
                cmd = 'scroll_page_up'
            elif data == 'm':
                cmd = 'scroll_page_down'
            elif data == 'u':
                cmd = 'scroll_up'
            elif data == 'n':
                cmd = 'scroll_down'
            elif data == 'a':
                cmd = 'toggle_auto_scroll'
            elif data == 't':
                cmd = 'move_to_top_visible'
            elif data == 'y':
                cmd = 'move_to_beginning'
            elif data == 'b':
                cmd = 'move_to_end'
            elif data == ',':
                cmd = 'decrease_speed'
            elif data == '.':
                cmd = 'increase_speed'
            elif data == 's':
                cmd = 'toggle_sentence_highlight'
            elif data == 'w':
                cmd = 'toggle_word_highlight'
            
            if cmd:
                reader.loop.call_soon_threadsafe(reader._post_command_sync, cmd)
                
    except Exception:
        pass

def _kill_audio_immediately(reader):
    """Kill audio playback immediately."""
    for process in reader.playback_processes[:]:
        try:
            process.kill()
        except (ProcessLookupError, AttributeError):
            pass
    try:
        subprocess.run(['pkill', '-f', 'ffplay'], check=False, 
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
