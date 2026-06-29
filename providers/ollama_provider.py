import requests
import time
import logging
from typing import List, Dict, Any, Tuple
from providers.base_provider import BaseLLMProvider

logger = logging.getLogger("app")

class OllamaProvider(BaseLLMProvider):
    def generate_response(self, 
                          prompt: str, 
                          system_instruction: str, 
                          history: List[Dict[str, str]], 
                          model: str, 
                          api_key: str, 
                          **kwargs) -> Tuple[str, Dict[str, Any]]:
        local_url = kwargs.get("local_url", "http://localhost:11434")
        url = f"{local_url.rstrip('/')}/api/chat"
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": model,
            "messages": messages,
            "options": {
                "temperature": kwargs.get("temperature", 0.3)
            },
            "stream": False
        }
        
        start_time = time.time()
        try:
            # Short timeout fallback for local service to keep UI responsive
            res = requests.post(url, json=data, timeout=90)
            latency = time.time() - start_time
            if res.status_code == 200:
                res_data = res.json()
                content = res_data.get("message", {}).get("content", "")
                
                # Ollama returns token count parameters: prompt_eval_count, eval_count
                prompt_tokens = res_data.get("prompt_eval_count", 0)
                completion_tokens = res_data.get("eval_count", 0)
                
                return content, {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "latency": latency,
                    "success": True
                }
            else:
                logger.error(f"Ollama local error {res.status_code}: {res.text}")
                return f"Local Ollama error {res.status_code}: {res.text}", {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "latency": latency,
                    "success": False
                }
        except Exception as e:
            logger.error(f"Ollama local service unreachable: {e}")
            return f"Ollama service unreachable at {local_url}. Make sure it is running locally. Error: {str(e)}", {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "latency": time.time() - start_time,
                "success": False
            }

    def get_available_models(self, api_key: str, **kwargs) -> List[str]:
        local_url = kwargs.get("local_url", "http://localhost:11434")
        url = f"{local_url.rstrip('/')}/api/tags"
        default_models = ["llama3", "mistral", "phi3", "gemma"]
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name") for m in data.get("models", [])]
                return sorted(models) if models else default_models
            return default_models
        except Exception as e:
            logger.error(f"Failed to fetch Ollama local models from {url}: {e}")
            return default_models

    def test_connection(self, api_key: str, **kwargs) -> bool:
        local_url = kwargs.get("local_url", "http://localhost:11434")
        url = f"{local_url.rstrip('/')}/api/tags"
        try:
            res = requests.get(url, timeout=5)
            return res.status_code == 200
        except Exception:
            return False
