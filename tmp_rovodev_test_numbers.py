#!/usr/bin/env python3
"""
Test script to reproduce the word highlighting issue with numbers in Edge TTS.
"""
import asyncio
import os
import sys

# Add the lue package to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lue.tts.edge_tts import EdgeTTS
from rich.console import Console

async def test_edge_tts_with_numbers():
    """Test Edge TTS with sentences containing numbers."""
    console = Console()
    
    # Test sentences with numbers
    test_sentences = [
        "I have 5 apples and 3 oranges.",
        "The year 2024 was amazing.",
        "There are 10 items in the list.",
        "Chapter 1 begins here.",
        "I bought 2 books yesterday."
    ]
    
    # Initialize Edge TTS
    edge_tts = EdgeTTS(console)
    if not await edge_tts.initialize():
        console.print("[red]Failed to initialize Edge TTS[/red]")
        return
    
    for i, sentence in enumerate(test_sentences):
        console.print(f"\n[bold cyan]Testing sentence {i+1}:[/bold cyan] {sentence}")
        
        output_file = f"tmp_rovodev_test_{i}.mp3"
        
        try:
            # Generate audio with timing
            duration, word_timings = await edge_tts.generate_audio_with_timing(sentence, output_file)
            
            console.print(f"[green]Duration:[/green] {duration:.2f}s")
            console.print(f"[green]Word timings:[/green]")
            
            words_in_sentence = sentence.split()
            console.print(f"[yellow]Original words:[/yellow] {words_in_sentence}")
            console.print(f"[yellow]Number of original words:[/yellow] {len(words_in_sentence)}")
            
            console.print(f"[blue]TTS word timings:[/blue]")
            for j, (word, start, end) in enumerate(word_timings):
                console.print(f"  {j}: '{word}' ({start:.2f}s - {end:.2f}s)")
            
            console.print(f"[blue]Number of TTS words:[/blue] {len(word_timings)}")
            
            # Check for mismatch
            if len(words_in_sentence) != len(word_timings):
                console.print(f"[red]MISMATCH: Original has {len(words_in_sentence)} words, TTS has {len(word_timings)} words[/red]")
                
                # Try to identify the issue
                console.print("[yellow]Analyzing differences:[/yellow]")
                tts_words = [word for word, _, _ in word_timings]
                console.print(f"  Original: {words_in_sentence}")
                console.print(f"  TTS:      {tts_words}")
            else:
                console.print("[green]Word count matches![/green]")
            
            # Clean up
            if os.path.exists(output_file):
                os.remove(output_file)
                
        except Exception as e:
            console.print(f"[red]Error processing sentence:[/red] {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_edge_tts_with_numbers())