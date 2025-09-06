import asyncio
import os
import re
import subprocess
import logging
from . import config, content_parser

# This pattern is used to both clean text for TTS and detect sentence fragments.
ABBREVIATION_PATTERN = r'\b(Mr|Mrs|Ms|Dr|Prof|Rev|Hon|Jr|Sr|Cpl|Sgt|Gen|Col|Capt|Lt|Pvt|vs|viz|Co|Inc|Ltd|Corp|St|Ave|Blvd)\.'
INITIAL_PATTERN = r'\b([A-Z])\.(?=\s[A-Z])'


def _create_word_mapping(original_words, tts_word_timings):
    """
    Create a mapping from original word indices to TTS word timing indices.
    This handles cases where TTS combines words (e.g., "Chapter 1" -> "Chapter 1").
    
    Returns a list where index i contains the TTS timing index for original word i,
    or None if the original word is part of a combined TTS word.
    """
    if not original_words or not tts_word_timings:
        return None
    
    # Extract just the text from TTS timings
    tts_words = [word for word, _, _ in tts_word_timings]
    
    # If counts match, create simple 1:1 mapping
    if len(original_words) == len(tts_words):
        return list(range(len(original_words)))
    
    # Handle mismatched counts by trying to map words intelligently
    mapping = []
    tts_index = 0
    
    for orig_index, orig_word in enumerate(original_words):
        if tts_index >= len(tts_words):
            # No more TTS words, map to the last one
            mapping.append(len(tts_words) - 1)
            continue
            
        tts_word = tts_words[tts_index]
        
        # Check if the original word is contained in the current TTS word
        # Remove punctuation for comparison
        orig_clean = orig_word.strip('.,!?;:"()[]{}')
        tts_clean = tts_word.strip('.,!?;:"()[]{}')
        
        if orig_clean.lower() in tts_clean.lower():
            # This original word is part of the current TTS word
            mapping.append(tts_index)
            
            # Check if this TTS word contains multiple original words
            # by looking ahead to see if the next original word is also in this TTS word
            if (orig_index + 1 < len(original_words) and 
                tts_index < len(tts_words)):
                next_orig = original_words[orig_index + 1].strip('.,!?;:"()[]{}')
                if next_orig.lower() not in tts_clean.lower():
                    # Next original word is not in this TTS word, move to next TTS word
                    tts_index += 1
        else:
            # Try to find the original word in subsequent TTS words
            found = False
            for look_ahead in range(tts_index, min(tts_index + 3, len(tts_words))):
                look_ahead_tts = tts_words[look_ahead].strip('.,!?;:"()[]{}')
                if orig_clean.lower() in look_ahead_tts.lower():
                    mapping.append(look_ahead)
                    tts_index = look_ahead + 1
                    found = True
                    break
            
            if not found:
                # Fallback: map to current TTS word
                mapping.append(tts_index)
                tts_index += 1
    
    return mapping


def clean_tts_text(text: str) -> str:
    """
    Removes periods from specific English abbreviations and single initials
    to prevent unnatural pauses in TTS engines. Also removes loose punctuation
    marks that are not connected to any word.
    """
    # Remove periods from abbreviations and initials
    text = re.sub(ABBREVIATION_PATTERN, r'\1', text)
    text = re.sub(INITIAL_PATTERN, r'\1 ', text)
    
    # Remove loose punctuation marks that are standalone (not connected to words)
    # This pattern matches punctuation that is surrounded by whitespace or at string boundaries
    text = re.sub(r'(?:^|\s)[.,:;!?]+(?=\s|$)', ' ', text)
    
    # Remove standalone dashes that are followed by quotation marks
    # This prevents TTS engines from reading "-" as "dash" in cases like: -" 
    text = re.sub(r'(?:^|\s)-(?=")', ' ', text)
    
    # Clean up any extra whitespace that might result from removing punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

async def stop_and_clear_audio(reader):
    """Stop audio playback and clear the audio queue."""
    tasks_to_cancel = []
    for task in [reader.producer_task, reader.player_task]:
        if task and not task.done():
            task.cancel()
            tasks_to_cancel.append(task)
    if tasks_to_cancel:
        await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
    
    reader.producer_task = None
    reader.player_task = None
    
    processes_to_kill = reader.playback_processes.copy()
    reader.playback_processes.clear()
    for process in processes_to_kill:
        try:
            if process.returncode is None:
                process.terminate()
                try: await asyncio.wait_for(process.wait(), timeout=0.2)
                except asyncio.TimeoutError:
                    process.kill()
                    await asyncio.wait_for(process.wait(), timeout=0.1)
        except (ProcessLookupError, AttributeError, asyncio.TimeoutError): pass
    
    try:
        pkill_proc = await asyncio.create_subprocess_exec('pkill', '-9', '-f', 'ffplay.*buffer_', stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        await asyncio.wait_for(pkill_proc.wait(), timeout=0.3)
    except (FileNotFoundError, asyncio.TimeoutError): pass
    
    while not reader.audio_queue.empty():
        try:
            reader.audio_queue.get_nowait()
            reader.audio_queue.task_done()
        except asyncio.QueueEmpty: break
    
    await asyncio.sleep(0.1)
    
    # More aggressive cleanup with longer delays for file system operations
    for buf_base in config.AUDIO_BUFFERS:
        for ext in ['.mp3', '.wav']:
            buf = f"{buf_base}{ext}"
            for attempt in range(5):  # Increased attempts
                try:
                    if os.path.exists(buf): 
                        os.remove(buf)
                    break
                except OSError:
                    if attempt < 4: 
                        await asyncio.sleep(0.1)  # Longer delay
            

    
    await asyncio.sleep(0.2)  # Longer final delay


        
async def get_audio_duration(file_path):
    """Get the duration of an audio file."""
    command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
    process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=subprocess.DEVNULL)
    stdout, _ = await process.communicate()
    if process.returncode != 0: return None
    try: return float(stdout.decode().strip())
    except (ValueError, TypeError): return None

