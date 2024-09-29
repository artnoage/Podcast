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
    old_timestamp: str
    new_timestamp: str

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

from fastapi import UploadFile, File

@app.post("/create_podcasts")
async def create_podcasts_endpoint(api_key: Optional[str] = None, pdf_content: UploadFile = File(...)):
    logger.info(f"Creating podcasts. PDF file name: {pdf_content.filename}")
    if not pdf_content:
        logger.error("No PDF file provided")
        raise HTTPException(status_code=400, detail="No PDF file provided")

    try:
        # Read the content of the uploaded file
        pdf_bytes = await pdf_content.read()

        # Log the API key status
        api_key_status = "provided" if api_key else "not provided"
        logger.info(f"Creating podcasts with API key status: {api_key_status}")

        # Get the last timestamp and a random timestamp
        logger.info("Getting timestamps")
        all_timestamps = get_all_timestamps()
        logger.info(f"All timestamps: {all_timestamps}")

        if not all_timestamps:
            logger.info("No timestamps available, creating podcast without timestamp")
            # If no timestamps are available, create a podcast without a timestamp
            podcast_state, message = await create_podcast(pdf_bytes, timestamp=None, summarizer_model="gpt-4o-mini", scriptwriter_model="gpt-4o-mini", enhancer_model="gpt-4o-mini", provider="OpenAI", api_key=api_key)
            if podcast_state is None:
                logger.error(f"Failed to create podcast: {message}")
                raise HTTPException(status_code=500, detail=f"Failed to create podcast: {message}")
            podcasts = [podcast_state]
        else:
            logger.info("Timestamps available, creating podcasts with timestamps")
            last_timestamp = max(all_timestamps)
            random_timestamp = random.choice([t for t in all_timestamps if t != last_timestamp])
            
            async def create_podcast_task(timestamp, podcast_type):
                try:
                    logger.info(f"Creating podcast for timestamp {timestamp}")
                    podcast_state, message = await create_podcast(pdf_bytes, timestamp=timestamp, summarizer_model="gpt-4o-mini", scriptwriter_model="gpt-4o-mini", enhancer_model="gpt-4o-mini", provider="OpenAI", api_key=api_key)
                    
                    if podcast_state is None:
                        logger.error(f"Failed to create podcast for timestamp {timestamp}: {message}")
                        raise HTTPException(status_code=500, detail=f"Failed to create podcast for timestamp {timestamp}: {message}")
                    
                    logger.info(f"Generating audio for timestamp {timestamp}")
                    # Generate audio
                    enhanced_script = podcast_state["enhanced_script"].content
                    dialogue_pieces = parse_dialogue(enhanced_script)
                    
                    audio_segments = []
                    for piece in dialogue_pieces:
                        speaker, text = piece.split(': ', 1)
                        voice = "onyx" if speaker == "Host" else "nova"
                        audio_content = generate_tts(text, voice=voice)
                        audio_segments.append(audio_content)
                    
                    logger.info(f"Podcast created successfully for timestamp {timestamp}")
                    
                    # For the last podcast, save the state with a new timestamp
                    new_timestamp = None
                    if podcast_type == "last":
                        new_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        logger.info(f"Saving podcast state for new timestamp {new_timestamp}")
                        save_podcast_state(podcast_state, new_timestamp)
                    
                    # Add timestamp and type to the podcast_state, along with audio segments
                    return {
                        "timestamp": timestamp,
                        "new_timestamp": new_timestamp,
                        "type": podcast_type,
                        "audio_segments": audio_segments
                    }
                except Exception as e:
                    logger.error(f"Error in create_podcast_task for timestamp {timestamp}: {str(e)}", exc_info=True)
                    raise
            
            logger.info("Creating both podcasts concurrently")
            # Create both podcasts concurrently
            try:
                podcasts = await asyncio.gather(
                    create_podcast_task(random_timestamp, "random"),
                    create_podcast_task(last_timestamp, "last")
                )
            except Exception as e:
                logger.error(f"Error in asyncio.gather: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to create podcasts: {str(e)}")
        
        logger.info("Podcasts created successfully")
        return {"podcasts": podcasts}
    except Exception as e:
        logger.error(f"Error in create_podcasts_endpoint: {str(e)}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        error_detail = str(e)
        if len(error_detail) > 100:
            error_detail = error_detail[:100] + "... (truncated)"
        raise HTTPException(status_code=500, detail=f"An error occurred: {error_detail}")

@app.post("/process_feedback")
async def process_feedback(request: FeedbackRequest):
    feedback = request.feedback
    old_timestamp = request.old_timestamp
    new_timestamp = request.new_timestamp
    podcast_state = request.podcast_state

    # Add feedback to the podcast state
    add_feedback_to_state(old_timestamp, feedback)

    # Optimize prompts
    optimize_prompt("summarizer", old_timestamp, new_timestamp, "gpt-4o-mini", "gpt-4o")
    optimize_prompt("scriptwriter", old_timestamp, new_timestamp, "gpt-4o-mini", "gpt-4o")
    optimize_prompt("enhancer", old_timestamp, new_timestamp, "gpt-4o-mini", "gpt-4o")

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
