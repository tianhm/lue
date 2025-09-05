import os
import asyncio
import logging
from rich.console import Console

from .base import TTSBase
from .. import config

class EdgeTTS(TTSBase):
    """TTS implementation for Microsoft Edge's online TTS service."""

    @property
    def name(self) -> str:
        return "edge"

    @property
    def output_format(self) -> str:
        return "mp3"

    def __init__(self, console: Console, voice: str = None, lang: str = None):
        super().__init__(console, voice, lang)
        self.edge_tts = None
        if self.voice is None:
            self.voice = config.TTS_VOICES.get(self.name)

    async def initialize(self) -> bool:
        """Checks if the edge-tts library is available."""
        try:
            import edge_tts
            self.edge_tts = edge_tts
            self.initialized = True
            self.console.print("[green]Edge TTS model is available.[/green]")
            return True
        except ImportError:
            self.console.print("[bold red]Error: 'edge-tts' package not found.[/bold red]")
            self.console.print("[yellow]Please run 'pip install edge-tts' to use this TTS model.[/yellow]")
            logging.error("'edge-tts' is not installed.")
            return False

    async def generate_audio_with_timing(self, text: str, output_path: str):
        """
        Generates audio from text using edge-tts and saves it to a file,
        returning word timing information.
        
        Returns:
            tuple: (audio_duration, word_timings) where word_timings is a list of 
                   (word, start_time, end_time) tuples in seconds
        """
        if not self.initialized:
            raise RuntimeError("Edge TTS has not been initialized.")
        
        try:
            communicate = self.edge_tts.Communicate(text, self.voice, boundary="WordBoundary")
            
            # Collect word timing information
            word_timings = []
            audio_chunks = []
            
            async for chunk in communicate.stream():
                if chunk['type'] == 'WordBoundary':
                    # Convert from 100-nanosecond units to seconds
                    start_time = chunk['offset'] / 10000000.0
                    end_time = (chunk['offset'] + chunk['duration']) / 10000000.0
                    word_timings.append((chunk['text'], start_time, end_time))
                elif chunk['type'] == 'audio':
                    audio_chunks.append(chunk['data'])
            
            # Save audio to file
            with open(output_path, 'wb') as f:
                for chunk in audio_chunks:
                    f.write(chunk)
            
            # Adjust word timings to ensure continuity - end time of one word 
            # should match start time of the next word
            if len(word_timings) > 1:
                adjusted_word_timings = []
                for i in range(len(word_timings)):
                    word, start_time, end_time = word_timings[i]
                    # For all words except the last one, use the start time of the next word as end time
                    if i < len(word_timings) - 1:
                        next_start_time = word_timings[i + 1][1]
                        adjusted_end_time = next_start_time
                    else:
                        # For the last word, keep the original end time
                        adjusted_end_time = end_time
                    adjusted_word_timings.append((word, start_time, adjusted_end_time))
                word_timings = adjusted_word_timings
            
            # Calculate total audio duration from word timings
            audio_duration = max([end for _, _, end in word_timings]) if word_timings else 0
            
            return audio_duration, word_timings
            
        except Exception as e:
            logging.error(f"Edge TTS audio generation failed for text: '{text[:50]}...'", exc_info=True)
            raise e

    async def generate_audio(self, text: str, output_path: str):
        """Generates audio from text using edge-tts and saves it to a file."""
        if not self.initialized:
            raise RuntimeError("Edge TTS has not been initialized.")
        try:
            communicate = self.edge_tts.Communicate(text, self.voice)
            await communicate.save(output_path)
        except Exception as e:
            logging.error(f"Edge TTS audio generation failed for text: '{text[:50]}...'", exc_info=True)
            raise e

    async def warm_up(self):
        """Warms up the TTS model by making a short request."""
        if not self.initialized:
            return

        self.console.print("[bold cyan]Warming up the Edge TTS model...[/bold cyan]")
        warmup_file = os.path.join(config.AUDIO_DATA_DIR, f".warmup_edge.{self.output_format}")
        try:
            await self.generate_audio("Ready.", warmup_file)
            self.console.print("[green]Edge TTS model is ready.[/green]")
        except Exception as e:
            self.console.print(f"[bold yellow]Warning: Edge model warm-up failed.[/bold yellow]")
            self.console.print(f"[yellow]This may indicate a network issue or an invalid voice name: {self.voice}[/yellow]")
            logging.warning(f"Edge TTS model warm-up failed: {e}", exc_info=True)
        finally:
            if os.path.exists(warmup_file):
                try:
                    os.remove(warmup_file)
                except OSError:
                    pass