import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.utils.utils import create_podcast, save_podcast_state, add_feedback_to_state, get_all_timestamps
from src.utils.textGDwithWeightClipping import optimize_prompt
import os
from datetime import datetime
import random
import json
from openai import OpenAI
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
client = OpenAI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow the React development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

uploaded_pdf_content = None
VOTES_FILE = "votes.json"

def load_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_votes(votes):
    with open(VOTES_FILE, 'w') as f:
        json.dump(votes, f)

@app.post("/upload_pdf")
async def upload_pdf(file: UploadFile = File(...)):
    global uploaded_pdf_content
    try:
        content = await file.read()
        uploaded_pdf_content = content
        logger.info("PDF uploaded successfully")
        return {"message": "PDF uploaded successfully"}
    except Exception as e:
        logger.error(f"An error occurred while uploading the file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while uploading the file: {str(e)}")

from pydantic import BaseModel

class CreatePodcastsRequest(BaseModel):
    api_key: str

@app.post("/create_podcasts")
async def create_podcasts_endpoint(request: CreatePodcastsRequest):
    global uploaded_pdf_content
    logger.info(f"Creating podcasts. PDF content available: {uploaded_pdf_content is not None}")
    if uploaded_pdf_content is None:
        logger.error("No PDF uploaded")
        raise HTTPException(status_code=400, detail="No PDF uploaded")

    try:
        # Log the last 4 characters of the API key if provided
        api_key_suffix = request.api_key[-4:] if request.api_key else "None"
        logger.info(f"Creating podcasts using API key ending with ...{api_key_suffix}")

        # Get the last timestamp and a random timestamp
        all_timestamps = get_all_timestamps()
        if not all_timestamps:
            # If no timestamps are available, create a podcast without a timestamp
            podcast_state, message = await create_podcast(uploaded_pdf_content, timestamp=None, summarizer_model="gpt-4o-mini", scriptwriter_model="gpt-4o-mini", enhancer_model="gpt-4o-mini", provider="OpenAI", api_key=request.api_key if request.api_key else None)
            if podcast_state is None:
                logger.error(f"Failed to create podcast: {message}")
                raise HTTPException(status_code=500, detail=f"Failed to create podcast: {message}")
            podcasts = [podcast_state]
        else:
            last_timestamp = max(all_timestamps)
            random_timestamp = random.choice(all_timestamps)
            
            async def create_podcast_task(timestamp):
                podcast_state, message = await create_podcast(uploaded_pdf_content, timestamp=timestamp, summarizer_model="gpt-4o-mini", scriptwriter_model="gpt-4o-mini", enhancer_model="gpt-4o-mini", provider="OpenAI", api_key=request.api_key if request.api_key else None)
                
                if podcast_state is None:
                    logger.error(f"Failed to create podcast for timestamp {timestamp}: {message}")
                    raise HTTPException(status_code=500, detail=f"Failed to create podcast for timestamp {timestamp}: {message}")
                
                # Save the podcast state
                save_podcast_state(podcast_state, timestamp)
                
                # Generate audio (you'll need to implement this part)
                audio_filename = f"podcast_{timestamp}.mp3"
                audio_path = os.path.join("static", audio_filename)
                # TODO: Implement audio generation and save to audio_path
                
                # Add audio_url, timestamp, and type to the podcast_state
                return {
                    "timestamp": timestamp,
                    "type": "last" if timestamp == last_timestamp else "random",
                    "main_text": podcast_state["main_text"],
                    "key_points": podcast_state["key_points"],
                    "script_essence": podcast_state["script_essence"],
                    "enhanced_script": podcast_state["enhanced_script"],
                    "audio_url": f"/static/{audio_filename}"
                }
            
            # Create both podcasts concurrently
            podcasts = await asyncio.gather(
                create_podcast_task(last_timestamp),
                create_podcast_task(random_timestamp)
            )
        
        logger.info("Podcasts created successfully")
        return {"podcasts": podcasts}
    except Exception as e:
        logger.error(f"Error in create_podcasts_endpoint: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        error_detail = str(e)
        if len(error_detail) > 100:
            error_detail = error_detail[:100] + "... (truncated)"
        raise HTTPException(status_code=422, detail=f"An error occurred: {error_detail}")
    finally:
        uploaded_pdf_content = None
        logger.info("Cleared uploaded PDF content")

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
