# Lue - Developer Guide: Adding a New TTS Model

Lue is designed to automatically discover and use any TTS model that adheres to a specific "contract." To add a new model, you only need to create one Python file and edit the configuration.

The process is:
1.  Create a new file in `lue/tts/` named `yourtts_tts.py`. The filename has to end with `_tts.py`.
2.  Implement a class inside that file that inherits from `TTSBase`.
3.  Add the model's dependencies to `requirements.txt`.
4.  Add a default voice for the model in `config.py`'s `TTS_VOICES` dictionary.
5.  If the model requires a language code, add a default to `config.py`'s `TTS_LANGUAGE_CODES` dictionary.

### The `TTSBase` Contract

Your new class must implement the following properties and methods. The `Lue` application relies on this exact structure to function correctly.

-   `__init__(self, console: Console, voice: str = None, lang: str = None):`
    -   **Purpose:** The constructor for your TTS model.
    -   **Rules:** It must accept `console`, `voice`, and `lang` and pass them to the base class constructor: `super().__init__(console, voice, lang)`. The `voice` and `lang` values are passed from the command-line arguments (`--voice` and `--lang`). Not all TTS models support language selection; if yours doesn't, you can simply ignore the `lang` parameter.

-   `@property name(self) -> str:`
    -   **Purpose:** A unique, lowercase identifier for the model.
    -   **Rules:** Must match the filename (e.g., if the file is `yourtts_tts.py`, this must return `"yourtts"`). This is used for command-line arguments and configuration keys.

-   `@property output_format(self) -> str:`
    -   **Purpose:** The audio format the model produces.
    -   **Rules:** Must be `"mp3"` or `"wav"`. This tells the audio pipeline how to process the output files.

-   `async def initialize(self) -> bool:`
    -   **Purpose:** Prepare the model. This is where you should handle imports, check for API keys, and load models.
    -   **Rules:**
        -   It **must** be asynchronous.
        -   It **must** gracefully handle a missing dependency by wrapping imports in a `try...except ImportError` block and returning `False`.
        -   It **must** return `True` on success and `False` on failure.
        -   For long-running tasks (like downloading models), use `self.console.print()` to give the user feedback.
        -   If model loading is a blocking operation, it **must** be run in a separate thread to avoid freezing the UI (see template).

-   `async def generate_audio(self, text: str, output_path: str):`
    -   **Purpose:** The core function that converts a string of text into an audio file.
    -   **Rules:**
        -   It **must** be asynchronous.
        -   It **must** save the generated audio to the exact `output_path` provided. The audio pipeline depends on this file existing after the method completes.
        -   Like `initialize`, any blocking TTS generation code **must** be run in a separate thread.

### Code Template

Use this template for your `lue/tts/yourtts_tts.py` file. It includes the required structure and best practices for handling errors and blocking operations.

```python
# lue/tts/yourtts_tts.py
import os
import asyncio
import logging
from rich.console import Console

# TODO: Import any other libraries your TTS model needs.

from .base import TTSBase
from .. import config

class YourTTSTTS(TTSBase):
    """
    A brief description of your TTS model and what it does.
    """
    
    @property
    def name(self) -> str:
        # Must match the filename: yourtts_tts.py -> "yourtts"
        return "yourtts"

    @property
    def output_format(self) -> str:
        # The audio format your model produces ("mp3" or "wav")
        return "mp3"

    def __init__(self, console: Console, voice: str = None, lang: str = None):
        super().__init__(console, voice, lang)
        self.client = None # Example: an API client or model object
        
        # If the user doesn't provide a voice via --voice, use the default from config.py
        if self.voice is None:
            self.voice = config.TTS_VOICES.get(self.name)
        
        # If the user doesn't provide a language via --lang, use the default from config.py
        # Only use self.lang if your TTS model actually supports it.
        if self.lang is None:
            self.lang = config.TTS_LANGUAGE_CODES.get(self.name)

    async def initialize(self) -> bool:
        """
        Prepare the model. Check dependencies, load models, etc.
        """
        # 1. Check for dependencies and handle failure gracefully.
        try:
            # TODO: Import the actual TTS library here.
            # from your_tts_library import YourTTSClient
            pass # Replace with actual import
        except ImportError:
            self.console.print("[bold red]Error: 'your_tts_library' package not found.[/bold red]")
            self.console.print("[yellow]Please install it with 'pip install your_tts_library'[/yellow]")
            logging.error("'your_tts_library' is not installed.")
            return False

        # 2. For heavy/blocking setup tasks (like downloading or loading a large model),
        #    run them in a separate thread to keep the UI responsive.
        loop = asyncio.get_running_loop()
        try:
            self.console.print("[cyan]Initializing YourTTS model... (this may take a moment)[/cyan]")
            
            # This is a synchronous function to do the heavy lifting.
            def _blocking_init():
                # TODO: Replace with your actual model loading logic.
                # For example, check for API keys or load a model using self.lang
                # client = YourTTSClient(api_key=os.environ.get("YOURTTS_API_KEY"), language=self.lang)
                # return client
                return True # Return the client/model object on success

            # Run the blocking function in an executor.
            self.client = await loop.run_in_executor(None, _blocking_init)
            
            if not self.client:
                self.console.print("[bold red]YourTTS initialization failed. Check logs for details.[/bold red]")
                return False

            self.initialized = True
            self.console.print("[green]YourTTS model initialized successfully.[/green]")
            return True
        except Exception as e:
            self.console.print(f"[bold red]An unexpected error occurred during YourTTS initialization: {e}[/bold red]")
            logging.error("YourTTS async initialization failed.", exc_info=True)
            return False

    async def generate_audio(self, text: str, output_path: str):
        """
        Generate audio from text and save it to the given path.
        """
        if not self.initialized or not self.client:
            raise RuntimeError("YourTTS has not been initialized.")

        # This is a synchronous function to do the audio generation.
        def _blocking_generate():
            try:
                # TODO: Replace with your library's actual audio generation call.
                # Use self.voice, which was set in __init__
                # The final audio MUST be saved to the `output_path`.
                # audio_data = self.client.generate(text=text, voice=self.voice)
                # with open(output_path, "wb") as f:
                #     f.write(audio_data)
                pass # Replace with actual generation
            except Exception as e:
                logging.error(f"Error during YourTTS audio generation: {e}", exc_info=True)
                raise e
        
        # Run the blocking generation in a separate thread.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _blocking_generate)

```
