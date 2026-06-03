import os
import json
import logging
from typing import List, Dict, Any
import google.generativeai as genai
from pydantic import BaseModel, Field

# Setup logger
logger = logging.getLogger("viral_reel_backend.llm_service")

class SceneItem(BaseModel):
    scene_id: int = Field(description="The 1-based sequential index of the scene")
    text: str = Field(description="The exact spoken script text for this scene")
    search_query: str = Field(description="A 2-4 word visual query optimized for stock video search engines like Pexels (e.g. 'typing keyboard close up', 'stock chart neon')")
    visual_prompt: str = Field(description="Detailed visual B-roll description describing the scene setting")

class StoryboardResponse(BaseModel):
    scenes: List[SceneItem]

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        logger.warning("GEMINI_API_KEY is not configured. Falling back to mock generator.")
        return None
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        logger.error(f"Error configuring Gemini client: {e}")
        return None

def generate_storyboard(raw_text: str, tone: str = "curious") -> Dict[str, Any]:
    """
    Parses raw_text into structured storyboard scenes using Gemini Free Tier.
    If no API key is present, falls back to a deterministic rule-based generator.
    """
    model = get_gemini_client()
    
    if not model:
        return generate_mock_storyboard(raw_text, tone)

    prompt = f"""
    You are an expert short-form video editor and scriptwriter. 
    Analyze the following raw text and segment it into a sequential list of script scenes.
    Each scene segment should be between 3 and 7 seconds of spoken text (roughly 8 to 18 words).
    
    Apply a **{tone}** tone to any script refinements if necessary, while preserving the core message.
    
    For each scene:
    1. Provide the exact spoken `text`.
    2. Provide a 2-4 word `search_query` for Pexels stock video search (e.g., 'man programming laptop', 'aesthetic workspace sunset'). Ensure the terms are generic enough to find search matches easily.
    3. Provide a descriptive `visual_prompt` for this scene.

    Input Raw Text:
    ---
    {raw_text}
    ---
    """

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=StoryboardResponse,
                temperature=0.2
            )
        )
        data = json.loads(response.text)
        return data
    except Exception as e:
        logger.error(f"Gemini generation failed: {e}. Falling back to mock generator.")
        return generate_mock_storyboard(raw_text, tone)

def generate_mock_storyboard(raw_text: str, tone: str) -> Dict[str, Any]:
    """
    Rule-based sentence-splitting fallback if Gemini API is unavailable.
    """
    import re
    # Split text into sentences
    sentences = re.split(r'(?<=[.!?])\s+', raw_text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        sentences = [raw_text.strip()]

    scenes = []
    for idx, sentence in enumerate(sentences):
        # Generate some simple mock visual queries based on keywords
        words = sentence.lower()
        query = "office aesthetic lofi"
        if "code" in words or "program" in words or "html" in words or "css" in words:
            query = "typing keyboard laptop"
        elif "money" in words or "wealth" in words or "rich" in words or "invest" in words or "save" in words:
            query = "stock market graph"
        elif "run" in words or "sport" in words or "fast" in words:
            query = "runner training track"

        scenes.append({
            "scene_id": idx + 1,
            "text": sentence,
            "search_query": query,
            "visual_prompt": f"Close up shot matching query: {query}. Modern color grading, lofi aesthetic."
        })
        
    return {"scenes": scenes}
