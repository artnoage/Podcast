import os
from dotenv import load_dotenv

load_dotenv()
from datetime import datetime
import re
try:
    from src.utils.utils import create_podcast, parse_dialogue, save_podcast_state, add_feedback_to_state, get_random_arxiv_file
    from src.utils.agents_and_workflows import FeedbackAgent, PersonalityCreatorAgent
    from src.utils.textGDwithWeightClipping import optimize_prompt
except ImportError:
    from utils.utils import create_podcast, parse_dialogue, save_podcast_state, add_feedback_to_state, get_random_arxiv_file
    from utils.agents_and_workflows import FeedbackAgent, PersonalityCreatorAgent
    from utils.textGDwithWeightClipping import optimize_prompt

# Predefined values for provider and models
podcast_provider = "OpenAI"
podcast_model = "gpt-4o-mini"
feedback_provider = "OpenAI"
feedback_model = "gpt-4o"
personality_provider = "OpenAI"
personality_model = "gpt-4o-mini"


def get_last_timestamp():
    prompt_history_dir = "prompt_history"
    if not os.path.exists(prompt_history_dir):
        return None
    
    history_files = os.listdir(prompt_history_dir)
    if not history_files:
        return None
    
    timestamps = []
    for filename in history_files:
        match = re.search(r'(\d{8}_\d{6})', filename)
        if match:
            try:
                timestamp_str = match.group(1)
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                timestamps.append(timestamp)
            except ValueError:
                continue
    
    if timestamps:
        return max(timestamps).strftime("%Y%m%d_%H%M%S")
    return None

def process_pdf_and_improve_prompts():
    # Get a random PDF file from the arxiv folder
    pdf_path = get_random_arxiv_file()
    print(f"Selected PDF: {pdf_path}")

    # Get the last timestamp (for loading prompts)
    last_timestamp = get_last_timestamp()
    print(f"Using prompts from timestamp: {last_timestamp or 'default'}")

    # Create a new timestamp for saving results
    new_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create the podcast
    final_state, message = create_podcast(pdf_path, timestamp=last_timestamp, summarizer_model=podcast_model, scriptwriter_model=podcast_model, enhancer_model=podcast_model, provider=podcast_provider, api_key=os.getenv("OPENAI_API_KEY"))

    if message != "Success":
        print(f"Error creating podcast: {message}")
        return False

    if final_state is None:
        print("Error: final_state is None")
        return False

    # Parse the dialogue
    enhanced_script = final_state["enhanced_script"].content
    dialogue_pieces = parse_dialogue(enhanced_script)

    # Generate personality
    personality_creator = PersonalityCreatorAgent(model=personality_model, provider=personality_provider)
    personality = personality_creator.create_personality()
    print("\n=== Generated Personality ===\n")

    # Process feedback
    text = final_state["main_text"].content
    feedback_agent = FeedbackAgent(model=feedback_model, provider=feedback_provider)
    feedback = feedback_agent.run_feedback(original_text=text, final_product=enhanced_script, personality=personality)
    
    # Save the podcast state with new timestamp
    save_podcast_state(final_state, new_timestamp)

    # If feedback was generated, add it to the state file
    add_feedback_to_state(new_timestamp, feedback)

    # Save parsed dialogue pieces
    podcast_history_dir = "podcast_history"
    os.makedirs(podcast_history_dir, exist_ok=True)
    dialogue_file = os.path.join(podcast_history_dir, f"dialogue_pieces_{new_timestamp}.txt")
    with open(dialogue_file, 'w', encoding='utf-8') as f:
        for piece in dialogue_pieces:
            f.write(f"{piece}\n")
    print(f"\nParsed Dialogue Pieces saved to: {dialogue_file}")

    # Optimize prompts
    optimize_prompt("summarizer", last_timestamp, new_timestamp, "gpt-4o-mini", "gpt-4o-mini")
    optimize_prompt("scriptwriter", last_timestamp, new_timestamp, "gpt-4o-mini", "gpt-4o-mini")
    optimize_prompt("enhancer", last_timestamp, new_timestamp, "gpt-4o-mini", "gpt-4o-mini")

    return True

r = 1
def main():
    for iteration in range(r):
        print(f"\nStarting iteration {iteration + 1} of {r}...\n")
        process_pdf_and_improve_prompts()
        
if __name__ == "__main__":
    main()
