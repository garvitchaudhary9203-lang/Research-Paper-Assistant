import requests
import time
import logging
from typing import List, Dict, Any, Tuple
from providers.base_provider import BaseLLMProvider

logger = logging.getLogger("app")

class ClaudeProvider(BaseLLMProvider):
    def generate_response(self, 
                          prompt: str, 
                          system_instruction: str, 
                          history: List[Dict[str, str]], 
                          model: str, 
                          api_key: str, 
                          **kwargs) -> Tuple[str, Dict[str, Any]]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        # Format history for Anthropic (user & assistant only, no system message)
        messages = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            messages.append({"role": role, "content": msg["content"]})
            
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.3)
        }

        if system_instruction:
            data["system"] = system_instruction

        start_time = time.time()
        try:
            res = requests.post(url, json=data, headers=headers, timeout=60)
            latency = time.time() - start_time
            if res.status_code == 200:
                res_data = res.json()
                # Parse text response
                content_list = res_data.get("content", [])
                content = content_list[0].get("text", "") if content_list else ""
                
                usage = res_data.get("usage", {})
                prompt_tokens = usage.get("input_tokens", 0)
                completion_tokens = usage.get("output_tokens", 0)
                
                return content, {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "latency": latency,
                    "success": True
                }
            else:
                logger.error(f"Claude API error {res.status_code}: {res.text}")
                return f"Error {res.status_code}: {res.text}", {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "latency": latency,
                    "success": False
                }
        except Exception as e:
            logger.error(f"Claude Network error: {e}")
            return f"Network Error: {str(e)}", {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "latency": time.time() - start_time,
                "success": False
            }

    def get_available_models(self, api_key: str, **kwargs) -> List[str]:
        # Anthropic has a /v1/models endpoint now, but it's cleaner to have a solid fallback.
        url = "https://api.anthropic.com/v1/models"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        default_models = ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("id") for m in data.get("data", [])]
                return sorted(models) if models else default_models
            return default_models
        except Exception as e:
            logger.error(f"Failed to fetch Claude models: {e}")
            return default_models

    def test_connection(self, api_key: str, **kwargs) -> bool:
        # Check connection by fetching models or sending empty message.
        # Fetching models is safer as it does not consume tokens.
        url = "https://api.anthropic.com/v1/models"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        try:
            res = requests.get(url, headers=headers, timeout=10)
            return res.status_code == 200
        except Exception:
            return False
