import os
import re
from datetime import datetime
import PyPDF2
import markdown
import random
import json
import io
from typing import List, Tuple, Optional
try:
    from src.utils.agents_and_workflows import PodcastCreationWorkflow, PodcastState
except ImportError:
    from utils.agents_and_workflows import PodcastCreationWorkflow, PodcastState
from langchain_core.messages import HumanMessage
import tiktoken

def get_project_root():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(current_dir))

PROJECT_ROOT = get_project_root()

def get_all_timestamps():
    prompt_history_dir = os.path.join(PROJECT_ROOT, "prompt_history")
    if not os.path.exists(prompt_history_dir):
        print(f"Directory '{prompt_history_dir}' does not exist.")
        return []
    
    print(f"Searching for timestamps in '{prompt_history_dir}'...")
    
    timestamps = set()
    for filename in os.listdir(prompt_history_dir):
        match = re.search(r'(\d{8}_\d{6})', filename)
        if match:
            try:
                timestamp_str = match.group(1)
                datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                timestamps.add(timestamp_str)
            except ValueError:
                print(f"Warning: Invalid timestamp format in file '{filename}'")
    
    sorted_timestamps = sorted(list(timestamps))
    print(f"Found {len(sorted_timestamps)} unique timestamps.")
    return sorted_timestamps

def get_last_timestamp():
    timestamps = get_all_timestamps()
    return timestamps[-1] if timestamps else None


def load_prompt(role, timestamp=None):
    prompt_file = f"{role}_prompt.txt"
    prompts_dir = os.path.join(PROJECT_ROOT, "prompts")
    
    if timestamp:
        prompt_history_dir = os.path.join(PROJECT_ROOT, "prompt_history")
        os.makedirs(prompt_history_dir, exist_ok=True)  # Ensure the directory exists
        history_file = f"{role}_prompt_{timestamp}.txt"
        history_path = os.path.join(prompt_history_dir, history_file)
        
        if os.path.exists(history_path):
            print(f"Loading prompt for {role} from history: {history_path}")
            with open(history_path, 'r') as file:
                return file.read().strip()
        else:
            print(f"No history found for {role} with timestamp {timestamp}")
    
    # If no timestamp provided or file not found, fall back to the original prompt file
    prompt_path = os.path.join(prompts_dir, prompt_file)
    print(f"Loading original prompt for {role} from: {prompt_path}")
    with open(prompt_path, 'r') as file:
        return file.read().strip()

def load_podcast_state(timestamp):
    state_file = f"podcast_state_{timestamp}.json"
    podcast_states_dir = os.path.join(PROJECT_ROOT, "podcast_states")
    state_file_path = os.path.join(podcast_states_dir, state_file)
    if os.path.exists(state_file_path):
        print(f"Loading podcast state from: {state_file_path}")
        with open(state_file_path, 'r') as f:
            return json.load(f)
    else:
        print(f"No podcast state found for timestamp: {timestamp}")
        print(f"Searched in: {state_file_path}")
        return None

def format_text_with_line_breaks(text, words_per_line=15):
    words = text.split()
    formatted_lines = []
    for i in range(0, len(words), words_per_line):
        line = ' '.join(words[i:i+words_per_line])
        formatted_lines.append(line)
    return '\n'.join(formatted_lines)


def extract_text_from_pdf(pdf_content: bytes) -> Tuple[Optional[str], int]:
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        text = "".join(page.extract_text() for page in pdf_reader.pages)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None, 0
    
    if not text.strip():
        return None, 0
    
    # Count tokens
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    token_count = len(tokens)
    
    return text, token_count

def pdf_to_markdown(pdf_path: str) -> None:
    text = extract_text_from_pdf(pdf_path)
    md = markdown.markdown(text)
    output_path = pdf_path.rsplit('.', 1)[0] + '.md'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"Markdown file created: {output_path}")

def get_random_arxiv_file():
    arxiv_folder = os.path.join(PROJECT_ROOT, "arxiv_papers")
    
    if not os.path.exists(arxiv_folder):
        print(f"The '{arxiv_folder}' folder does not exist.")
        return None
    
    pdf_files = [f for f in os.listdir(arxiv_folder) if f.endswith('.pdf')]
    if not pdf_files:
        print(f"No PDF files found in the '{arxiv_folder}' folder.")
        return None
    
    return os.path.join(arxiv_folder, random.choice(pdf_files))

def save_podcast_state(state: PodcastState, timestamp: str):
    filename = f"podcast_state_{timestamp}.json"
    
    data = {
        "main_text": state["main_text"].content,
        "key_points": state["key_points"].content,
        "script_essence": state["script_essence"].content,
        "enhanced_script": state["enhanced_script"].content
    }
    
    podcast_states_dir = os.path.join(PROJECT_ROOT, "podcast_states")
    
    os.makedirs(podcast_states_dir, exist_ok=True)
    filepath = os.path.join(podcast_states_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Podcast state saved to {filepath}")

def add_feedback_to_state(timestamp: str, feedback: str):
    filename = f"podcast_state_{timestamp}.json"
    
    podcast_states_dir = os.path.join(PROJECT_ROOT, "podcast_states")
    
    filepath = os.path.join(podcast_states_dir, filename)
    
    if not os.path.exists(filepath):
        print(f"Error: Podcast state file {filepath} not found.")
        return
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    data["feedback"] = feedback
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Feedback added to {filepath}")

def parse_dialogue(text: str) -> List[str]:
    pattern = r'(Host:|Guest:)'
    pieces = re.split(pattern, text)
    dialogue_pieces = []
    for i in range(1, len(pieces), 2):
        dialogue_pieces.append(f"{pieces[i].strip()} {pieces[i+1].strip()}")
    return dialogue_pieces

async def create_podcast(pdf_content: bytes, timestamp: str = None, summarizer_model: str = "openai/gpt-4o-mini", scriptwriter_model: str = "openai/gpt-4o-mini", enhancer_model: str = "openai/gpt-4o-mini", provider: str = "OpenRouter", api_key: str = None) -> Tuple[Optional[PodcastState], str]:
    text, token_count = extract_text_from_pdf(pdf_content)

    if text is None:
        return None, "Error extracting text from PDF"

    if token_count > 40000:
        return None, f"PDF content exceeds 40,000 tokens (current: {token_count})"

    if not text.strip():
        return None, "Extracted text is empty"

    # If api_key is None, don't pass it to PodcastCreationWorkflow
    workflow_obj = PodcastCreationWorkflow(summarizer_model, scriptwriter_model, enhancer_model, timestamp, provider, api_key) if api_key else PodcastCreationWorkflow(summarizer_model, scriptwriter_model, enhancer_model, timestamp, provider)
    workflow = workflow_obj.create_workflow()
    workflow = workflow.compile()

    state = PodcastState(
        main_text=HumanMessage(content=text),
        key_points=None,
        script_essence=None,
        enhanced_script=None)

    try:
        final_state = await workflow.ainvoke(state)
        return final_state, "Success"
    except Exception as e:
        return None, f"Error creating podcast: {str(e)}"
