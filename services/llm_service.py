import time
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from providers.openai_provider import OpenAIProvider
from providers.gemini_provider import GeminiProvider
from providers.claude_provider import ClaudeProvider
from providers.groq_provider import GroqProvider
from providers.openrouter_provider import OpenRouterProvider
from providers.ollama_provider import OllamaProvider
from services.db_service import DatabaseService
from services.settings_service import SettingsService

logger = logging.getLogger("app")

class LLMService:
    def __init__(self, db_service: DatabaseService, settings_service: SettingsService):
        self.db = db_service
        self.settings = settings_service
        
        # Instantiate provider registry
        self.providers = {
            "openai": OpenAIProvider(),
            "gemini": GeminiProvider(),
            "claude": ClaudeProvider(),
            "groq": GroqProvider(),
            "openrouter": OpenRouterProvider(),
            "ollama": OllamaProvider()
        }

    # --- Mode System Prompts ---
    ASSISTANT_MODES = {
        "General": (
            "You are an expert academic research assistant. Provide concise, clear, and objective answers. "
            "Always back up your statements with references from the provided context chunks. If you cannot "
            "answer from the context, state it clearly."
        ),
        "Paper Reviewer": (
            "You are an expert peer reviewer for top-tier scientific journals. Critically evaluate the provided research context. "
            "Inspect the methodology, dataset limitations, potential statistical flaws, and experimental rigor. "
            "Highlight strengths, weaknesses, gaps in reasoning, and validity concerns."
        ),
        "Literature Review Assistant": (
            "You are a literature review expert. Your task is to contextualize the provided research papers within the broader scientific "
            "domain. Synthesize trends, relate different ideas, and identify how these papers build upon preceding work."
        ),
        "Thesis Assistant": (
            "You are a academic thesis supervisor. Explain the concepts, findings, and formulas from the papers in clear, "
            "pedagogical terms. Guide the student on how to write about these methods, synthesize definitions, and structure "
            "their own literature draft."
        ),
        "Comparison Expert": (
            "You are a comparative research expert. Focus heavily on comparing and contrasting research problems, methodologies, "
            "datasets, metrics, results, and limitations of the papers. Present trade-offs in structured tabular formats if appropriate."
        )
    }

    # --- Estimated Cost Calculator per 1M tokens ---
    # Prices in USD
    COST_TABLE = {
        "openai": {
            "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
            "gpt-4o": {"prompt": 2.50, "completion": 10.00},
            "gpt-4": {"prompt": 30.00, "completion": 60.00},
            "default": {"prompt": 0.15, "completion": 0.60}
        },
        "gemini": {
            "gemini-2.5-flash": {"prompt": 0.075, "completion": 0.30},
            "gemini-2.5-pro": {"prompt": 1.25, "completion": 5.00},
            "gemini-1.5-flash": {"prompt": 0.075, "completion": 0.30},
            "gemini-1.5-pro": {"prompt": 1.25, "completion": 5.00},
            "default": {"prompt": 0.075, "completion": 0.30}
        },
        "claude": {
            "claude-3-5-sonnet-20241022": {"prompt": 3.00, "completion": 15.00},
            "claude-3-5-haiku-20241022": {"prompt": 0.80, "completion": 4.00},
            "claude-3-opus-20240229": {"prompt": 15.00, "completion": 75.00},
            "default": {"prompt": 3.00, "completion": 15.00}
        },
        "groq": {
            "default": {"prompt": 0.05, "completion": 0.10}
        },
        "openrouter": {
            "default": {"prompt": 2.00, "completion": 8.00}
        },
        "ollama": {
            "default": {"prompt": 0.0, "completion": 0.0}
        }
    }

    def _calculate_cost(self, provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate the estimated API cost of the call."""
        prov_costs = self.COST_TABLE.get(provider, self.COST_TABLE["ollama"])
        model_costs = prov_costs.get(model, prov_costs.get("default", {"prompt": 0.0, "completion": 0.0}))
        
        prompt_cost = (prompt_tokens / 1_000_000) * model_costs["prompt"]
        completion_cost = (completion_tokens / 1_000_000) * model_costs["completion"]
        return prompt_cost + completion_cost

    def generate(self, 
                 user_id: str, 
                 prompt: str, 
                 context_chunks: List[Dict[str, Any]], 
                 history: List[Dict[str, str]], 
                 mode: str = "General",
                 custom_system_prompt: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Gathers context chunks, compresses history if needed, calls active provider, and logs usage benchmark.
        """
        provider_name = self.settings.get_active_provider(user_id)
        model = self.settings.get_provider_model(user_id, provider_name)
        api_key = self.settings.get_api_key(user_id, provider_name)
        
        provider = self.providers.get(provider_name)
        if not provider:
            return f"Provider {provider_name} not implemented.", []

        # Construct System Instruction
        mode_instruction = self.ASSISTANT_MODES.get(mode, self.ASSISTANT_MODES["General"])
        system_instruction = custom_system_prompt if custom_system_prompt else mode_instruction
        
        # Inject RAG chunks if available
        rag_context = ""
        citations = []
        if context_chunks:
            rag_context = "\n=== RETRIEVED RESEARCH PAPERS CONTEXT ===\n"
            for i, chunk in enumerate(context_chunks):
                doc_name = chunk.get("paper_name", "Unknown Paper")
                page_num = chunk.get("page_number", "?")
                score = chunk.get("score", 0.0)
                text = chunk.get("content", "")
                
                rag_context += f"\n[Source {i+1}]: {doc_name} (Page {page_num}, Confidence Score: {score:.4f})\nContent: {text}\n"
                citations.append({
                    "paper_name": doc_name,
                    "page_number": page_num,
                    "similarity_score": score,
                    "snippet": text
                })
            rag_context += "\n=========================================\n"

        full_prompt = prompt
        if rag_context:
            full_prompt = f"{rag_context}\nUser Question: {prompt}\n\nAnswer the question using the context above. If references are helpful, cite them by [Source X]."

        # Memory Compression (Rolling Summary Check)
        # If history is long, compress older messages
        compressed_history = history
        rolling_summary = ""
        if len(history) > 10:
            logger.info("Chat history is long. Triggering rolling memory compression...")
            # We take the first len(history)-4 messages, generate a short summary, and use it
            messages_to_compress = history[:-4]
            latest_messages = history[-4:]
            
            summary_prompt = "Summarize the key topics and facts discussed in this conversation session so far in a single paragraph."
            temp_content, _ = provider.generate_response(
                prompt=summary_prompt,
                system_instruction="You are a context compression utility.",
                history=messages_to_compress,
                model=model,
                api_key=api_key,
                local_url=self.settings.get_ollama_url(user_id) if provider_name == "ollama" else ""
            )
            rolling_summary = f"\n=== SUMMARY OF CONVERSATION SO FAR ===\n{temp_content}\n======================================\n"
            system_instruction = f"{system_instruction}\n{rolling_summary}"
            compressed_history = latest_messages

        # Prepare parameters for Ollama if needed
        extra_args = {}
        if provider_name == "ollama":
            extra_args["local_url"] = self.settings.get_ollama_url(user_id)

        # Call Provider
        content, usage = provider.generate_response(
            prompt=full_prompt,
            system_instruction=system_instruction,
            history=compressed_history,
            model=model,
            api_key=api_key,
            **extra_args
        )

        # Log Cost & Metrics in DB (only if user_id is provided)
        if user_id and usage.get("success", False):
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            cost = self._calculate_cost(provider_name, model, prompt_tokens, completion_tokens)
            
            # Record cost inside usage dict
            usage["cost"] = cost
            self.db.log_api_usage(
                user_id=user_id,
                provider=provider_name,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost
            )
            
        return content, citations

    def get_models_for_provider(self, user_id: str, provider_name: str) -> List[str]:
        """Fetch available models from the provider's API."""
        provider = self.providers.get(provider_name)
        if not provider:
            return []
        
        api_key = self.settings.get_api_key(user_id, provider_name)
        extra_args = {}
        if provider_name == "ollama":
            extra_args["local_url"] = self.settings.get_ollama_url(user_id)
            
        return provider.get_available_models(api_key, **extra_args)

    def test_provider_connection(self, user_id: str, provider_name: str, api_key: str, local_url: str = "") -> bool:
        """Test API credentials."""
        provider = self.providers.get(provider_name)
        if not provider:
            return False
        
        extra_args = {}
        if provider_name == "ollama" and local_url:
            extra_args["local_url"] = local_url
            
        return provider.test_connection(api_key, **extra_args)
