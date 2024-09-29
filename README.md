# Podcast Creation Workflow

This project implements an automated workflow for creating podcast scripts from academic texts using AI-powered agents. The system takes a PDF file as input, processes its content, and generates an engaging podcast script with playful banter between a host and a guest. It also includes a prompt improvement feature and feedback generation.

## Key Components

1. **PDF Text Extraction**: The system extracts text from a given PDF file using the PyPDF2 library.

2. **Podcast Creation Workflow**: The main workflow consists of three AI agents:
   - **Summarizer**: Extracts key points from the original academic text.
   - **Scriptwriter**: Creates a script focusing on the essence of the content based on the key points.
   - **Enhancer**: Transforms the script into an engaging dialogue with playful banter.

3. **PersonalityCreatorAgent**: Generates a unique personality for the podcast critic, which is used to tailor the feedback.

4. **Feedback Generation**: After the main workflow, a feedback agent provides critical analysis of the generated content compared to the original text, taking into account the generated personality.

5. **WeightClippingAgent**: Cleans and refines the optimized system prompts to ensure they remain abstract, topic-agnostic, and relevant to their specific roles.

6. **Prompt Improvement**: The `prompt_improving.py` script optimizes the prompts for each agent based on feedback and performance, and then uses the WeightClippingAgent to clean the optimized prompts.

7. **Flexible Model Selection**: The system allows specifying different models for each agent in the podcast creation process.

8. **Evaluation System**: An evaluation script (`evaluation.py`) compares podcast scripts generated using different prompts to assess their quality and track improvements over time.

## Key Files

- `simulation.py`: The entry point of the simulation process, orchestrating the entire self-improvement workflow.
- `create_podcast.py`: Contains functions for creating podcasts, saving podcast states, and adding feedback.
- `agents_and_workflows.py`: Contains the implementation of the PodcastCreationWorkflow, PersonalityCreatorAgent, FeedbackAgent, and WeightClippingAgent.
- `prompts/`: Directory containing prompt templates for each agent, including files for personality creation, weight clipping, and evaluation.
- `textGDwithWeightClipping.py`: Script for optimizing agent prompts and applying weight clipping.
- `evaluation.py`: Script for evaluating and comparing podcast scripts generated with different prompts.
- `paudio.py`: Script for generating actual podcast audio using a specific prompt generation, separate from the self-improvement process.
- `backend/fast_api_app.py`: FastAPI backend application for handling API requests from the frontend.

## Project Structure

- `arxiv_papers/`: Directory for storing input PDF files.
- `podcast_states/`: Directory for saving podcast creation states and feedback.
- `prompt_history/`: Directory for storing optimized prompts.
- `prompts/`: Directory containing prompt templates for each agent.
- `creator-front-end/`: React-based frontend application for the web interface.

## How It Works

1. The system reads a random PDF file from the `arxiv_papers` folder.
2. The extracted text is passed through the PodcastCreationWorkflow:
   - The Summarizer extracts key points.
   - The Scriptwriter creates a script based on these key points.
   - The Enhancer transforms the script into a dialogue with playful banter.
3. The dialogue is parsed into separate pieces for the host and guest.
4. The PersonalityCreatorAgent generates a unique personality for the podcast critic.
5. The FeedbackAgent provides critical feedback on the final product compared to the original text, taking into account the generated personality.
6. The podcast state is saved, and the generated feedback is added to the state file.
7. The system then enters a self-improvement phase using the `textGDwithWeightClipping.py` script:
   - It utilizes TextGrad, a powerful gradient-based text optimization library, to refine the prompts for each agent based on the feedback received.
   - TextGrad analyzes the feedback and computes gradients to adjust the prompts, aiming to address the identified shortcomings.
   - After the TextGrad optimization, the WeightClippingAgent comes into play. This specialized agent:
     * Cleans and refines the optimized prompts to ensure they remain abstract and topic-agnostic.
     * Removes any overly specific instructions that might limit the prompts' applicability.
     * Maintains the overall structure and intent of each prompt while improving its versatility.
   - The final, cleaned, and optimized prompts are then saved in the `prompt_history` folder with a timestamp.
