import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environmental variables from .env
load_dotenv()

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("viral_reel_backend.main")

# Import our modular services
from services.llm_service import generate_storyboard
from services.tts_service import synthesize_text
from services.whisper_service import align_words
from services.asset_service import get_pexels_video
from services.render_service import (
    compile_ass_subtitles,
    render_scene_clip,
    concatenate_videos,
    concatenate_audios,
    render_final_video
)

app = FastAPI(
    title="ViralReel.AI Backend Engine",
    description="Zero-Cost API-orchestration rendering pipeline for short-form portrait videos."
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to dashboard host origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Ensure directories exist
CACHE_DIR = os.getenv("CACHE_DIR", "./cache")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./static/outputs")
VOICEOVER_DIR = os.getenv("VOICEOVER_DIR", "./static/voiceovers")
LOFI_TRACKS_DIR = os.getenv("LOFI_TRACKS_DIR", "./static/lofi")

for path in [CACHE_DIR, OUTPUT_DIR, VOICEOVER_DIR, LOFI_TRACKS_DIR]:
    os.makedirs(path, exist_ok=True)

# Mount static outputs folder so videos are downloadable/playable from frontend
# We dynamically get the parent directory of OUTPUT_DIR (e.g., '/tmp/static' or './static') to support custom mount points
STATIC_DIR = os.path.dirname(OUTPUT_DIR)
os.makedirs(STATIC_DIR, exist_ok=True)

# Sync pre-packaged assets (e.g., presentation slides or lofi tracks) to the runtime static folder
import shutil
repo_static_dir = "./backend/static" if os.path.exists("./backend/static") else "./static"
repo_static_dir = os.path.abspath(repo_static_dir)
runtime_static_dir = os.path.abspath(STATIC_DIR)

if repo_static_dir != runtime_static_dir and os.path.exists(repo_static_dir):
    logger.info(f"Syncing pre-packaged assets from {repo_static_dir} to runtime {runtime_static_dir}...")
    for root, dirs, files in os.walk(repo_static_dir):
        rel_path = os.path.relpath(root, repo_static_dir)
        dest_dir = os.path.join(runtime_static_dir, rel_path)
        os.makedirs(dest_dir, exist_ok=True)
        for file in files:
            src_file = os.path.join(root, file)
            dest_file = os.path.join(dest_dir, file)
            if not os.path.exists(dest_file):
                logger.info(f"Copying {src_file} -> {dest_file}")
                shutil.copy2(src_file, dest_file)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Serve Frontend static assets directly from FastAPI
@app.get("/")
def serve_frontend_root():
    for path in ["index.html", "../index.html"]:
        if os.path.exists(path):
            return FileResponse(path)
    return {"message": "ViralReel.AI API Server is running. Frontend index.html not found."}

@app.get("/style.css")
def serve_frontend_style():
    for path in ["style.css", "../style.css"]:
        if os.path.exists(path):
            return FileResponse(path, media_type="text/css")
    raise HTTPException(status_code=404, detail="style.css not found")

@app.get("/app.js")
def serve_frontend_app():
    for path in ["app.js", "../app.js"]:
        if os.path.exists(path):
            return FileResponse(path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")

@app.get("/slides")
def serve_workshop_slides():
    for path in ["slides.html", "../slides.html"]:
        if os.path.exists(path):
            return FileResponse(path)
    raise HTTPException(status_code=404, detail="slides.html not found")

# Request/Response models
class StoryboardRequest(BaseModel):
    text: str
    tone: Optional[str] = "curious"

class StoryboardScene(BaseModel):
    scene_id: int
    text: str
    search_query: str
    visual_prompt: str

class RenderRequest(BaseModel):
    storyboard: List[StoryboardScene]
    voice: Optional[str] = "en_us_002"
    style: Optional[str] = "tech"

@app.post("/api/generate-storyboard")
def api_generate_storyboard(request: StoryboardRequest):
    """
    API endpoint: Invokes LLM parser to break raw script into visual scenes.
    """
    logger.info(f"Received storyboard request. Length: {len(request.text)} chars. Tone: {request.tone}")
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Script text cannot be empty.")
        
    try:
        storyboard = generate_storyboard(request.text, request.tone)
        return storyboard
    except Exception as e:
        logger.error(f"Error in generate-storyboard API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/render")
def api_render(request: RenderRequest):
    """
    API endpoint: Executes the 100% free-tier rendering pipeline.
    """
    if not request.storyboard:
        raise HTTPException(status_code=400, detail="Storyboard list cannot be empty.")

    job_id = str(uuid.uuid4())[:8]
    job_dir = os.path.join(CACHE_DIR, f"job_{job_id}")
    os.makedirs(job_dir, exist_ok=True)

    logger.info(f"Starting render job: {job_id} ({len(request.storyboard)} scenes)")

    scene_video_clips = []
    scene_audio_clips = []
    updated_storyboard_data = []

    try:
        # Step 1: Process each scene individually (TTS -> whisper align -> B-roll download -> clip render)
        total_time_offset = 0.0
        
        for idx, scene in enumerate(request.storyboard):
            scene_num = scene.scene_id
            logger.info(f"Processing Scene {scene_num}/{len(request.storyboard)}...")

            # A. Synthesize speech for this sentence
            scene_audio_path = os.path.join(job_dir, f"audio_scene_{scene_num}.mp3")
            synthesis_success = synthesize_text(scene.text, request.voice, scene_audio_path)
            
            if not synthesis_success:
                raise HTTPException(status_code=500, detail=f"Failed to synthesize audio for Scene {scene_num}")

            # B. Get word-level timestamps (alignment)
            words_timestamps = align_words(scene_audio_path, scene.text, start_offset=total_time_offset)
            
            # C. Determine scene duration
            scene_duration = 0.0
            if words_timestamps:
                scene_duration = words_timestamps[-1]["end"] - total_time_offset
            if scene_duration <= 0.0:
                scene_duration = 3.0 # Fallback
            
            logger.info(f"Scene {scene_num} synthesized. Duration: {scene_duration:.2f}s")

            # D. Query Pexels and download visual asset
            broll_source_path = get_pexels_video(scene.search_query, cache_dir=CACHE_DIR)

            # E. Scale, crop and trim raw B-roll to scene duration
            scene_video_path = os.path.join(job_dir, f"video_scene_{scene_num}.mp4")
            render_success = render_scene_clip(broll_source_path, scene_duration, scene_video_path)
            
            if not render_success:
                raise HTTPException(status_code=500, detail=f"FFmpeg trim/crop failed for Scene {scene_num}")

            scene_video_clips.append(scene_video_path)
            scene_audio_clips.append(scene_audio_path)

            # Store updated scene details with timing references
            updated_storyboard_data.append({
                "id": scene_num,
                "text": scene.text,
                "start": total_time_offset,
                "end": total_time_offset + scene_duration,
                "duration": scene_duration,
                "visualPrompt": scene.visual_prompt,
                "words": words_timestamps
            })

            total_time_offset += scene_duration

        # Step 2: Merge individual media fragments into master tracks
        master_audio_path = os.path.join(job_dir, "master_voiceover.mp3")
        concat_audio_success = concatenate_audios(scene_audio_clips, master_audio_path)
        if not concat_audio_success:
             raise HTTPException(status_code=500, detail="Failed to concatenate scene audio tracks.")

        master_video_path = os.path.join(job_dir, "master_video.mp4")
        concat_video_success = concatenate_videos(scene_video_clips, master_video_path)
        if not concat_video_success:
             raise HTTPException(status_code=500, detail="Failed to concatenate scene video tracks.")

        # Step 3: Compile ASS Subtitles file
        ass_path = os.path.join(job_dir, "subtitles.ass")
        compile_ass_subtitles(updated_storyboard_data, ass_path)

        # Step 4: Render final composite video with music & subtitles
        final_video_name = f"reel_{job_id}.mp4"
        final_video_path = os.path.join(OUTPUT_DIR, final_video_name)
        
        # Check if we have background lofi loop tracks in the tracks directory
        lofi_tracks = [f for f in os.listdir(LOFI_TRACKS_DIR) if f.endswith((".mp3", ".wav"))]
        selected_lofi_path = None
        if lofi_tracks:
            # Map style selection or pick first available track
            selected_lofi_path = os.path.join(LOFI_TRACKS_DIR, lofi_tracks[0])
            logger.info(f"Applying lofi background loop track: {selected_lofi_path}")

        final_render_success = render_final_video(
            master_video_path,
            master_audio_path,
            ass_path,
            final_video_path,
            lofi_music_path=selected_lofi_path
        )

        if not final_render_success:
            raise HTTPException(status_code=500, detail="FFmpeg final compositing stage failed.")

        # Return public URL to retrieve video stream
        video_url = f"/static/outputs/{final_video_name}"
        logger.info(f"Render job {job_id} successfully completed. Output: {video_url}")
        
        return {
            "status": "success",
            "videoUrl": video_url,
            "duration": total_time_offset,
            "storyboard": updated_storyboard_data
        }

    except Exception as e:
        logger.error(f"Error rendering job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