async def play_from_current_position(reader):
    """Start the audio producer and player loops."""
    if not reader.is_paused and reader.running and reader.tts_model:
        # Cancel existing tasks and wait for them to complete
        for task in [reader.producer_task, reader.player_task]:
            if task and not task.done():
                task.cancel()
                try: 
                    await asyncio.wait_for(task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError): 
                    pass
        
        # Ensure tasks are properly cleaned up
        reader.producer_task = None
        reader.player_task = None
        
        # Small delay to ensure cleanup is complete
        await asyncio.sleep(0.05)
        
        reader.producer_task = asyncio.create_task(_producer_loop(reader))
        reader.player_task = asyncio.create_task(_player_loop(reader))

async def _producer_loop(reader):
    """Producer loop to generate audio files."""
    if not reader.tts_model or not reader.tts_model.initialized:
        try: await asyncio.wait_for(reader.audio_queue.put(None), timeout=0.5)
        except (asyncio.TimeoutError, asyncio.CancelledError): pass
        return

    producer_pos = (reader.chapter_idx, reader.paragraph_idx, reader.sentence_idx)
    buffer_index = 0
    try:
        while reader.running:
            if reader.audio_queue.full():
                await asyncio.sleep(0.1)
                continue
            try:
                c, p, s = producer_pos
                sentences = content_parser.split_into_sentences(reader.chapters[c][p])
                text = sentences[s]
            except IndexError: break
            if not text or not text.strip():
                next_pos = reader._advance_position(producer_pos, wrap=False)
                if not next_pos: break
                producer_pos = next_pos
                continue

            # --- Start of fragment merging logic ---
            merged = False
            # Heuristic: if a "sentence" is just an abbreviation, it might be a fragment.
            # We check if the entire text matches common abbreviation patterns.
            is_abbrev_fragment = re.fullmatch(ABBREVIATION_PATTERN, text.strip())

            if is_abbrev_fragment and s + 1 < len(sentences):
                text += " " + sentences[s+1]
                merged = True
            # --- End of fragment merging logic ---

            output_format = reader.tts_model.output_format
            output_filename = f"{config.AUDIO_BUFFERS[buffer_index]}.{output_format}"
            
            try:
                if not reader.running: break
                
                for attempt in range(3):
                    try:
                        if os.path.exists(output_filename): os.remove(output_filename)
                        break
                    except OSError:
                        if attempt < 2: await asyncio.sleep(0.05)
                
                cleaned_text = clean_tts_text(text)
                
                word_timings = []
                speech_duration = None
                
                # Use the timing-aware method if available
                if hasattr(reader.tts_model, 'generate_audio_with_timing'):
                    try:
                        speech_duration, word_timings = await reader.tts_model.generate_audio_with_timing(cleaned_text, output_filename)
                    except Exception:
                        # If timing generation fails, fall back to generating without it
                        await reader.tts_model.generate_audio(cleaned_text, output_filename)
                else:
                    # Fallback to regular method
                    await reader.tts_model.generate_audio(cleaned_text, output_filename)

                # Always get the actual duration from the file
                duration = await get_audio_duration(output_filename)
                
                if not reader.running: break
                
                # If timing info is available, store it in a more structured way
                timing_info = {
                    "word_timings": word_timings,
                    "speech_duration": speech_duration,
                    "total_duration": duration
                }
                
                await asyncio.wait_for(reader.audio_queue.put((output_filename, *producer_pos, duration, timing_info)), timeout=1.0)
                
                next_pos = reader._advance_position(producer_pos, wrap=False)
                if merged:
                    # If we merged two sentences, we must advance the position an extra time.
                    if next_pos:
                        next_pos = reader._advance_position(next_pos, wrap=False)

                if not next_pos: break
                producer_pos = next_pos
                buffer_index = (buffer_index + 1) % len(config.AUDIO_BUFFERS)
            except asyncio.CancelledError: break
            except Exception as e:
                if reader.running:
                    logging.error(f"TTS Error in producer: {e}", exc_info=True)
                    await asyncio.sleep(2)
                continue
    except asyncio.CancelledError: pass
    finally:
        try: await asyncio.wait_for(reader.audio_queue.put(None), timeout=0.5)
        except (asyncio.TimeoutError, asyncio.CancelledError): pass

