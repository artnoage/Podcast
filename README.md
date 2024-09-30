# AI-Powered Podcast Creation and Optimization System

This project implements an automated workflow for creating engaging podcasts from academic texts using AI-powered agents. The system takes a PDF file as input, processes its content, and generates an audio podcast with playful banter between a host and a guest. It also includes a self-improving mechanism that optimizes the prompts used in the podcast creation process based on user feedback.

## Key Components

1. **Podcast Creation (paudio.py)**
   - Extracts text from PDF files
   - Utilizes AI agents for summarization, script writing, and script enhancement
   - Generates audio using text-to-speech technology
   - Creates a complete podcast from academic content

2. **Prompt Optimization (src/utils/textGDwithWeightClipping.py)**
   - Uses TextGrad for gradient-based optimization of prompts
   - Implements a WeightClippingAgent to maintain prompt generality
   - Continuously improves the system based on user feedback

3. **Simulation and Evaluation**
   - Simulates the podcast creation and improvement process
   - Evaluates the quality of generated podcasts over time

4. **Web Interface**
   - React-based frontend for user interaction
   - FastAPI backend for handling requests and managing the podcast creation process

## How It Works

1. **Podcast Creation:**
   - The system reads a PDF file and extracts its content.
   - AI agents summarize the content, create a script, and enhance it with engaging dialogue.
   - Text-to-speech technology converts the script into audio.

2. **Prompt Optimization:**
   - User feedback is collected on generated podcasts.
   - TextGrad optimizes the prompts used by AI agents based on this feedback.
   - The WeightClippingAgent ensures prompts remain general and applicable across topics.

3. **Continuous Improvement:**
   - Each podcast creation cycle contributes to the system's learning.
   - Prompts evolve over time, stored with timestamps for version control.
   - The system uses the most recent optimized prompts for each new podcast creation.

## Usage

1. **Generate a Podcast:**
   ```
   python src/paudio.py <path_to_pdf_file> [--timestamp YYYYMMDD_HHMMSS]
   ```

2. **Run Self-Improving Simulation:**
   ```
   python src/simulation.py
   ```

3. **Evaluate Self-Improvement Process:**
   ```
   python src/evaluation.py
   ```

4. **Web Interface:**
   - Start the backend:
     ```
     uvicorn backend.fast_api_app:app --reload
     ```
   - Start the frontend:
     ```
     cd creator-front-end
     npm start
     ```
   - Access the interface at `http://localhost:3000`

## Requirements

- Python 3.7+
- OpenAI API key
- Required Python packages (install via `pip install -r requirements.txt`)
- Node.js and npm for the frontend

## Project Structure

- `src/paudio.py`: Main script for podcast creation
- `src/utils/textGDwithWeightClipping.py`: Prompt optimization script
- `src/simulation.py`: Simulation of the self-improvement process
- `src/evaluation.py`: Evaluation script for generated podcasts
- `backend/fast_api_app.py`: FastAPI backend application
- `creator-front-end/`: React-based frontend application

## Note

This project uses OpenAI's GPT models, which require an API key and may incur costs. Ensure you have appropriate credits or billing set up with OpenAI.

For detailed information on setup, usage, and the self-improvement mechanism, please refer to the sections below.
