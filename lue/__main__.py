"""Main entry point for the Lue eBook reader application."""

import asyncio
import sys
import termios
import tty
import subprocess
import argparse
import os
import platform
import platformdirs
import logging
from rich.console import Console
from .reader import Lue
from . import config, progress_manager
from .tts_manager import TTSManager, get_default_tts_model_name

def setup_logging():
    """Set up file-based logging for the application."""
    log_dir = platformdirs.user_log_dir(appname="lue", appauthor=False)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "error.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        filename=log_file,
        filemode='a',
        force=True,
    )
    logging.info("Application starting")

def setup_environment():
    """Set environment variables for TTS models."""
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["HF_HUB_ETAG_TIMEOUT"] = "10"
    os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "10"
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    if platform.system() == "Darwin" and platform.processor() == "arm":
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

async def main():
    tts_manager = TTSManager()
    available_tts = tts_manager.get_available_tts_names()
    default_tts = get_default_tts_model_name(available_tts)

    parser = argparse.ArgumentParser(
        description="A terminal-based eBook reader with TTS",
        add_help=False  # Disable automatic help to add custom one
    )
    
    parser.add_argument(
        '-h', '--help',
        action='help',
        help='Show this help message and exit'
    )
    
    parser.add_argument("file_path", nargs='?', help="Path to the eBook file (.epub, .pdf, .txt, etc.). If not provided, opens the last book you were reading.")
    parser.add_argument(
        "-f",
        "--filter",
        action="store_true",
        help="Enable PDF text cleaning filters",
    )
    
    parser.add_argument(
        "-o", "--over", type=float, help="Seconds of overlap between sentences"
    )
    
    if available_tts:
        # Add "none" option to available TTS choices
        tts_choices = ["none"] + available_tts
        parser.add_argument(
            "-t",
            "--tts",
            choices=tts_choices,
            default=default_tts,
            help=f"Select the Text-to-Speech model. Use 'none' to disable TTS (default: {default_tts})",
        )
        parser.add_argument(
            "-v",
            "--voice",
            help="Specify the voice for the TTS model",
        )
        parser.add_argument(
            "-s",
            "--speed",
            type=float,
            default=1.0,
            help="Set the speech speed (default: 1.0)",
        )
        parser.add_argument(
            "-l",
            "--lang",
            help="Specify the language for the TTS model",
        )
    args = parser.parse_args()

    # Initialize console early for printing messages
    console = Console()

    # Handle the case when no file is provided - try to open the last book
    if not args.file_path:
        last_book_path = progress_manager.find_most_recent_book()
        if last_book_path:
            console.print(f"[green]Opening last book: {os.path.basename(last_book_path)}[/green]")
            args.file_path = last_book_path
        else:
            console.print("[red]No file specified and no previous books found.[/red]")
            console.print("Please provide a file path as an argument.")
            parser.print_help()
            sys.exit(1)
    else:
        # Convert relative path to absolute path for consistency
        args.file_path = os.path.abspath(args.file_path)

    if args.over is not None:
        config.OVERLAP_SECONDS = args.over

    if args.filter:
        config.PDF_FILTERS_ENABLED = True

    setup_environment()
    setup_logging()


    for tool in ['ffprobe', 'ffplay', 'ffmpeg']:
        try:
            subprocess.run([tool, '-version'], check=True, text=True, 
                         stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print(f"\n[bold red]Error: {tool} not found.[/bold red] "
                         "Please install FFmpeg and ensure it's in your system's PATH.")
            logging.error(f"Required tool '{tool}' not found. FFmpeg may not be installed.")
            sys.exit(1)

    tts_instance = None
    if available_tts and hasattr(args, 'tts') and args.tts and args.tts != "none":
        voice = args.voice if hasattr(args, 'voice') else None
        lang = args.lang if hasattr(args, 'lang') else None
        tts_instance = tts_manager.create_model(args.tts, console, voice=voice, lang=lang)

    reader = Lue(args.file_path, tts_model=tts_instance, overlap=args.over)
    if hasattr(args, 'speed'):
        reader.playback_speed = args.speed
        
    # Hide cursor, enable mouse tracking
    sys.stdout.write('\033[?1000h\033[?1006h\033[?25l')
    sys.stdout.flush()
    
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(sys.stdin.fileno())
        
        initialized = await reader.initialize_tts()
        if not initialized and hasattr(args, 'tts') and args.tts and args.tts != "none":
            console.print(f"[bold yellow]Warning: TTS model '{args.tts}' "
                         "failed to initialize and has been disabled.[/bold yellow]")

        await reader.run()

    finally:
        sys.stdout.write('\033[?1000l\033[?1006l\033[?25h')
        sys.stdout.flush()
        if fd is not None and old_settings is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def cli():
    """Synchronous entry point for the command-line interface."""
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception as e:
        logging.critical(f"Fatal error in application startup: {e}", exc_info=True)

if __name__ == "__main__":
    cli()
