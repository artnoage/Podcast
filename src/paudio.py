import os
import asyncio
import io
from datetime import datetime
from openai import OpenAI
import logging
from pydub import AudioSegment
try:
    from src.utils.utils import create_podcast, parse_dialogue, save_podcast_state, PROJECT_ROOT
except ImportError:
    from utils.utils import create_podcast, parse_dialogue, save_podcast_state, PROJECT_ROOT


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_tts(text, voice="onyx"):
    """
    Generates text-to-speech audio using OpenAI's API.

    Args:
    text (str): The text to convert to speech.
    voice (str, optional): The voice to use for TTS. Defaults to "onyx".

    Returns:
    bytes: The generated audio content.
    """
    try:
        client = OpenAI()
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )
        logger.info(f"TTS audio generated successfully using voice: {voice}")
        return response.content
    except Exception as e:
        logger.error(f"Error in OpenAI TTS API call: {str(e)}", exc_info=True)
        raise

# Create a thread-local storage for OpenAI clients
import threading
thread_local = threading.local()

def get_openai_client():
    if not hasattr(thread_local, "openai_client"):
        thread_local.openai_client = OpenAI()
    return thread_local.openai_client

async def generate_tts_async(text, voice="onyx"):
    """
    Asynchronously generates text-to-speech audio using OpenAI's API.

    Args:
    text (str): The text to convert to speech.
    voice (str, optional): The voice to use for TTS. Defaults to "onyx".

    Returns:
    bytes: The generated audio content.
    """
    try:
        client = get_openai_client()
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
        )
        logger.info(f"TTS audio generated asynchronously using voice: {voice}")
        return response.content
    except Exception as e:
        logger.error(f"Error in asynchronous OpenAI TTS API call: {str(e)}", exc_info=True)
        raise

async def create_podcast_audio(pdf_content, timestamp=None, summarizer_model="gpt-4o-mini", scriptwriter_model="gpt-4o-mini", enhancer_model="gpt-4o-mini", provider="OpenAI", api_key=None):
    """
    Creates an audio podcast from the given PDF content using the provided timestamp and models.
    """
    print(f"Using prompts from timestamp: {timestamp or 'default'}")
    print(f"Using models - Summarizer: {summarizer_model}, Scriptwriter: {scriptwriter_model}, Enhancer: {enhancer_model}")
    
    # Create the podcast
    podcast_state, message = await create_podcast(
        pdf_content, 
        timestamp=timestamp, 
        summarizer_model=summarizer_model, 
        scriptwriter_model=scriptwriter_model, 
        enhancer_model=enhancer_model, 
        provider=provider, 
        api_key=api_key
    )
    
    if podcast_state is None or message != "Success":
        raise ValueError(f"Failed to create podcast state: {message}")
    
    # Generate a new timestamp for saving the podcast state
    new_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_podcast_state(podcast_state, new_timestamp)

    enhanced_script = podcast_state["enhanced_script"].content
    
    if not enhanced_script:
        raise ValueError("No enhanced script found in the podcast state")

    # Parse the dialogue
    dialogue_pieces = parse_dialogue(enhanced_script)

    # Generate audio for each dialogue piece concurrently
    async def generate_audio_segment(piece):
        speaker, text = piece.split(': ', 1)
        voice = "onyx" if speaker == "Host" else "nova"
        audio_content = await generate_tts_async(text, voice=voice)
        return audio_content, speaker

    audio_segments = await asyncio.gather(*[generate_audio_segment(piece) for piece in dialogue_pieces])

    # Combine audio segments
    combined_audio = AudioSegment.empty()
    for audio_content, speaker in audio_segments:
        segment = AudioSegment.from_mp3(io.BytesIO(audio_content))
        combined_audio += segment

    # Export the final podcast audio to bytes
    buffer = io.BytesIO()
    combined_audio.export(buffer, format="mp3")
    audio_bytes = buffer.getvalue()

    # Save the dialogue
    dialogue_text = "\n".join(dialogue_pieces)

    return audio_bytes, dialogue_text, new_timestamp

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create a podcast audio from a PDF file.")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--timestamp", help="Timestamp to use for prompts (format: YYYYMMDD_HHMMSS)")
    args = parser.parse_args()
    
    asyncio.run(create_podcast_audio(args.pdf_path, args.timestamp))
