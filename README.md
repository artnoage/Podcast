# AI-Powered Podcast Creation and Optimization System

This project implements an automated workflow for creating engaging podcasts from academic texts using AI-powered agents. The system takes a PDF file as input, processes its content, and generates an audio podcast with playful banter between a host and a guest. It also includes a self-improving mechanism that optimizes the prompts used in the podcast creation process based on user feedback.

## Table of Contents

1. [Key Components and How It Works](#key-components-and-how-it-works)
2. [Setup Instructions](#setup-instructions)
3. [Timestamps](#timestamps)
4. [Usage](#usage)
5. [Project Structure](#project-structure)
6. [Try It Out](#try-it-out)
7. [TextGrad and Weight Clipping](#textgrad-and-weight-clipping)

## Key Components and How It Works

1. **Podcast Creation (src/paudio.py)**
   - Extracts text from PDF files using OCR technology.
   - Utilizes AI agents for content summarization, script writing, and script enhancement.
   - The summarizer agent condenses the academic content into key points.
   - The scriptwriter agent transforms the summary into an engaging dialogue between a host and a guest.
   - The enhancer agent adds playful banter and improves the overall flow of the conversation.
   - Generates audio using advanced text-to-speech technology, creating distinct voices for the host and guest.
   - Saves the complete podcast with a unique timestamp for version control.

2. **Feedback Collection and Prompt Optimization (src/paudiowithfeedback.py, src/utils/textGDwithWeightClipping.py)**
   - Extends the functionality of paudio.py to allow user feedback on generated podcasts.
   - Uses TextGrad, a gradient-based optimization technique, to refine the prompts used by AI agents.
   - Implements a WeightClippingAgent to ensure prompts remain general and applicable across various topics.
   - Feedback is stored with the podcast's timestamp and used to guide the optimization process.
   - New optimized prompts are saved with a new timestamp, creating a versioned history of improvements.

3. **Continuous Improvement Cycle**
   - Each podcast creation and feedback cycle contributes to the system's learning.
   - The system uses the most recent optimized prompts for each new podcast creation by default.
   - Users can specify older timestamps to use previous versions of prompts if needed, allowing for comparison and analysis of improvement over time.

4. **Simulation and Evaluation (src/simulation.py, src/evaluation.py)**
   - Simulates the podcast creation and improvement process without human intervention.
   - Uses AI-generated feedback to optimize prompts, mimicking real-world usage patterns.
   - Evaluates the quality of generated podcasts over time by comparing outputs from different prompt versions.
   - Helps assess and validate the system's improvement trajectory, ensuring that changes lead to better quality podcasts.

5. **Web Interface (frontend/, backend/fast_api_app.py)**
   - Provides a user-friendly React-based frontend for easy interaction with the system.
   - Allows users to upload PDFs, generate podcasts, and provide feedback through a web browser.
   - FastAPI backend efficiently handles requests and manages the podcast creation process.
   - Integrates all components into a cohesive system, making it accessible for non-technical users.

## Setup Instructions

### Prerequisites

- Python 3.9+
- Node.js and npm (for frontend)
- Rust (for jiter installation)
- OpenAI API key

### Backend Setup

1. **Create and activate a Conda environment:**
   ```
   conda create -n podcast_env python=3.9
   conda activate podcast_env
   ```

2. **Install required Python packages:**
   ```
   pip install -r requirements.txt
   ```

3. **Install Rust (required for jiter):**
   - Follow the instructions at https://www.rust-lang.org/tools/install

4. **Install jiter:**
   ```
   cargo install jiter
   ```

5. **Install uvicorn:**
   ```
   pip install uvicorn
   ```

6. **Set up OpenAI API key:**
   - Create a `.env` file in the project root
   - Add your OpenAI API key: `OPENAI_API_KEY=your_api_key_here`

### Frontend Setup

1. **Install Node.js and npm:**
   - Follow the instructions at https://nodejs.org/

2. **Install frontend dependencies:**
   ```
   cd frontend
   npm install
   ```

## Timestamps

Timestamps are used in this project to version control the prompts used by the AI agents. Each time the system generates a podcast and receives feedback, it optimizes the prompts and saves them with a new timestamp. This allows the system to track the evolution of prompts over time and use the most recent or specific versions when creating new podcasts.

## Usage

1. **Generate a Podcast:**
   ```
   python src/paudio.py <path_to_pdf_file> [--timestamp YYYYMMDD_HHMMSS]
   ```
   Options:
   - `<path_to_pdf_file>`: Path to the PDF file you want to convert into a podcast.
   - `--timestamp YYYYMMDD_HHMMSS`: (Optional) Use prompts from a specific timestamp. If not provided, it uses the most recent prompts.
   - `--timestamp last`: Use the most recent timestamp (same as not providing a timestamp).

2. **Generate a Podcast with Feedback:**
   ```
   python src/paudiowithfeedback.py <path_to_pdf_file> [--timestamp YYYYMMDD_HHMMSS]
   ```
   This script creates a podcast and allows you to provide feedback, which is then used to optimize the prompts.

3. **Run Self-Improving Simulation:**
   ```
   python src/simulation.py
   ```
   This script runs a simulation of the podcast creation and prompt optimization process.

4. **Evaluate Self-Improvement Process:**
   ```
   python src/evaluation.py
   ```
   This script evaluates the quality of generated podcasts over time.

5. **Start the Web Interface:**
   - Backend:
     ```
     uvicorn backend.fast_api_app:app --reload
     ```
   - Frontend:
     ```
     cd frontend
     npm start
     ```
   - Access the interface at `http://localhost:3000`

## Project Structure

- `src/paudio.py`: Main script for podcast creation
- `src/paudiowithfeedback.py`: Script for podcast creation with feedback collection
- `src/utils/textGDwithWeightClipping.py`: Prompt optimization script
- `src/simulation.py`: Simulation of the self-improvement process
- `src/evaluation.py`: Evaluation script for generated podcasts
- `backend/fast_api_app.py`: FastAPI backend application
- `frontend/`: React-based frontend application
- `requirements.txt`: List of Python dependencies

## Try It Out

You can try this AI-powered podcast creation tool for free at [https://www.metaskepsis.com/](https://www.metaskepsis.com/). Experience the power of AI-generated podcasts and see how this system can transform academic texts into engaging audio content.

## TextGrad and Weight Clipping

This project draws inspiration from TextGrad, a novel approach to optimization in natural language processing introduced by Mert Yuksekgonul, Federico Bianchi, Joseph Boen, Sheng Liu, Zhi Huang, Carlos Guestrin, and James Zou.

An additional feature implemented here is a "weight clipper" concept, which draws an interesting parallel to gradient clipping in traditional stochastic gradient descent (SGD). In SGD, gradient clipping prevents exploding gradients and ensures stable training. Similarly, in this TextGrad-inspired implementation, the weight clipper constrains modifications to prompts or other textual elements during the optimization process. This helps maintain coherence, prevents drastic changes to the text, and keeps textual modifications meaningful and aligned with the original intent.

The project also addresses the challenge of applying gradients to a chain of agents in LangGraph. The solution implemented here uses a role-specific loss function for each agent, while providing the same final feedback to all agents. This approach allows each agent to determine independently what changes to make based on their specific role and the overall feedback, optimizing the entire chain of agents while respecting their individual functions within the larger process.
