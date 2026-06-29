import requests
import time
import logging
from typing import List, Dict, Any, Tuple
from providers.base_provider import BaseLLMProvider

logger = logging.getLogger("app")

class OpenRouterProvider(BaseLLMProvider):
    def generate_response(self, 
                          prompt: str, 
                          system_instruction: str, 
                          history: List[Dict[str, str]], 
                          model: str, 
                          api_key: str, 
                          **kwargs) -> Tuple[str, Dict[str, Any]]:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/google-deepmind/research-paper-assistant",
            "X-Title": "Research Paper Assistant Pro"
        }
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.3)
        }
        
        start_time = time.time()
        try:
            res = requests.post(url, json=data, headers=headers, timeout=60)
            latency = time.time() - start_time
            if res.status_code == 200:
                res_data = res.json()
                content = res_data["choices"][0]["message"]["content"]
                # OpenRouter might not return standard usage structure, so handle key safety
                usage = res_data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                return content, {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "latency": latency,
                    "success": True
                }
            else:
                logger.error(f"OpenRouter API error {res.status_code}: {res.text}")
                return f"Error {res.status_code}: {res.text}", {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "latency": latency,
                    "success": False
                }
        except Exception as e:
            logger.error(f"OpenRouter Network error: {e}")
            return f"Network Error: {str(e)}", {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "latency": time.time() - start_time,
                "success": False
            }

    def get_available_models(self, api_key: str, **kwargs) -> List[str]:
        url = "https://openrouter.ai/api/v1/models"
        default_models = ["google/gemini-2.5-flash", "anthropic/claude-3.5-sonnet", "openai/gpt-4o-mini"]
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                models_data = res.json()
                models = [m["id"] for m in models_data.get("data", [])]
                return sorted(models) if models else default_models
            return default_models
        except Exception as e:
            logger.error(f"Failed to fetch OpenRouter models: {e}")
            return default_models

    def test_connection(self, api_key: str, **kwargs) -> bool:
        # Check connection by querying models with key (OpenRouter allows model list without key, but validation is useful)
        url = "https://openrouter.ai/api/v1/models"
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            res = requests.get(url, headers=headers, timeout=10)
            return res.status_code == 200
        except Exception:
            return False
