import os
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
        response = await client.audio.speech.acreate(
            model="tts-1",
            voice=voice,
            input=text
        )
        logger.info(f"TTS audio generated asynchronously using voice: {voice}")
        return response.content
    except Exception as e:
        logger.error(f"Error in asynchronous OpenAI TTS API call: {str(e)}", exc_info=True)
        raise

def create_podcast_audio(pdf_path, timestamp=None):
    """
    Creates an audio podcast from the given PDF file using the provided timestamp.
    """
    print(f"Using prompts from timestamp: {timestamp or 'default'}")
    # Create the podcast
    podcast_state, message = create_podcast(pdf_path, timestamp=timestamp, summarizer_model="gpt-4o", scriptwriter_model="gpt-4o", enhancer_model="gpt-4o", provider="OpenAI", api_key=None)
    
    if podcast_state is None or message != "Success":
        raise ValueError(f"Failed to create podcast state: {message}")
    
    save_podcast_state(podcast_state, timestamp)

    enhanced_script = podcast_state["enhanced_script"].content
    
    if not enhanced_script:
        raise ValueError("No enhanced script found in the podcast state")

    # Parse the dialogue
    dialogue_pieces = parse_dialogue(enhanced_script)

    # Generate audio for each dialogue piece
    combined_audio = AudioSegment.empty()
    for piece in dialogue_pieces:
        speaker, text = piece.split(': ', 1)
        voice = "onyx" if speaker == "Host" else "nova"
        audio_content = generate_tts(text, voice=voice)
        
        # Save temporary audio file
        temp_file = f"temp_{speaker.lower()}.mp3"
        with open(temp_file, "wb") as f:
            f.write(audio_content)
        
        # Append to combined audio
        segment = AudioSegment.from_mp3(temp_file)
        combined_audio += segment
        
        # Remove temporary file
        os.remove(temp_file)

    # Export the final podcast audio
    output_audio_file = os.path.join(PROJECT_ROOT, "final_podcast.mp3")
    combined_audio.export(output_audio_file, format="mp3")
    logger.info(f"Podcast audio created successfully: {output_audio_file}")

    # Save the dialogue
    output_dialogue_file = os.path.join(PROJECT_ROOT, "podcast_dialogue.txt")
    with open(output_dialogue_file, 'w', encoding='utf-8') as f:
        for piece in dialogue_pieces:
            f.write(f"{piece}\n")
    logger.info(f"Podcast dialogue saved to: {output_dialogue_file}")

    # Save a small text file with summary information
    summary_file = os.path.join(PROJECT_ROOT, "podcast_summary.txt")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"Podcast created on: {timestamp}\n")
        f.write(f"Source PDF: {os.path.basename(pdf_path)}\n")
        f.write(f"Audio file: {os.path.basename(output_audio_file)}\n")
        f.write(f"Dialogue file: {os.path.basename(output_dialogue_file)}\n")
    logger.info(f"Podcast summary saved to: {summary_file}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create a podcast audio from a PDF file.")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--timestamp", help="Timestamp to use for prompts (format: YYYYMMDD_HHMMSS)")
    args = parser.parse_args()
    
    create_podcast_audio(args.pdf_path, args.timestamp)
