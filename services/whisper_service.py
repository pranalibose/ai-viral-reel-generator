import os
import json
import logging
import subprocess
from typing import List, Dict, Any

# Setup logger
logger = logging.getLogger("viral_reel_backend.whisper_service")

# Try to import faster-whisper to handle transcription
HAS_WHISPER = False
try:
    from faster_whisper import WhisperModel
    HAS_WHISPER = True
except ImportError:
    logger.warning("faster-whisper package is not available. Using heuristic word-level alignment.")

_whisper_model = None

def get_whisper_model():
    """
    Lazy load Whisper model to save memory startup cost.
    """
    global _whisper_model, HAS_WHISPER
    if not HAS_WHISPER:
        return None
    if _whisper_model is None:
        try:
            logger.info("Initializing faster-whisper 'tiny' model on CPU...")
            # We use 'tiny' because it loads extremely fast, compiles on CPU, and is lightweight
            _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
        except Exception as e:
            logger.error(f"Failed to load WhisperModel: {e}. Defaulting to heuristic aligner.")
            HAS_WHISPER = False
    return _whisper_model

def get_audio_duration_ffprobe(audio_path: str) -> float:
    """
    Retrieves the duration of an audio file in seconds using ffprobe.
    """
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Failed to run ffprobe on {audio_path}: {e}")
        return 0.0

def align_words(audio_path: str, text: str, start_offset: float = 0.0) -> List[Dict[str, Any]]:
    """
    Extracts word timestamps for subtitles. Maps words in 'text' to exact playback times.
    """
    duration = get_audio_duration_ffprobe(audio_path)
    if duration <= 0:
        words_count = len(text.split())
        duration = max(1.0, words_count / 2.4) # Guessing 2.4 words per second

    model = get_whisper_model()
    if model and HAS_WHISPER:
        try:
            logger.info(f"Running Whisper word-level alignment for audio: {audio_path}")
            segments, info = model.transcribe(audio_path, word_timestamps=True)
            aligned_words = []
            
            for segment in segments:
                if not segment.words:
                    continue
                for w in segment.words:
                    # Whisper words sometimes contain spaces, clean them up
                    aligned_words.append({
                        "word": w.word.strip(),
                        "start": round(start_offset + w.start, 2),
                        "end": round(start_offset + w.end, 2)
                    })
            if aligned_words:
                logger.info(f"Whisper aligned {len(aligned_words)} words.")
                return aligned_words
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}. Falling back to heuristic alignment.")

    # Linear Heuristic Fallback
    logger.info("Whisper unavailable. Performing heuristic/linear word alignment.")
    words = text.split()
    if not words:
        return []
        
    word_duration = duration / len(words)
    aligned_words = []
    
    for idx, w in enumerate(words):
        w_start = start_offset + (idx * word_duration)
        w_end = w_start + word_duration
        aligned_words.append({
            "word": w.strip(),
            "start": round(w_start, 2),
            "end": round(w_end, 2)
        })
        
    return aligned_words
