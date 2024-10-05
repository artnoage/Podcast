# AI-Powered Podcast Creation and Optimization System

This project implements an automated workflow for creating engaging podcasts from academic texts using AI-powered agents. The system takes a PDF file as input, processes its content, and generates an audio podcast with playful banter between a host and a guest. It also includes a self-improving mechanism that optimizes the prompts used in the podcast creation process based on user feedback.

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

This integrated system creates a feedback loop where each podcast generation, user interaction, and optimization cycle contributes to improving the overall quality of the AI-generated podcasts. The use of timestamps throughout the process ensures version control and allows for detailed analysis of the system's evolution over time.


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

   Examples:
   ```
   python src/paudio.py path/to/your/file.pdf
   python src/paudio.py path/to/your/file.pdf --timestamp 20230615_120000
   python src/paudio.py path/to/your/file.pdf --timestamp last
   ```

2. **Generate a Podcast with Feedback:**
   ```
   python src/paudiowithfeedback.py <path_to_pdf_file> [--timestamp YYYYMMDD_HHMMSS]
   ```
   This script creates a podcast and allows you to provide feedback, which is then used to optimize the prompts.

   Options:
   - `<path_to_pdf_file>`: Path to the PDF file you want to convert into a podcast.
   - `--timestamp YYYYMMDD_HHMMSS`: (Optional) Use prompts from a specific timestamp.
   - `--timestamp last`: Use the most recent timestamp (default behavior if no timestamp is provided).

   The script will:
   - Create a podcast using the specified or most recent prompts
   - Save the audio and dialogue text with a new timestamp
   - Ask for your feedback
   - Add the feedback to the podcast state with the new timestamp
   - Use the feedback to optimize the prompts for future use, creating a new set of prompts with the new timestamp

   How it works with timestamps:
   - If no timestamp is provided or 'last' is specified, it uses the most recent set of prompts
   - It generates a new timestamp for the created podcast
   - Feedback and optimized prompts are associated with this new timestamp
   - This allows for tracking the evolution of prompts over time and using specific versions when needed

   Examples:
   ```
   python src/paudiowithfeedback.py path/to/your/file.pdf
   python src/paudiowithfeedback.py path/to/your/file.pdf --timestamp 20230615_120000
   python src/paudiowithfeedback.py path/to/your/file.pdf --timestamp last
   ```

3. **Run Self-Improving Simulation:**
   ```
   python src/simulation.py
   ```
   This script runs a simulation of the podcast creation and prompt optimization process:
   - It randomly selects PDF files from the `arxiv_papers` folder in the project root directory.
   - For each selected PDF, it generates a podcast using the current prompts.
   - An AI agent provides feedback on the generated podcast, simulating human feedback.
   - Based on this feedback, the system optimizes the prompts for future use.
   - This process repeats, simulating the improvement of the system over time without human intervention.
   
   Note: Before running the simulation, make sure to add PDF files to the `arxiv_papers` folder.

4. **Evaluate Self-Improvement Process:**
   ```
   python src/evaluation.py
   ```
   This script evaluates the quality of generated podcasts over time:
   - It randomly selects PDF files from the `arxiv_papers` folder.
   - For each selected PDF, it generates two podcasts:
     1. One using randomly selected prompts from different timestamps.
     2. Another using the most recent prompts.
   - An AI evaluator then compares these two podcasts and chooses the better one.
   - This process helps assess whether the system's prompts are improving over time.

5. **Web Interface:**
   - Start the backend:
     ```
     uvicorn backend.fast_api_app:app --reload
     ```
   - Start the frontend:
     ```
     cd frontend
     npm start
     ```
   - Access the interface at `http://localhost:3000`

## Requirements

- Python 3.7+
- OpenAI API key
- Required Python packages (install via `pip install -r requirements.txt`)
- Node.js and npm for the frontend

### Installing Node.js and npm

Node.js and npm are required for the frontend. Here's how to install them on different operating systems:

#### Windows:
1. Download the installer from the official Node.js website: https://nodejs.org/
2. Run the installer and follow the installation wizard.
3. Restart your computer after installation.

#### macOS:
1. Using Homebrew (recommended):
   ```
   brew install node
   ```
2. Alternatively, download the macOS installer from https://nodejs.org/ and run it.

#### Linux:
For Ubuntu or Debian-based distributions:
```
sudo apt update
sudo apt install nodejs npm
```

For other distributions, refer to your package manager or the official Node.js documentation.

Verify the installation by running:
```
node --version
npm --version
```

## Project Structure

- `src/paudio.py`: Main script for podcast creation
- `src/utils/textGDwithWeightClipping.py`: Prompt optimization script
- `src/simulation.py`: Simulation of the self-improvement process
- `src/evaluation.py`: Evaluation script for generated podcasts
- `backend/fast_api_app.py`: FastAPI backend application
- `frontend/`: React-based frontend application

## Note

This project uses OpenAI's GPT models, which require an API key and may incur costs. Ensure you have appropriate credits or billing set up with OpenAI.

For detailed information on setup, usage, and the self-improvement mechanism, please refer to the sections below.

## Try It Out

You can try this AI-powered podcast creation tool for free at [https://www.metaskepsis.com/](https://www.metaskepsis.com/). Experience the power of AI-generated podcasts and see how this system can transform academic texts into engaging audio content.

## TextGrad and Weight Clipping


This project draws inspiration from TextGrad, a novel approach to optimization in natural language processing introduced by Mert Yuksekgonul, Federico Bianchi, Joseph Boen, Sheng Liu, Zhi Huang, Carlos Guestrin, and James Zou.

An additional feature implemented here is a "weight clipper" concept, which draws an interesting parallel to gradient clipping in traditional stochastic gradient descent (SGD). In SGD, gradient clipping prevents exploding gradients and ensures stable training. Similarly, in this TextGrad-inspired implementation, the weight clipper constrains modifications to prompts or other textual elements during the optimization process. This helps maintain coherence, prevents drastic changes to the text, and keeps textual modifications meaningful and aligned with the original intent. This approach adapts optimization concepts to the unique challenges of working with natural language, bridging the gap between traditional machine learning techniques and language model optimization.

Another challenge addressed in this project is applying gradients to a chain of agents in LangGraph. The solution implemented here uses a role-specific loss function for each agent, while providing the same final feedback to all agents. This approach allows each agent to determine independently what changes to make based on their specific role and the overall feedback. It's worth noting that feedback allocation is a distinct and complex problem in reinforcement learning, and there's no one-size-fits-all solution. By implementing this method, the system attempts to optimize the entire chain of agents while respecting their individual functions within the larger process, though it's an area that likely warrants further exploration and refinement.