8. For subsequent iterations, the system uses the most recently optimized prompts from the `prompt_history` folder.
9. The evaluation script (`evaluation.py`) is used to compare podcast scripts generated with different prompts:
   - It selects random timestamps (representing different prompt versions) and generates podcasts using these prompts.
   - An evaluator agent compares the generated podcasts and determines which one is better.
   - The results are tracked and plotted to visualize the performance of different prompt versions over time.
10. This self-improvement and evaluation process allows the system to continuously evolve and enhance its performance over time, learning from each podcast creation iteration and objectively measuring improvements.

## Self-Improvement Mechanism

The self-improvement mechanism is a key feature of this system, allowing it to adapt and enhance its performance over time:

1. **TextGrad Optimization**: 
   - TextGrad is used to fine-tune the prompts based on the feedback received for each podcast creation.
   - It treats the prompts as variables and computes gradients to minimize the loss between the current output and the desired output (based on feedback).
   - This allows for subtle, data-driven adjustments to the prompts that address specific shortcomings identified in the feedback.

2. **WeightClippingAgent**:
   - After TextGrad optimization, the WeightClippingAgent ensures the prompts remain generally applicable:
   - It removes instructions that are too specific or topic-dependent.
   - Maintains the core structure and intent of each prompt.
   - Ensures prompts remain abstract enough to work across various topics.
   - The name "WeightClippingAgent" is an analogy to weight clipping in neural networks:
     * In neural networks, weight clipping constrains weights within a specific range to prevent instability or overfitting.
     * Similarly, this agent "clips" or constrains the content of prompts to maintain their generality and prevent them from becoming too specialized.
     * Just as weight clipping in neural networks helps maintain generalization, the WeightClippingAgent helps maintain the versatility and broad applicability of the prompts.

3. **Continuous Learning**:
   - Each podcast creation cycle contributes to the system's learning.
   - Prompts evolve over time, stored with timestamps in the `prompt_history` folder.
   - The system can use the most recent optimized prompts for each new podcast creation, ensuring continuous improvement.

This self-improvement cycle allows the system to refine its performance incrementally, learning from each iteration to produce better podcast scripts over time.

## Requirements

- Python 3.7+
- OpenAI API key (for the gradient descent)
- OpenRouter API key (for testing different models)
- Required Python packages (install via `pip install -r requirements.txt`):
  - langchain
  - langgraph
  - PyPDF2
  - openai

## Usage

This project offers four main ways to interact with the system:

1. **Generate a Podcast from a PDF (Best Prompt)**
   To create a podcast using the current best prompt:
   ```
   python paudio.py <path_to_pdf_file> [--timestamp YYYYMMDD_HHMMSS]
   ```
   This will generate an audio file and a dialogue transcript using the most optimized prompts.

2. **Run Self-Improving Simulation**
   To start the self-improvement process:
   ```
   python simulation.py
   ```
   This will process random PDFs, generate podcasts, and continuously improve the prompts based on feedback.

3. **Evaluate Self-Improvement Process**
   To quantify and evaluate the self-improvement process:
   ```
   python evaluation.py
   ```
   This script compares podcast scripts generated using different prompts and tracks improvements over time.

4. **Web Interface**
   To use the web interface:
   
   a. Start the backend server:
   ```
   uvicorn backend.fast_api_app:app --reload
   ```
   
   b. Start the frontend development server:
   ```
   cd creator-front-end
   npm start
   ```
   
   Then open your browser and navigate to `http://localhost:3000` to access the web interface.

General Setup:
1. Ensure you have all required packages installed for both Python backend and Node.js frontend.
2. Place your input PDF files in the `arxiv_papers` folder.
3. Set your OpenAI API key as an environment variable or enter it when prompted.

The system will process PDFs, generate podcast scripts, and provide feedback. For the self-improving simulation and evaluation, it will automatically run the prompt improvement process. The web interface allows for a more user-friendly interaction with the system.

## Recent Updates

- Added ability to specify different models for each agent in the podcast creation process.
- Implemented a system to use the most recent optimized prompts from the `prompt_history` directory.
- Improved feedback handling by adding it directly to the podcast state file.
- Enhanced error handling and logging throughout the workflow.
- Renamed `prompt_improving.py` to `textGDwithWeightClipping.py` for clarity.
- Updated the utility functions in `utils.py` to include functionality from `pdf_to_markdown.py` and `create_podcast.py`.

## Note

This project uses OpenAI's GPT models, which require an API key and may incur costs. Make sure you have appropriate credits or billing set up with OpenAI.
