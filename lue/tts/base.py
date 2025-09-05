"""Abstract base class for TTS models in the Lue eBook reader."""

from abc import ABC, abstractmethod
from rich.console import Console


class TTSBase(ABC):
    """
    Abstract base class for all TTS models.
    
    This class defines the interface that all TTS models must implement
    to be compatible with the Lue eBook reader.
    """

    def __init__(self, console: Console, voice: str = None, lang: str = None):
        """
        Initialize the TTS model.
        
        Args:
            console: Rich console instance for user feedback
            voice: Optional voice for the TTS model
            lang: Optional language for the TTS model
        """
        self.console = console
        self.voice = voice
        self.lang = lang
        self.initialized = False

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the unique identifier for this TTS model.
        
        Returns:
            str: Model name (e.g., 'edge', 'kokoro')
        """
        pass

    @property
    @abstractmethod
    def output_format(self) -> str:
        """
        Get the audio format this model produces.
        
        Returns:
            str: File extension without dot (e.g., 'mp3', 'wav')
        """
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the TTS model asynchronously.
        
        This method should:
        - Check for required dependencies
        - Load models if necessary
        - Handle ImportErrors gracefully
        - Set self.initialized = True on success
        
        Returns:
            bool: True if initialization succeeded, False otherwise
        """
        pass

    @abstractmethod
    async def generate_audio(self, text: str, output_path: str):
        """
        Generate audio from text and save to file.
        
        Args:
            text: Text to convert to speech
            output_path: Full path where audio file should be saved
            
        Raises:
            RuntimeError: If model is not initialized
            Exception: If audio generation fails
        """
        pass

    async def generate_audio_with_timing(self, text: str, output_path: str):
        """
        Generate audio from text and save to file, returning word timing information.
        
        This is an optional method that TTS implementations can override to provide
        precise word-level timing information for better highlighting accuracy.
        
        Args:
            text: Text to convert to speech
            output_path: Full path where audio file should be saved
            
        Returns:
            tuple: (audio_duration, word_timings) where word_timings is a list of 
                   (word, start_time, end_time) tuples in seconds
            
        Raises:
            RuntimeError: If model is not initialized
            Exception: If audio generation fails
        """
        # Default implementation falls back to regular audio generation
        # and estimates timing based on word count
        import asyncio
        await self.generate_audio(text, output_path)
        
        # Get audio duration
        from .. import audio
        duration = await audio.get_audio_duration(output_path)
        
        # Estimate timing based on word count
        words = text.split()
        if words:
            # If we couldn't get duration, estimate 0.3 seconds per word
            if duration is None or duration <= 0:
                duration = len(words) * 0.3
            
            time_per_word = duration / len(words)
            word_timings = []
            for i, word in enumerate(words):
                start_time = i * time_per_word
                end_time = (i + 1) * time_per_word
                word_timings.append((word, start_time, end_time))
            return duration, word_timings
        else:
            return duration or 0.0, []

    async def warm_up(self):
        """
        Warm up the model to reduce initial latency.
        
        This is called once after initialization to prepare the model
        for faster subsequent audio generation.
        """
        pass

    def get_overlap_seconds(self) -> float | None:
        """
        Get the TTS-specific overlap seconds for this model.
        
        Returns:
            float: Overlap seconds specific to this TTS model, or None to use default
        """
        from .. import config
        return config.TTS_OVERLAP_SECONDS.get(self.name)