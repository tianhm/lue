#!/usr/bin/env python3
import asyncio
import edge_tts

async def test_word_timing():
    text = "Hello world, this is a test."
    voice = "en-US-JennyNeural"
    
    # Create communicate object with word boundary enabled
    communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    
    # Stream the response to see what data we get
    async for chunk in communicate.stream():
        print(f"Type: {chunk['type']}")
        if chunk['type'] == 'WordBoundary':
            print(f"  Offset: {chunk['offset']}")
            print(f"  Duration: {chunk['duration']}")
            print(f"  Text: {chunk['text']}")
        elif chunk['type'] == 'audio':
            print(f"  Audio chunk size: {len(chunk['data'])} bytes")
        print()

if __name__ == "__main__":
    asyncio.run(test_word_timing())