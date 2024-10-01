import logging
import os
import random
import json
import asyncio
import base64
from datetime import datetime
from typing import Optional, List, Dict
from uuid import uuid4

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import base64
from pydantic import BaseModel
from openai import OpenAI

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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory task storage (replace with a proper database in production)
tasks: Dict[str, Dict] = {}

class ApiKeyRequest(BaseModel):
    api_key: str

class FeedbackRequest(BaseModel):
    feedback: str
    old_timestamp: Optional[str] = None
    new_timestamp: str

class VoteRequest(BaseModel):
    timestamp: Optional[str] = None

class ExperimentIdeaRequest(BaseModel):
    idea: str

VOTES_FILE = "votes.json"
EXPERIMENT_IDEAS_FILE = "experiment_ideas.md"

def load_votes():
    if os.path.exists(VOTES_FILE):
        with open(VOTES_FILE, 'r') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
    return {}

def save_votes(votes):
    with open(VOTES_FILE, 'w') as f:
        json.dump(votes, f)

@app.get("/health")
async def health_check():
    return {"status": "OK"}

@app.post("/validate_api_key")
async def validate_api_key(request: ApiKeyRequest):
    try:
        client.api_key = request.api_key
        client.models.list()
        return {"message": "API key is valid"}
    except Exception as e:
        if "Invalid API key" in str(e):
            logger.warning("Invalid API key provided")
            raise HTTPException(status_code=401, detail="Invalid API key")
        else:
            logger.error("Error validating API key", exc_info=True)
            raise HTTPException(status_code=500, detail="Error validating API key")

@app.post("/create_podcasts")
async def create_podcasts_endpoint(
    background_tasks: BackgroundTasks,
    api_key: Optional[str] = Form(None),
    pdf_content: UploadFile = File(...),
    summarizer_model: str = Form("gpt-4o-mini"),
    scriptwriter_model: str = Form("gpt-4o-mini"),
    enhancer_model: str = Form("gpt-4o-mini"),
    provider: str = Form("OpenAI")
):
    logger.info(f"Starting podcast creation. PDF file name: {pdf_content.filename}")
    if not pdf_content:
        logger.error("No PDF file provided")
        raise HTTPException(status_code=400, detail="No PDF file provided")

    try:
        pdf_bytes = await pdf_content.read()
        logger.info(f"PDF content read successfully. Size: {len(pdf_bytes)} bytes")

        task_id = str(uuid4())
        tasks[task_id] = {"status": "processing", "result": None}

        background_tasks.add_task(
            process_podcast_creation, 
            task_id, 
            pdf_bytes, 
            api_key, 
            summarizer_model, 
            scriptwriter_model, 
            enhancer_model, 
            provider
        )

        return {"task_id": task_id}
    except Exception as e:
        logger.error(f"Error in create_podcasts_endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/podcast_status/{task_id}")
async def get_podcast_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/get_podcast_audio/{task_id}")
async def get_podcast_audio(task_id: str):
    task = tasks.get(task_id)
    if not task or task["status"] != "completed":
        raise HTTPException(status_code=404, detail="Audio not found or task not completed")
    
    # Assuming the audio data is stored in the task result
    podcasts = task["result"]["podcasts"]
    
    # Combine audio data from both podcasts
    audio_data = b''.join([base64.b64decode(podcast["audio"]) for podcast in podcasts])
    
    return Response(content=audio_data, media_type="audio/mpeg")

async def process_podcast_creation(
    task_id: str, 
    pdf_bytes: bytes, 
    api_key: Optional[str], 
    summarizer_model: str,
    scriptwriter_model: str,
    enhancer_model: str,
    provider: str
):
    try:
        logger.info(f"Processing podcast creation for task {task_id}")
        api_key_status = "provided" if api_key else "not provided"
        logger.info(f"Creating podcasts with API key status: {api_key_status}")
        logger.info(f"Using models - Summarizer: {summarizer_model}, Scriptwriter: {scriptwriter_model}, Enhancer: {enhancer_model}")

        all_timestamps = get_all_timestamps()
        logger.info(f"All timestamps: {all_timestamps}")

        last_timestamp = max(all_timestamps) if all_timestamps else None
        other_timestamps = [t for t in all_timestamps if t != last_timestamp]
        random_timestamp = random.choice(other_timestamps) if other_timestamps else None

        async def create_podcast_subtask(timestamp, podcast_type):
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
                    "audio": base64.b64encode(podcast_audio).decode('utf-8') if podcast_audio else None,
                    "dialogue": dialogue_text
                }
            except Exception as e:
                logger.error(f"Error in create_podcast_subtask for timestamp {timestamp}: {str(e)}", exc_info=True)
                return {"error": str(e), "timestamp": timestamp, "type": podcast_type}

        logger.info("Creating both podcasts concurrently")
        podcasts = await asyncio.gather(
            create_podcast_subtask(random_timestamp, "random"),
            create_podcast_subtask(last_timestamp, "last")
        )

        # Check for errors in podcast creation
        errors = [podcast for podcast in podcasts if "error" in podcast]
        if errors:
            error_messages = "; ".join([f"{error['type']} podcast: {error['error']}" for error in errors])
            tasks[task_id] = {"status": "failed", "error": f"Failed to create podcasts: {error_messages}"}
        else:
            logger.info("Podcasts created successfully")
            tasks[task_id] = {"status": "completed", "result": {"podcasts": podcasts}}

    except Exception as e:
        logger.error(f"Error in process_podcast_creation: {str(e)}", exc_info=True)
        tasks[task_id] = {"status": "failed", "error": str(e)}

@app.post("/process_feedback")
async def process_feedback(request: FeedbackRequest):
    feedback = request.feedback
    old_timestamp = request.old_timestamp
    new_timestamp = request.new_timestamp

    logger.info(f"Received feedback: {feedback}")
    logger.info(f"Old timestamp: {old_timestamp}")
    logger.info(f"New timestamp: {new_timestamp}")

    if old_timestamp:
        add_feedback_to_state(old_timestamp, feedback)

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
