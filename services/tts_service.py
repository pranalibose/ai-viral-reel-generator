import os
import logging
import asyncio
import edge_tts

# Setup logger
logger = logging.getLogger("viral_reel_backend.tts_service")

# Map UI voice selectors to Edge TTS Neural Voices
VOICE_MAP = {
    "en_us_002": "en-US-EmmaMultilingualNeural",   # Bella
    "en_us_006": "en-US-AndrewNeural",             # Adam
    "en_us_003": "en-US-AnaNeural",                # Dolly
    "en_uk_001": "en-GB-RyanNeural"                # George
}

async def synthesize_text_async(text: str, voice_key: str, output_path: str) -> bool:
    """
    Asynchronously synthesizes text into an MP3 file using Edge-TTS.
    """
    voice = VOICE_MAP.get(voice_key, "en-US-EmmaMultilingualNeural")
    logger.info(f"Synthesizing voiceover with voice {voice} for text: '{text[:30]}...'")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        logger.info(f"Successfully saved synthesized audio to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to synthesize TTS via Edge-TTS: {e}")
        return False

def synthesize_text(text: str, voice_key: str, output_path: str) -> bool:
    """
    Synchronous wrapper to run the async synthesize function.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        # If the loop is already running (e.g. inside FastAPI async routes), run as a future task
        future = asyncio.run_coroutine_threadsafe(synthesize_text_async(text, voice_key, output_path), loop)
        return future.result()
    else:
        return loop.run_until_complete(synthesize_text_async(text, voice_key, output_path))
