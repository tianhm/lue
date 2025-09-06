"""
Word-level timing calculation module for the Lue eBook reader.
"""

import logging
from typing import List, Tuple, Optional, Dict, Any


def create_word_mapping(original_words: List[str], tts_word_timings: List[Tuple[str, float, float]]) -> Optional[List[int]]:
    """
    Create a mapping from original word indices to TTS word timing indices.
    This handles cases where TTS combines words (e.g., "Chapter 1" -> "Chapter 1").
    
    Args:
        original_words: List of words from the original text
        tts_word_timings: List of (word, start_time, end_time) tuples from TTS
    
    Returns:
        List where index i contains the TTS timing index for original word i,
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


def adjust_word_timings_for_continuity(word_timings: List[Tuple[str, float, float]]) -> List[Tuple[str, float, float]]:
    """
    Adjust word timings to ensure continuity - end time of one word 
    should match start time of the next word.
    
    Args:
        word_timings: List of (word, start_time, end_time) tuples
        
    Returns:
        Adjusted list of (word, start_time, end_time) tuples
    """
    if len(word_timings) <= 1:
        return word_timings
    
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
    
    return adjusted_word_timings


def calculate_speech_duration(word_timings: List[Tuple[str, float, float]]) -> float:
    """
    Calculate the total speech duration from word timings.
    
    Args:
        word_timings: List of (word, start_time, end_time) tuples
        
    Returns:
        Speech duration in seconds
    """
    if not word_timings:
        return 0.0
    
    return max([end for _, _, end in word_timings])


def estimate_word_timings_from_duration(text: str, total_duration: float) -> List[Tuple[str, float, float]]:
    """
    Estimate word timings based on word count and total duration.
    This is a fallback when TTS doesn't provide precise timing information.
    
    Args:
        text: The text that was spoken
        total_duration: Total duration of the audio in seconds
        
    Returns:
        List of (word, start_time, end_time) tuples
    """
    words = text.split()
    if not words:
        return []
    
    # If we couldn't get duration, estimate 0.3 seconds per word
    if total_duration is None or total_duration <= 0:
        total_duration = len(words) * 0.3
    
    time_per_word = total_duration / len(words)
    word_timings = []
    
    for i, word in enumerate(words):
        start_time = i * time_per_word
        end_time = (i + 1) * time_per_word
        word_timings.append((word, start_time, end_time))
    
    return word_timings


def process_tts_timing_data(
    original_text: str,
    raw_word_timings: List[Tuple[str, float, float]],
    total_duration: float = None
) -> Dict[str, Any]:
    """
    Process raw timing data from TTS into a standardized format with all necessary
    calculations and adjustments applied.
    
    Args:
        original_text: The original text that was spoken
        raw_word_timings: Raw word timings from TTS engine
        total_duration: Total audio duration (optional, will be calculated if not provided)
        
    Returns:
        Dictionary containing:
        - word_timings: Adjusted word timings
        - speech_duration: Duration of speech content
        - total_duration: Total audio duration
        - word_mapping: Mapping from original words to TTS timings
    """
    try:
        # If no raw timings provided, estimate from duration
        if not raw_word_timings:
            if total_duration is None:
                logging.warning("No timing data and no duration provided, using fallback estimation")
                total_duration = len(original_text.split()) * 0.3
            
            word_timings = estimate_word_timings_from_duration(original_text, total_duration)
            speech_duration = total_duration
        else:
            # Adjust raw timings for continuity
            word_timings = adjust_word_timings_for_continuity(raw_word_timings)
            speech_duration = calculate_speech_duration(word_timings)
        
        # Create word mapping
        original_words = original_text.split()
        word_mapping = create_word_mapping(original_words, word_timings)
        
        # Use provided total_duration or fall back to speech_duration
        final_total_duration = total_duration if total_duration is not None else speech_duration
        
        return {
            "word_timings": word_timings,
            "speech_duration": speech_duration,
            "total_duration": final_total_duration,
            "word_mapping": word_mapping
        }
        
    except Exception as e:
        logging.error(f"Error processing TTS timing data: {e}", exc_info=True)
        # Return fallback data
        fallback_duration = len(original_text.split()) * 0.3
        fallback_timings = estimate_word_timings_from_duration(original_text, fallback_duration)
        
        return {
            "word_timings": fallback_timings,
            "speech_duration": fallback_duration,
            "total_duration": fallback_duration,
            "word_mapping": create_word_mapping(original_text.split(), fallback_timings)
        }


def validate_timing_data(timing_data: Dict[str, Any]) -> bool:
    """
    Validate that timing data contains all required fields and is properly formatted.
    
    Args:
        timing_data: Dictionary containing timing information
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["word_timings", "speech_duration", "total_duration"]
    
    for field in required_fields:
        if field not in timing_data:
            return False
    
    word_timings = timing_data["word_timings"]
    if not isinstance(word_timings, list):
        return False
    
    # Check that each timing entry is properly formatted
    for timing in word_timings:
        if not isinstance(timing, tuple) or len(timing) != 3:
            return False
        word, start_time, end_time = timing
        if not isinstance(word, str) or not isinstance(start_time, (int, float)) or not isinstance(end_time, (int, float)):
            return False
        if start_time < 0 or end_time < start_time:
            return False
    
    return True