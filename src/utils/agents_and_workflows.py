import os
from os import path
from langgraph.graph import END, StateGraph
from langchain_core.messages import BaseMessage, HumanMessage
from typing import TypedDict
from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

class PodcastState(TypedDict):
    main_text: BaseMessage
    key_points: BaseMessage
    script_essence: BaseMessage
    enhanced_script: BaseMessage

class PodcastCreationWorkflow:
    def __init__(self, summarizer_model="openai/gpt-4o-mini", scriptwriter_model="openai/gpt-4o-mini", enhancer_model="openai/gpt-4o-mini", timestamp=None, provider="OpenRouter", api_key=None):
        self.provider = provider
        self.api_key = api_key
        self.summarizer_model = self._create_chat_model(summarizer_model, 0)
        self.scriptwriter_model = self._create_chat_model(scriptwriter_model, 0)
        self.enhancer_model = self._create_chat_model(enhancer_model, 0.7)
        self.timestamp = timestamp

        self.summarizer_system_prompt = self.load_prompt("prompts/summarizer_prompt.txt", self.timestamp)
        self.scriptwriter_system_prompt = self.load_prompt("prompts/scriptwriter_prompt.txt", self.timestamp)
        self.enhancer_system_prompt = self.load_prompt("prompts/enhancer_prompt.txt", self.timestamp)

    @staticmethod
    def load_prompt(file_path, timestamp=None):
        # Get the absolute path to the project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        
        if timestamp:
            prompt_history_dir = os.path.join(root_dir, "prompt_history")
            base_filename = os.path.basename(file_path)
            history_file = f"{base_filename}_{timestamp}"
            history_path = os.path.join(prompt_history_dir, history_file)
            
            if os.path.exists(history_path):
                with open(history_path, 'r', encoding='utf-8') as file:
                    return file.read().strip()
        
        # If no timestamp provided or file not found, fall back to the original prompt file
        absolute_path = os.path.join(root_dir, file_path)
        if not os.path.exists(absolute_path):
            raise FileNotFoundError(f"Prompt file not found: {absolute_path}")
        
        with open(absolute_path, 'r', encoding='utf-8') as file:
            return file.read().strip()

    def _create_chat_model(self, model, temperature):
        if self.provider == "OpenAI":
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                api_key=self.api_key or os.getenv("OPENAI_API_KEY")
            )
        else:  # OpenRouter
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                base_url="https://openrouter.ai/api/v1",
                api_key=self.api_key or os.getenv("OPENROUTER_API_KEY")
            )

    @staticmethod
    def load_prompt(file_path, timestamp=None):
        # Get the absolute path to the project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        
        if timestamp:
            prompt_history_dir = os.path.join(root_dir, "prompt_history")
            base_filename = os.path.basename(file_path)
            history_file = f"{base_filename}_{timestamp}"
            history_path = os.path.join(prompt_history_dir, history_file)
            
            if os.path.exists(history_path):
                with open(history_path, 'r', encoding='utf-8') as file:
                    return file.read().strip()
        
        # If no timestamp provided or file not found, fall back to the original prompt file
        absolute_path = os.path.join(root_dir, file_path)
        if not os.path.exists(absolute_path):
            raise FileNotFoundError(f"Prompt file not found: {absolute_path}")
        
        with open(absolute_path, 'r', encoding='utf-8') as file:
            return file.read().strip()

    def run_summarizer(self, state: PodcastState) -> PodcastState:
        text = state["main_text"].content

        if not text:
            raise ValueError("The main_text content is empty.")

        print("Summarizing the entire text to extract key points...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.summarizer_system_prompt),
            ("human", "{text}")
        ])
        chain = prompt | self.summarizer_model
        response = chain.invoke({"text": text})
        key_points = response.content.strip()

        state["key_points"] = HumanMessage(content=key_points)
        return state

    def run_scriptwriter(self, state: PodcastState) -> PodcastState:
        key_points = state["key_points"].content

        if not key_points:
            raise ValueError("No key points found to generate the script.")

        print("Generating script essence from key points...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.scriptwriter_system_prompt),
            ("human", "{key_points}")
        ])
        chain = prompt | self.scriptwriter_model
        response = chain.invoke({"key_points": key_points})
        script_essence = response.content.strip()

        state["script_essence"] = HumanMessage(content=script_essence)
        return state

    def run_enhancer(self, state: PodcastState) -> PodcastState:
        script_essence = state["script_essence"].content

        if not script_essence:
            raise ValueError("No script essence found to enhance.")

        print("Enhancing script with playful banter in dialogue form...")
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.enhancer_system_prompt),
            ("human", "{script_essence}")
        ])
        chain = prompt | self.enhancer_model
        response = chain.invoke({"script_essence": script_essence})
        enhanced_script = response.content.strip()

        state["enhanced_script"] = HumanMessage(content=enhanced_script)
        return state


    def create_workflow(self) -> StateGraph:
        workflow = StateGraph(PodcastState)
        workflow.set_entry_point("summarizer")
        workflow.add_node("summarizer", self.run_summarizer)
        workflow.add_node("scriptwriter", self.run_scriptwriter)
        workflow.add_node("enhancer", self.run_enhancer)

        workflow.add_edge("summarizer", "scriptwriter")
        workflow.add_edge("scriptwriter", "enhancer")
        workflow.add_edge("enhancer", END)

        return workflow

