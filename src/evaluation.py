import os
from dotenv import load_dotenv
import random
import csv
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple, Optional

# Get the project root directory
def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add the project root to sys.path
import sys
sys.path.append(get_project_root())

from src.utils.utils import create_podcast, extract_text_from_pdf, get_random_arxiv_file, get_all_timestamps
from src.utils.agents_and_workflows import EvaluatorAgent

load_dotenv()

# Set the PROJECT_ROOT
PROJECT_ROOT = get_project_root()

def choose_random_timestamps(n=2):
    all_timestamps = get_all_timestamps()
    if len(all_timestamps) < n:
        print(f"Warning: Not enough timestamps available. Found {len(all_timestamps)}, need at least {n}.")
        return all_timestamps if all_timestamps else [None, None]
    return random.sample(all_timestamps, n)

def update_scores(scores, winner):
    if winner in scores:
        scores[winner] += 1
    else:
        scores[winner] = 1

def plot_scores(scores,  evaluator_model, prompt_model):
    timestamps = sorted(scores.keys())
    points = [scores[t] for t in timestamps]

    # Normalize the points
    total_points = sum(points)
    normalized_points = [p / total_points for p in points] if total_points > 0 else points

    plt.figure(figsize=(12, 6))
    plt.plot(timestamps, normalized_points, marker='o')
    plt.title("Normalized Prompt Performance Over Time")
    plt.xlabel("Timestamp")
    plt.ylabel("Normalized Points")
    plt.xticks(rotation=45)
    
    # Add evaluator, prompt model, and provider information
    info_text = f"Evaluator: {evaluator_model}\nPrompt: {prompt_model}"
    plt.text(0.02, 0.98, info_text, 
             transform=plt.gca().transAxes, verticalalignment='top', 
             fontsize=8, bbox=dict(facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    # Create a directory for plots and data if it doesn't exist
    plots_dir = os.path.join(PROJECT_ROOT, "evaluation_plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    # Save the plot with a unique filename
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_filename = os.path.join(plots_dir, f"prompt_performance_{current_time}.png")
    plt.savefig(plot_filename)
    plt.close()
    
    print(f"Plot saved as: {plot_filename}")

    # Save the raw data to a CSV file
    csv_filename = os.path.join(plots_dir, f"raw_data_{current_time}.csv")
    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Timestamp', 'Raw Points', 'Normalized Points'])
        for t, p, np in zip(timestamps, points, normalized_points):
            writer.writerow([t, p, np])
    
    print(f"Raw data saved as: {csv_filename}")

def process_evaluation(evaluator, prompt_model, prompt_provider, i) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    print(f"{i}-th generation")
    pdf_path = get_random_arxiv_file()
    if pdf_path is None:
        print("No more PDF files available in the arxiv_folder. Stopping the evaluation process.")
        return None, None, None
    
    try:
        original_text, token_count = extract_text_from_pdf(pdf_path)
        if original_text is None:
            print(f"Failed to extract text from PDF: {pdf_path}")
            return None, None, None

        timestamp1, timestamp2 = choose_random_timestamps(2)
        
        podcast1, message1 = create_podcast(pdf_path, timestamp=timestamp1, summarizer_model=prompt_model, scriptwriter_model=prompt_model, enhancer_model=prompt_model, provider=prompt_provider, api_key=os.getenv("OPENAI_API_KEY"))
        if podcast1 is None or message1 != "Success":
            print(f"Failed to create podcast1: {message1}")
            return None, None, None
        
        api_key = os.getenv("OPENAI_API_KEY") if prompt_provider == "OpenAI" else os.getenv("OPENROUTER_API_KEY")
        podcast2, message2 = create_podcast(pdf_path, timestamp=timestamp2, summarizer_model=prompt_model, scriptwriter_model=prompt_model, enhancer_model=prompt_model, provider=prompt_provider, api_key=api_key)
        if podcast2 is None or message2 != "Success":
            print(f"Failed to create podcast2: {message2}")
            return None, None, None
        
        evaluation = evaluator.evaluate_podcasts(original_text, podcast1["enhanced_script"].content, podcast2["enhanced_script"].content)
        
        return timestamp1, timestamp2, evaluation
    except Exception as e:
        print(f"An error occurred: {str(e)}. Skipping this evaluation.")
        return None, None, None

def main():
    evaluator_models = [ ("OpenAI", "gpt-4o-mini")]
    prompt_models = [ ("OpenAI", "gpt-4o-mini")]
    #evaluator_models = [("OpenRouter", "google/gemini-pro-1.5")]
    #prompt_models = [("OpenRouter", "openai/gpt-4o-mini")]

    # Ensure prompt_history directory exists
    prompt_history_dir = os.path.join(PROJECT_ROOT, "prompt_history")
    os.makedirs(prompt_history_dir, exist_ok=True)

    for evaluator_provider, evaluator_model in evaluator_models:
        for prompt_provider, prompt_model in prompt_models:
            scores = {}
            evaluator = EvaluatorAgent(model=evaluator_model, provider=evaluator_provider)

            with ThreadPoolExecutor(max_workers=2) as executor:
                # Submit all tasks
                futures = [executor.submit(process_evaluation, evaluator, prompt_model, prompt_provider, i) for i in range(2)]
                
                # Process results as they complete
                all_none = True
                for future in as_completed(futures):
                    timestamp1, timestamp2, evaluation = future.result()
                    if timestamp1 is None and timestamp2 is None and evaluation is None:
                        continue
                    all_none = False
                    if evaluation:
                        if "1" in evaluation.lower() and "2" not in evaluation.lower():
                            update_scores(scores, timestamp1)
                        elif "2" in evaluation.lower() and "1" not in evaluation.lower():
                            update_scores(scores, timestamp2)
                        else:
                            print(f"Unclear or tie response from evaluator: {evaluation}")
                    else:
                        print("No evaluation result available.")

                if all_none:
                    print("All evaluations failed or no PDF files were available. Stopping the process.")
                    break

                if scores:  # Only plot if we have any scores
                    plot_scores(scores, evaluator_model, prompt_model)
                    print(f"Evaluation complete for evaluator: {evaluator_model}, prompt: {prompt_model}. Results plotted.")
                else:
                    print("No evaluations were completed successfully. No results to plot.")

if __name__ == "__main__":
    main()
