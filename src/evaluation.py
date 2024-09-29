import os
from dotenv import load_dotenv
import random
import csv
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.utils.utils import create_podcast, extract_text_from_pdf, get_random_arxiv_file, get_all_timestamps, save_podcast_state
from src.utils.agents_and_workflows import EvaluatorAgent
from typing import Tuple, Optional

load_dotenv()

def choose_random_timestamps(n=2):
    all_timestamps = get_all_timestamps()
    if len(all_timestamps) < n:
        raise ValueError(f"Not enough timestamps available. Found {len(all_timestamps)}, need at least {n}.")
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
    os.makedirs("evaluation_plots", exist_ok=True)
    
    # Save the plot with a unique filename
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_filename = f"evaluation_plots/prompt_performance_{current_time}.png"
    plt.savefig(plot_filename)
    plt.close()
    
    print(f"Plot saved as: {plot_filename}")

    # Save the raw data to a CSV file
    csv_filename = f"evaluation_plots/raw_data_{current_time}.csv"
    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Timestamp', 'Raw Points', 'Normalized Points'])
        for t, p, np in zip(timestamps, points, normalized_points):
            writer.writerow([t, p, np])
    
    print(f"Raw data saved as: {csv_filename}")

def process_evaluation(evaluator, prompt_model, prompt_provider, i) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    while True:
        try:
            print(f"{i}-th generation")
            pdf_path = get_random_arxiv_file()
            original_text = extract_text_from_pdf(pdf_path)

            timestamp1, timestamp2 = choose_random_timestamps(2)
            
            podcast1, message1 = create_podcast(pdf_path, timestamp=timestamp1, summarizer_model=prompt_model, scriptwriter_model=prompt_model, enhancer_model=prompt_model, provider=prompt_provider, api_key=os.getenv("OPENAI_API_KEY"))
            if podcast1 is None or message1 != "Success":
                raise ValueError(f"Failed to create podcast1: {message1}")
            
            podcast2, message2 = create_podcast(pdf_path, timestamp=timestamp2, summarizer_model=prompt_model, scriptwriter_model=prompt_model, enhancer_model=prompt_model, provider=prompt_provider, api_key=os.getenv("OPENAI_API_KEY"))
            if podcast2 is None or message2 != "Success":
                raise ValueError(f"Failed to create podcast2: {message2}")
            
            evaluation = evaluator.evaluate_podcasts(original_text, podcast_state1["enhanced_script"].content, podcast_state2["enhanced_script"].content)
            
            return timestamp1, timestamp2, evaluation
        except Exception as e:
            print(f"An error occurred: {str(e)}. Retrying...")
            continue

def main():
    evaluator_models = [ ("OpenAI", "gpt-4o-mini")]
    prompt_models = [ ("OpenAI", "gpt-4o-mini")]
    #evaluator_models = [("OpenRouter", "google/gemini-pro-1.5")]
    #prompt_models = [("OpenRouter", "openai/gpt-4o-mini")]

    for evaluator_provider, evaluator_model in evaluator_models:
        for prompt_provider, prompt_model in prompt_models:
            scores = {}
            evaluator = EvaluatorAgent(model=evaluator_model, provider=evaluator_provider)

            with ThreadPoolExecutor(max_workers=20) as executor:
                # Submit all tasks
                futures = [executor.submit(process_evaluation, evaluator, prompt_model, prompt_provider, i) for i in range(300)]
                
                # Process results as they complete
                for future in as_completed(futures):
                    timestamp1, timestamp2, evaluation = future.result()
                    if "1" in evaluation.lower() and "2" not in evaluation.lower():
                        update_scores(scores, timestamp1)
                    elif "2" in evaluation.lower() and "1" not in evaluation.lower():
                        update_scores(scores, timestamp2)
                    else:
                        print(f"Unclear or tie response from evaluator: {evaluation}")

                plot_scores(scores, evaluator_model, prompt_model)
                print(f"Evaluation complete for evaluator: {evaluator_model}, prompt: {prompt_model}. Results plotted.")

if __name__ == "__main__":
    main()