class PersonalityCreatorAgent:
    def __init__(self, model="openai/gpt-4o-mini", personality_prompt=None, provider="OpenRouter"):
        self.provider = provider
        self.personality_model = self._create_chat_model(model, 0.7)
        self.personality_prompt_template = personality_prompt or self.load_prompt("prompts/personality_creator_prompt.txt")

    def _create_chat_model(self, model, temperature):
        if self.provider == "OpenAI":
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                api_key=os.getenv("OPENAI_API_KEY")
            )
        else:  # OpenRouter
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY")
            )

    @staticmethod
    def load_prompt(file_path):
        # Get the absolute path to the project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        absolute_path = os.path.join(root_dir, file_path)
        if not os.path.exists(absolute_path):
            raise FileNotFoundError(f"Prompt file not found: {absolute_path}")
        with open(absolute_path, 'r', encoding='utf-8') as file:
            return file.read().strip()

    def create_personality(self) -> str:
        prompt = ChatPromptTemplate.from_template(self.personality_prompt_template)
        chain = prompt | self.personality_model
        print("Generating personality for feedback assessment...")
        response = chain.invoke({})
        personality = response.content.strip()
        return personality

class FeedbackAgent:
    def __init__(self, model="openai/gpt-4o", feedback_prompt=None, provider="OpenRouter"):
        self.provider = provider
        self.feedback_model = self._create_chat_model(model, 0)
        self.feedback_prompt_template = feedback_prompt or self.load_prompt("prompts/feedback_prompt.txt")

    def _create_chat_model(self, model, temperature):
        if self.provider == "OpenAI":
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                api_key=os.environ.get("OPENAI_API_KEY")
            )
        else:  # OpenRouter
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                base_url="https://openrouter.ai/api/v1",
                api_key=os.environ.get("OPENROUTER_API_KEY")
            )

    @staticmethod
    def load_prompt(file_path):
        # Get the absolute path to the project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        absolute_path = os.path.join(root_dir, file_path)
        with open(absolute_path, 'r') as file:
            return file.read().strip()

    def run_feedback(self, original_text: str, final_product: str, personality: str) -> str:
        if not original_text or not final_product or not personality:
            raise ValueError("Original text, final product, and personality are all required for feedback.")

        prompt = ChatPromptTemplate.from_template(self.feedback_prompt_template)
        chain = prompt | self.feedback_model
        print("Generating feedback on the original text and final product...")
        response = chain.invoke({
            "personality": personality,
            "original_text": original_text,
            "final_product": final_product
        })
        feedback = response.content.strip()
        return feedback

class WeightClippingAgent:
    def __init__(self, model="openai/gpt-4o", provider="OpenRouter"):
        self.provider = provider
        self.model = self._create_chat_model(model, 0)
        self.prompt_template = self.load_prompt("prompts/weight_clipper_prompt.txt")
    def _create_chat_model(self, model, temperature):
        if self.provider == "OpenAI":
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                api_key=os.environ.get("OPENAI_API_KEY")
            )
        else:  # OpenRouter
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                base_url="https://openrouter.ai/api/v1",
                api_key=os.environ.get("OPENROUTER_API_KEY")
            )
        

    @staticmethod
    def load_prompt(file_path):
        # Get the absolute path to the project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        absolute_path = os.path.join(root_dir, file_path)
        with open(absolute_path, 'r') as file:
            return file.read().strip()

    def clean_prompt(self, system_prompt: str, role: str) -> str:
        prompt = ChatPromptTemplate.from_template(self.prompt_template)
        chain = prompt | self.model
        response = chain.invoke({"role": role, "system_prompt": system_prompt})
        return response.content.strip()

class EvaluatorAgent:
    def __init__(self, model="openai/gpt-4o", provider="OpenRouter"):
        self.provider = provider
        self.model = self._create_chat_model(model, 0)
        self.prompt_template = self.load_prompt("prompts/evaluator_prompt.txt")

    def _create_chat_model(self, model, temperature):
        if self.provider == "OpenAI":
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                api_key=os.environ.get("OPENAI_API_KEY")
            )
        else:  # OpenRouter
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                base_url="https://openrouter.ai/api/v1",
                api_key=os.environ.get("OPENROUTER_API_KEY")
            )

    @staticmethod
    def load_prompt(file_path):
        # Get the absolute path to the project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        absolute_path = os.path.join(root_dir, file_path)
        with open(absolute_path, 'r') as file:
            return file.read().strip()

    def evaluate_podcasts(self, original_text: str, podcast1: str, podcast2: str) -> str:
        prompt = ChatPromptTemplate.from_template(self.prompt_template)
        chain = prompt | self.model
        response = chain.invoke({
            "original_text": original_text,
            "podcast1": podcast1,
            "podcast2": podcast2
        })
        return response.content.strip()

