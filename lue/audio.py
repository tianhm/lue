import asyncio
import os
import re
import subprocess
import logging
from . import config

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
                sentences = re.split(r'(?<=[.!?])\s+', reader.chapters[c][p])
                text = sentences[s]
            except IndexError: break
            if not text or not text.strip():
                next_pos = reader._advance_position(producer_pos, wrap=False)
                if not next_pos: break
                producer_pos = next_pos
                continue

            output_format = reader.tts_model.output_format
            output_filename = f"{config.AUDIO_BUFFERS[buffer_index]}.{output_format}"
            
            try:
                if not reader.running: break
                
                # Check if output file already exists and remove it
                for attempt in range(3):
                    try:
                        if os.path.exists(output_filename):
                            os.remove(output_filename)
                        break
                    except OSError:
                        if attempt < 2:
                            await asyncio.sleep(0.05)
                
                await reader.tts_model.generate_audio(text, output_filename)
                if not reader.running: break
                await asyncio.wait_for(reader.audio_queue.put((output_filename, *producer_pos)), timeout=1.0)
                next_pos = reader._advance_position(producer_pos, wrap=False)
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
                    # Wait for remaining playback tasks to finish before setting the event
                    if reader.active_playback_tasks:
                        await asyncio.gather(*reader.active_playback_tasks, return_exceptions=True)
                    reader.playback_finished_event.set()
                    break
                audio_file, c, p, s = item
                if not os.path.exists(audio_file):
                    reader.audio_queue.task_done()
                    continue
                duration = await get_audio_duration(audio_file)
                if duration is None or duration <= 0:
                    reader.audio_queue.task_done()
                    continue
                try:
                    reader.loop.call_soon_threadsafe(reader._post_command_sync, ('_update_highlight', (c, p, s)))
                except RuntimeError:
                    reader.audio_queue.task_done()
                    break
                try:
                    process = await asyncio.create_subprocess_exec('ffplay', '-nodisp', '-autoexit', '-loglevel', 'error', audio_file, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    reader.playback_processes.append(process)
                except Exception:
                    reader.audio_queue.task_done()
                    continue

                async def await_and_remove(proc, file):
                    task = asyncio.current_task()
                    try:
                        await proc.wait()
                    except Exception:
                        pass
                    finally:
                        try:
                            if proc in reader.playback_processes:
                                reader.playback_processes.remove(proc)
                        except ValueError:
                            pass
                        for attempt in range(3):
                            try:
                                if os.path.exists(file):
                                    os.remove(file)
                                break
                            except OSError:
                                if attempt < 2:
                                    await asyncio.sleep(0.05)
                        if task in reader.active_playback_tasks:
                            reader.active_playback_tasks.remove(task)

                playback_task = asyncio.create_task(await_and_remove(process, audio_file))
                reader.active_playback_tasks.append(playback_task)
                
                # Use TTS-specific overlap if available, otherwise use default
                overlap_seconds = config.OVERLAP_SECONDS
                if reader.tts_model and hasattr(reader.tts_model, 'get_overlap_seconds'):
                    tts_overlap = reader.tts_model.get_overlap_seconds()
                    if tts_overlap is not None:
                        overlap_seconds = tts_overlap
                
                await asyncio.sleep(max(0.1, duration - overlap_seconds))
                reader.audio_queue.task_done()
            except asyncio.TimeoutError:
                if not reader.running:
                    break
                continue
            except asyncio.CancelledError:
                break
    except asyncio.CancelledError:
        pass
    finally:
        # Clean up any remaining processes on exit
        for process in reader.playback_processes.copy():
            try:
                if process.returncode is None:
                    process.terminate()
            except (ProcessLookupError, AttributeError):
                pass