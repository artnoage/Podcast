import logging
import os
import random
import json
import asyncio
import base64
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI
from pydub import AudioSegment
import os

from src.utils.utils import add_feedback_to_state, get_all_timestamps
from src.utils.textGDwithWeightClipping import optimize_prompt
from src.paudio import create_podcast_audio

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
    allow_origins=["*"],  # Allow the React development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add CORS headers to all responses
@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
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
    feedback: str
    old_timestamp: Optional[str] = None
    new_timestamp: str

from typing import Optional

class VoteRequest(BaseModel):
    timestamp: Optional[str] = None

class ExperimentIdeaRequest(BaseModel):
    idea: str

VOTES_FILE = "votes.json"
EXPERIMENT_IDEAS_FILE = "experiment_ideas.md"

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
async def create_podcasts_endpoint(
    api_key: Optional[str] = None,
    pdf_content: UploadFile = File(...),
    summarizer_model: str = "gpt-4o-mini",
    scriptwriter_model: str = "gpt-4o-mini",
    enhancer_model: str = "gpt-4o-mini",
    provider: str = "OpenAI"
):
    logger.info(f"Creating podcasts. PDF file name: {pdf_content.filename}")
    if not pdf_content:
        logger.error("No PDF file provided")
        raise HTTPException(status_code=400, detail="No PDF file provided")

    try:
        # Read the content of the uploaded file
        pdf_bytes = await pdf_content.read()

        # Log the API key status and model information
        api_key_status = "provided" if api_key else "not provided"
        logger.info(f"Creating podcasts with API key status: {api_key_status}")
        logger.info(f"Using models - Summarizer: {summarizer_model}, Scriptwriter: {scriptwriter_model}, Enhancer: {enhancer_model}")

        # Get the last timestamp and a random timestamp
        logger.info("Getting timestamps")
        all_timestamps = get_all_timestamps()
        logger.info(f"All timestamps: {all_timestamps}")

        logger.info("Creating podcasts")
        last_timestamp = max(all_timestamps) if all_timestamps else None
        other_timestamps = [t for t in all_timestamps if t != last_timestamp]
        random_timestamp = random.choice(other_timestamps) if other_timestamps else None

        async def create_podcast_task(timestamp, podcast_type):
            try:
                logger.info(f"Creating podcast for timestamp {timestamp}")
                podcast_audio, dialogue_text, new_timestamp = await create_podcast_audio(
                    pdf_bytes, timestamp=timestamp,
                    summarizer_model=summarizer_model,
                    scriptwriter_model=scriptwriter_model,
                    enhancer_model=enhancer_model,
                    provider=provider,
                    api_key=api_key
                )

                logger.info(f"Podcast created successfully for timestamp {timestamp}")
                logger.info(f"New timestamp for saved podcast state: {new_timestamp}")

                return {
                    "timestamp": timestamp,
                    "new_timestamp": new_timestamp,
                    "type": podcast_type,
                    "audio": podcast_audio,
                    "dialogue": dialogue_text
                }
            except Exception as e:
                logger.error(f"Error in create_podcast_task for timestamp {timestamp}: {str(e)}", exc_info=True)
                raise

        logger.info("Creating both podcasts concurrently")
        try:
            podcasts = await asyncio.gather(
                create_podcast_task(random_timestamp, "random"),
                create_podcast_task(last_timestamp, "last")
            )
        except Exception as e:
            logger.error(f"Error in asyncio.gather: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to create podcasts: {str(e)}")
            
        
        logger.info("Podcasts created successfully")
        # Convert audio content to base64 for JSON serialization
        for podcast in podcasts:
            if podcast['audio']:
                podcast['audio'] = base64.b64encode(podcast['audio']).decode('utf-8')
        
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

    # Log the received values
    logger.info(f"Received feedback: {feedback}")
    logger.info(f"Old timestamp: {old_timestamp}")
    logger.info(f"New timestamp: {new_timestamp}")

    # Add feedback to the podcast state if old_timestamp is not None
    if old_timestamp:
        add_feedback_to_state(old_timestamp, feedback)

    # Optimize prompts
    try:
        optimize_prompt("summarizer", old_timestamp, new_timestamp, "gpt-4o-mini", "gpt-4o-mini")
        optimize_prompt("scriptwriter", old_timestamp, new_timestamp, "gpt-4o-mini", "gpt-4o-mini")
        optimize_prompt("enhancer", old_timestamp, new_timestamp, "gpt-4o-mini", "gpt-4o-mini")
    except Exception as e:
        logger.error(f"Error optimizing prompts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error optimizing prompts: {str(e)}")

    return {"message": "Feedback processed and prompts optimized"}

@app.post("/vote")
async def vote(request: VoteRequest):
    votes = load_votes()
    timestamp = request.timestamp if request.timestamp is not None else "original"
    if timestamp in votes:
        votes[timestamp] += 1
    else:
        votes[timestamp] = 1
    save_votes(votes)
    logger.info(f"Vote recorded for timestamp: {timestamp}")
    return {"message": "Vote recorded successfully", "timestamp": timestamp}

@app.post("/submit_experiment_idea")
async def submit_experiment_idea(request: ExperimentIdeaRequest):
    idea = request.idea
    with open(EXPERIMENT_IDEAS_FILE, "a") as f:
        f.write(f"\n\n---\n\n# New Experiment Idea\n\n{idea}\n")
    return {"message": "Experiment idea submitted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
