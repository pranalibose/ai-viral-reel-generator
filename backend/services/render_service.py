import os
import subprocess
import logging
from typing import List, Dict, Any, Optional

# Setup logger
logger = logging.getLogger("viral_reel_backend.render_service")

def format_ass_timestamp(seconds: float) -> str:
    """
    Converts float seconds into ASS timestamp format: H:MM:SS.cs
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds % 1) * 100))
    if cs == 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def compile_ass_subtitles(storyboard: List[Dict[str, Any]], output_path: str):
    """
    Compiles word timestamps into an ASS subtitle script with modern typography
    and active word highlighting.
    """
    ass_header = """[Script Info]
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Plus Jakarta Sans,72,&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,5,30,30,860,1
"""
    # Alignment 5 = Middle-Center. Outline 6 = thick black outline. Fontsize 72 = clear readability on mobile.
    
    events = []
    
    for scene in storyboard:
        words = scene.get("words", [])
        if not words:
            continue
            
        # Group words to render on screen in segments
        # To avoid rapid flashing, we show a full line of words on screen,
        # but output a sequence of dialogue records that highlights the active word.
        scene_words = [w["word"] for w in words]
        
        for w_idx, active_word_obj in enumerate(words):
            start_str = format_ass_timestamp(active_word_obj["start"])
            end_str = format_ass_timestamp(active_word_obj["end"])
            
            # Reconstruct the line, applying yellow highlight to the active word index
            styled_words = []
            for idx, word_str in enumerate(scene_words):
                if idx == w_idx:
                    # Highlight color (Yellow): \c&H00FFFF&
                    styled_words.append(f"\\c&H00FFFF&{word_str}")
                else:
                    # Standard color (White): \c&HFFFFFF&
                    # Put \rDefault to reset style just in case
                    styled_words.append(f"\\c&HFFFFFF&{word_str}")
                    
            text_line = " ".join(styled_words)
            events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0000,0000,0000,,{text_line}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        f.write("\n[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        for event in events:
            f.write(event + "\n")
            
    logger.info(f"Successfully compiled ASS subtitles at {output_path}")

def render_scene_clip(input_video_path: str, duration: float, output_clip_path: str) -> bool:
    """
    Trims, scales, and center-crops a stock B-roll video to 1080x1920 vertical format.
    """
    os.makedirs(os.path.dirname(output_clip_path), exist_ok=True)
    
    # FFmpeg crop-to-fit filter complex
    # Scales the video so it completely covers the 1080x1920 box without stretching, then crops to center.
    scale_crop_filter = (
        "scale=w='max(1080,ih*1080/1920)':h='max(1920,iw*1920/1080)',"
        "crop=1080:1920:center=1"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", "0",
        "-t", str(duration),
        "-i", input_video_path,
        "-vf", scale_crop_filter,
        "-an", # Remove audio track from B-roll
        "-c:v", "libx264",
        "-preset", "superfast",
        "-crf", "22",
        output_clip_path
    ]
    
    try:
        logger.info(f"Rendering scene video clip: {output_clip_path} (Duration: {duration}s)")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg scene render failed: {e.stderr}")
        return False

def concatenate_videos(video_paths: List[str], output_path: str) -> bool:
    """
    Concatenates multiple visual MP4 files into a single video file.
    """
    # Write files list for FFmpeg concat demuxer
    list_path = output_path + ".list.txt"
    with open(list_path, "w") as f:
        for p in video_paths:
            # Paths must be formatted correctly for FFmpeg file list
            abs_p = os.path.abspath(p)
            f.write(f"file '{abs_p}'\n")
            
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_path,
        "-c", "copy", # Fast copy since dimensions and codecs are pre-aligned
        output_path
    ]
    
    try:
        logger.info(f"Concatenating {len(video_paths)} scene videos into {output_path}...")
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        if os.path.exists(list_path):
            os.remove(list_path)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg video concatenation failed: {e.stderr}")
        if os.path.exists(list_path):
            os.remove(list_path)
        return False

def concatenate_audios(audio_paths: List[str], output_path: str) -> bool:
    """
    Concatenates multiple audio voiceover fragments into a single audio track.
    """
    # We construct a filter complex to safely concatenate audio streams without codec issues
    inputs = []
    filter_complex = ""
    for idx, path in enumerate(audio_paths):
        inputs.extend(["-i", path])
        filter_complex += f"[{idx}:a]"
        
    filter_complex += f"concat=n={len(audio_paths)}:v=0:a=1[outa]"
    
    cmd = [
        "ffmpeg", "-y"
    ] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[outa]",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        output_path
    ]
    
    try:
        logger.info(f"Concatenating {len(audio_paths)} audio voice fragments into {output_path}...")
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg audio concatenation failed: {e.stderr}")
        return False

def render_final_video(
    combined_video_path: str,
    combined_audio_path: str,
    ass_subtitles_path: str,
    output_video_path: str,
    lofi_music_path: Optional[str] = None
) -> bool:
    """
    Assembles video, voiceover, lofi background music (with sidechain audio ducking),
    and overlays ASS typography.
    """
    inputs = [
        "-i", combined_video_path,
        "-i", combined_audio_path
    ]
    
    # Compile the filter complex
    if lofi_music_path and os.path.exists(lofi_music_path):
        # We loop the music and apply sidechain compress sidechain filter
        inputs.extend(["-stream_loop", "-1", "-i", lofi_music_path])
        filter_complex = (
            "[1:a]volume=1.0[speech];"
            "[2:a]volume=0.08[music];"
            "[speech][music]sidechaincompress=threshold=0.15:ratio=12:level_in=1.0:level_out=1.0[outa];"
            f"[0:v]ass={os.path.abspath(ass_subtitles_path)}[outv]"
        )
        audio_map = "[outa]"
    else:
        # Standard narration without lofi background
        filter_complex = f"[0:v]ass={os.path.abspath(ass_subtitles_path)}[outv]"
        audio_map = "1:a"
        
    cmd = [
        "ffmpeg", "-y"
    ] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", audio_map,
        "-shortest", # End when video finishes
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "21",
        "-c:a", "aac",
        "-b:a", "192k",
        output_video_path
    ]
    
    try:
        logger.info(f"Rendering final compiled video MP4: {output_video_path}")
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg final video compilation failed: {e.stderr}")
        return False