async def _player_loop(reader):
    """Player loop to play audio files."""
    try:
        while reader.running:
            try:
                item = await asyncio.wait_for(reader.audio_queue.get(), timeout=1.0)
                if item is None:
                    reader.audio_queue.task_done()
                    if reader.active_playback_tasks:
                        await asyncio.gather(*reader.active_playback_tasks, return_exceptions=True)
                    reader.playback_finished_event.set()
                    break
                # Unpack the queue item
                audio_file, c, p, s, duration, timing_data = item
                if isinstance(timing_data, dict):
                    timing_info = timing_data
                else:
                    # Old format, timing_data is word_timings
                    timing_info = {"word_timings": timing_data, "speech_duration": duration, "total_duration": duration}

                word_timings = timing_info.get("word_timings", [])
                
                if not os.path.exists(audio_file):
                    reader.audio_queue.task_done()
                    continue
                if duration is None or duration <= 0:
                    reader.audio_queue.task_done()
                    continue
                try:
                    reader.loop.call_soon_threadsafe(reader._post_command_sync, ('_update_highlight', (c, p, s)))
                    # Reset word index when starting a new sentence
                    reader.ui_word_idx = 0
                    # Store word timing information for this sentence
                    sentences = content_parser.split_into_sentences(reader.chapters[c][p])
                    current_text = sentences[s]
                    reader.current_sentence_words = current_text.split()
                    reader.current_sentence_duration = timing_info.get("speech_duration") or duration
                    reader.current_word_start_time = asyncio.get_event_loop().time()
                    
                    # Store precise word timings if available and create word mapping
                    if word_timings:
                        reader.current_word_timings = word_timings
                        # Create a mapping from original words to TTS word timings
                        reader.current_word_mapping = _create_word_mapping(reader.current_sentence_words, word_timings)
                    else:
                        reader.current_word_timings = None
                        reader.current_word_mapping = None
                except RuntimeError:
                    reader.audio_queue.task_done()
                    break
                try:
                    # Build ffplay command with speed control using atempo filter
                    cmd = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'error']
                    
                    # Add atempo filter if speed is not 1.0
                    if abs(reader.playback_speed - 1.0) > 0.01:
                        # atempo filter has limitations: must be between 0.5 and 2.0
                        # For speeds outside this range, we chain multiple atempo filters
                        speed = reader.playback_speed
                        filters = []
                        
                        while speed > 2.0:
                            filters.append('atempo=2.0')
                            speed /= 2.0
                        while speed < 0.5:
                            filters.append('atempo=0.5')
                            speed /= 0.5
                        if abs(speed - 1.0) > 0.01:
                            filters.append(f'atempo={speed:.3f}')
                        
                        if filters:
                            filter_chain = ','.join(filters)
                            cmd.extend(['-af', filter_chain])
                    
                    cmd.append(audio_file)
                    process = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    reader.playback_processes.append(process)
                except Exception:
                    reader.audio_queue.task_done()
                    continue

                async def await_and_remove(proc, file):
                    task = asyncio.current_task()
                    try:
                        await proc.wait()
                    except Exception: pass
                    finally:
                        try:
                            if proc in reader.playback_processes: reader.playback_processes.remove(proc)
                        except ValueError: pass
                        for attempt in range(3):
                            try:
                                if os.path.exists(file): os.remove(file)
                                break
                            except OSError:
                                if attempt < 2: await asyncio.sleep(0.05)
                        if task in reader.active_playback_tasks:
                            reader.active_playback_tasks.remove(task)

                playback_task = asyncio.create_task(await_and_remove(process, audio_file))
                reader.active_playback_tasks.append(playback_task)
                
                # Calculate dynamic overlap based on playback speed
                # Overlap should decrease as speed increases, reaching 0 at 3.00x speed and beyond
                base_overlap = config.OVERLAP_SECONDS
                if reader.tts_model and hasattr(reader.tts_model, 'get_overlap_seconds'):
                    tts_overlap = reader.tts_model.get_overlap_seconds()
                    if tts_overlap is not None:
                        base_overlap = tts_overlap
                
                # Apply speed-based overlap reduction
                # At 1.0x speed: full overlap
                # At 3.00x speed and above: 0 overlap
                # Linear decrease between 1.0x and 3.0x
                speed = reader.playback_speed
                if speed >= 3.0:
                    overlap_seconds = 0.0
                else:
                    # Calculate overlap as a linear function decreasing from base_overlap to 0
                    # as speed increases from 1.0 to 3.0
                    overlap_factor = max(0.0, min(1.0, (3.0 - speed) / (3.0 - 1.0)))
                    overlap_seconds = base_overlap * overlap_factor
                
                # Adjust duration for playback speed
                actual_duration = duration / speed
                
                await asyncio.sleep(max(0.1, actual_duration - overlap_seconds))
                reader.audio_queue.task_done()
            except asyncio.TimeoutError:
                if not reader.running: break
                continue
            except asyncio.CancelledError: break
    except asyncio.CancelledError: pass
    finally:
        for process in reader.playback_processes.copy():
            try:
                if process.returncode is None: process.terminate()
            except (ProcessLookupError, AttributeError): pass