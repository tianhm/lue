# Word-Level Timing in Lue

Lue now supports precise word-level timing for improved text highlighting accuracy during text-to-speech playback. This feature enhances the reading experience by synchronizing the visual highlighting with the actual spoken words.

## How It Works

### Edge TTS (Online)
The Edge TTS implementation leverages Microsoft's word boundary events to provide precise timing information:

1. When generating audio, Edge TTS emits `WordBoundary` events that contain:
   - The exact word being spoken
   - The start time (offset) in 100-nanosecond units
   - The duration in 100-nanosecond units

2. These timing events are converted to seconds and stored with the generated audio file.

3. During playback, the word update loop uses these precise timings to determine which word should be highlighted at any given moment.

### Kokoro TTS (Offline)
The Kokoro TTS implementation provides duration information through its `pred_dur` tensors:

1. Kokoro generates phoneme-level duration predictions during audio synthesis.

2. These durations are used to calculate word-level timing information.

3. The timing data is stored with the generated audio file for accurate highlighting.

### Fallback Implementation
For TTS models that don't provide native timing information, Lue uses a fallback approach:

1. The total audio duration is measured using `ffprobe`.

2. The duration is evenly distributed across all words in the sentence.

3. This provides reasonable timing approximation for highlighting.

## Benefits

- **Improved Accuracy**: Word highlighting now aligns precisely with spoken words rather than estimated timing.
- **Better User Experience**: Readers can follow along more easily with the narration.
- **Cross-Model Support**: Both online (Edge) and offline (Kokoro) TTS models provide accurate timing.
- **Backward Compatibility**: Falls back to estimation for models without native timing support.

## Technical Implementation

The implementation involves several key components:

1. **TTS Base Class**: Extended with `generate_audio_with_timing()` method that TTS implementations can override.

2. **Edge TTS**: Uses the `boundary="WordBoundary"` parameter to receive precise timing events.

3. **Kokoro TTS**: Extracts duration information from the model's `pred_dur` tensors.

4. **Audio System**: Modified to handle timing information alongside audio files.

5. **Word Update Loop**: Enhanced to use precise timing when available, falling back to estimation when not.

## Usage

The precise word timing feature is automatically enabled when using supported TTS models. No additional configuration is required - simply use Lue as normal and enjoy improved word highlighting accuracy.

For developers extending Lue with new TTS models, implementing the `generate_audio_with_timing()` method will enable precise word highlighting for your model.