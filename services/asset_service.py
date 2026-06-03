import os
import hashlib
import logging
import requests

# Setup logger
logger = logging.getLogger("viral_reel_backend.asset_service")

# Preset high-quality fallback video loops (free Mixkit stock clips)
FALLBACK_CLIPS = {
    "tech": "https://assets.mixkit.co/videos/preview/mixkit-hand-typing-on-a-keyboard-in-a-dark-room-42022-large.mp4",
    "bold": "https://assets.mixkit.co/videos/preview/mixkit-digital-animation-of-stock-market-charts-31908-large.mp4",
    "minimal": "https://assets.mixkit.co/videos/preview/mixkit-modern-office-with-creative-workspace-40294-large.mp4",
    "energetic": "https://assets.mixkit.co/videos/preview/mixkit-runner-training-on-an-outdoor-athletic-track-41551-large.mp4"
}

def get_pexels_video(query: str, cache_dir: str = "./cache") -> str:
    """
    Searches Pexels for a portrait B-roll video, downloads it, and returns the cached file path.
    """
    os.makedirs(cache_dir, exist_ok=True)
    
    # Hash query to create distinct cached filename
    query_hash = hashlib.md5(query.lower().encode('utf-8')).hexdigest()
    cache_path = os.path.join(cache_dir, f"{query_hash}.mp4")
    
    # Check cache hit
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
        logger.info(f"Cache hit for video query: '{query}' at {cache_path}")
        return cache_path

    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key or api_key == "your_pexels_api_key_here":
        logger.warning("PEXELS_API_KEY is missing. Using preset fallback video loops.")
        return download_fallback_asset(query, cache_path)

    headers = {"Authorization": api_key}
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=portrait"
    
    try:
        logger.info(f"Querying Pexels API for: '{query}'")
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            data = response.json()
            videos = data.get("videos", [])
            if videos:
                video = videos[0]
                video_files = video.get("video_files", [])
                
                # Try to find a vertical resolution format file
                portrait_files = [f for f in video_files if f.get("width", 0) < f.get("height", 0)]
                selected_file = portrait_files[0] if portrait_files else (video_files[0] if video_files else None)
                
                if selected_file:
                    video_url = selected_file.get("link")
                    logger.info(f"Found vertical B-roll url: {video_url}. Downloading...")
                    download_file(video_url, cache_path)
                    return cache_path
            
            logger.warning(f"No video matches found for query: '{query}'. Fallback to preset loops.")
        else:
            logger.error(f"Pexels returned status {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Pexels fetch connection failed: {e}")

    # Fallback to local default clips if API query returns nothing or fails
    return download_fallback_asset(query, cache_path)

def download_fallback_asset(query: str, target_path: str) -> str:
    """
    Selects one of the Mixkit loop templates depending on keywords.
    """
    q_lower = query.lower()
    selected_url = FALLBACK_CLIPS["minimal"]
    
    if any(k in q_lower for k in ["code", "tech", "program", "developer", "keyboard", "coding"]):
        selected_url = FALLBACK_CLIPS["tech"]
    elif any(k in q_lower for k in ["chart", "stock", "money", "finance", "invest", "save"]):
        selected_url = FALLBACK_CLIPS["bold"]
    elif any(k in q_lower for k in ["run", "sport", "train", "fast", "athlete"]):
        selected_url = FALLBACK_CLIPS["energetic"]

    logger.info(f"Downloading preset video asset loop: {selected_url} -> {target_path}")
    download_file(selected_url, target_path)
    return target_path

def download_file(url: str, dest_path: str):
    """
    Downloads media file from URL to disk.
    """
    try:
        response = requests.get(url, stream=True, timeout=25)
        response.raise_for_status()
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=16384):
                if chunk:
                    f.write(chunk)
        logger.info(f"Successfully downloaded file to: {dest_path}")
    except Exception as e:
        logger.error(f"Download failed for {url}: {e}")
        # Clear empty files on failure
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise e
