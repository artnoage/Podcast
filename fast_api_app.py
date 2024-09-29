import logging
import os
import random
import json
import asyncio
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI
from pydub import AudioSegment

from src.utils.utils import create_podcast, save_podcast_state, add_feedback_to_state, get_all_timestamps
from src.utils.textGDwithWeightClipping import optimize_prompt
from src.paudio import generate_tts, parse_dialogue

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
client = OpenAI()



# Create the 'static' directory if it doesn't exist
os.makedirs("static", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow the React development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add CORS headers to all responses
@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:3000"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# Add a new route for API key validation
@app.options("/validate_api_key")
async def options_validate_api_key():
    return {}  # This is needed for CORS preflight requests

class ApiKeyRequest(BaseModel):
    api_key: str

@app.post("/validate_api_key")
async def validate_api_key(request: ApiKeyRequest):
    try:
        client.api_key = request.api_key
        # Make a simple API call to test the key
        client.models.list()
        return {"message": "API key is valid"}
    except Exception as e:
        if "Invalid API key" in str(e):
            logger.warning("Invalid API key provided")
            raise HTTPException(status_code=401, detail="Invalid API key")
        else:
            logger.error("Error validating API key", exc_info=True)
            raise HTTPException(status_code=500, detail="Error validating API key")

class FeedbackRequest(BaseModel):
    podcast_state: dict
    feedback: str
    timestamp: str

class VoteRequest(BaseModel):
    timestamp: str

VOTES_FILE = "votes.json"

def load_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_votes(votes):
    with open(VOTES_FILE, 'w') as f:
        json.dump(votes, f)

class CreatePodcastsRequest(BaseModel):
    api_key: Optional[str] = None
    pdf_content: bytes

@app.post("/create_podcasts")
async def create_podcasts_endpoint(request: CreatePodcastsRequest):
    logger.info(f"Creating podcasts. PDF content available: {len(request.pdf_content) > 0}")
    if not request.pdf_content:
        logger.error("No PDF content provided")
        raise HTTPException(status_code=400, detail="No PDF content provided")

    try:
        # Log the API key status
        api_key_status = "provided" if request.api_key else "not provided"
        logger.info(f"Creating podcasts with API key status: {api_key_status}")

        # Use the api_key directly from the request
        api_key = request.api_key

        # Get the last timestamp and a random timestamp
        logger.info("Getting timestamps")
        all_timestamps = get_all_timestamps()
        logger.info(f"All timestamps: {all_timestamps}")

        if not all_timestamps:
            logger.info("No timestamps available, creating podcast without timestamp")
            # If no timestamps are available, create a podcast without a timestamp
            podcast_state, message = await create_podcast(request.pdf_content, timestamp=None, summarizer_model="gpt-4o-mini", scriptwriter_model="gpt-4o-mini", enhancer_model="gpt-4o-mini", provider="OpenAI", api_key=api_key)
            if podcast_state is None:
                logger.error(f"Failed to create podcast: {message}")
                raise HTTPException(status_code=500, detail=f"Failed to create podcast: {message}")
            podcasts = [podcast_state]
        else:
            logger.info("Timestamps available, creating podcasts with timestamps")
            last_timestamp = max(all_timestamps)
            random_timestamp = random.choice([t for t in all_timestamps if t != last_timestamp])
            
            async def create_podcast_task(timestamp, podcast_type):
                logger.info(f"Creating podcast for timestamp {timestamp}")
                podcast_state, message = await create_podcast(request.pdf_content, timestamp=timestamp, summarizer_model="gpt-4o-mini", scriptwriter_model="gpt-4o-mini", enhancer_model="gpt-4o-mini", provider="OpenAI", api_key=api_key)
                
                if podcast_state is None:
                    logger.error(f"Failed to create podcast for timestamp {timestamp}: {message}")
                    raise HTTPException(status_code=500, detail=f"Failed to create podcast for timestamp {timestamp}: {message}")
                
                logger.info(f"Saving podcast state for timestamp {timestamp}")
                save_podcast_state(podcast_state, timestamp)
                
                logger.info(f"Generating audio for timestamp {timestamp}")
                # Generate audio
                enhanced_script = podcast_state["enhanced_script"].content
                dialogue_pieces = parse_dialogue(enhanced_script)
                
                combined_audio = AudioSegment.empty()
                for piece in dialogue_pieces:
                    speaker, text = piece.split(': ', 1)
                    voice = "onyx" if speaker == "Host" else "nova"
                    audio_content = generate_tts(text, voice=voice)
                    
                    temp_file = f"temp_{speaker.lower()}.mp3"
                    with open(temp_file, "wb") as f:
                        f.write(audio_content)
                    
                    segment = AudioSegment.from_mp3(temp_file)
                    combined_audio += segment
                    
                    os.remove(temp_file)
                
                audio_filename = f"podcast_{timestamp}.mp3"
                audio_path = os.path.join("static", audio_filename)
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)
                combined_audio.export(audio_path, format="mp3")
                
                logger.info(f"Podcast created successfully for timestamp {timestamp}")
                # Add audio_url, timestamp, and type to the podcast_state
                return {
                    "timestamp": timestamp,
                    "type": podcast_type,
                    "main_text": podcast_state["main_text"].content,
                    "key_points": podcast_state["key_points"].content,
                    "script_essence": podcast_state["script_essence"].content,
                    "enhanced_script": podcast_state["enhanced_script"].content,
                    "audio_url": f"http://localhost:8000/static/{audio_filename}"
                }
            
            logger.info("Creating both podcasts concurrently")
            # Create both podcasts concurrently
            podcasts = await asyncio.gather(
                create_podcast_task(random_timestamp, "random"),
                create_podcast_task(last_timestamp, "last")
            )
        
        logger.info("Podcasts created successfully")
        return {"podcasts": podcasts}
    except Exception as e:
        logger.error(f"Error in create_podcasts_endpoint: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        error_detail = str(e)
        if len(error_detail) > 100:
            error_detail = error_detail[:100] + "... (truncated)"
        raise HTTPException(status_code=422, detail=f"An error occurred: {error_detail}")

@app.post("/process_feedback")
async def process_feedback(request: FeedbackRequest):
    feedback = request.feedback
    timestamp = request.timestamp
    podcast_state = request.podcast_state

    # Add feedback to the podcast state
    add_feedback_to_state(timestamp, feedback)

    # Generate a new timestamp
    new_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Optimize prompts
    optimize_prompt("summarizer", timestamp, new_timestamp, "gpt-4o-mini", "gpt-4o")
    optimize_prompt("scriptwriter", timestamp, new_timestamp, "gpt-4o-mini", "gpt-4o")
    optimize_prompt("enhancer", timestamp, new_timestamp, "gpt-4o-mini", "gpt-4o")

    return {"message": "Feedback processed and prompts optimized"}

@app.post("/vote")
async def vote(request: VoteRequest):
    votes = load_votes()
    timestamp = request.timestamp
    if timestamp in votes:
        votes[timestamp] += 1
    else:
        votes[timestamp] = 1
    save_votes(votes)
    return {"message": "Vote recorded successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
