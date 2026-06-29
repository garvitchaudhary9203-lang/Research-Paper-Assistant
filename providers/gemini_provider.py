import requests
import time
import logging
from typing import List, Dict, Any, Tuple
from providers.base_provider import BaseLLMProvider

logger = logging.getLogger("app")

class GeminiProvider(BaseLLMProvider):
    def generate_response(self, 
                          prompt: str, 
                          system_instruction: str, 
                          history: List[Dict[str, str]], 
                          model: str, 
                          api_key: str, 
                          **kwargs) -> Tuple[str, Dict[str, Any]]:
        # Ensure model is formatted correctly
        model_name = model
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
            
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={api_key}"
        headers = {
            "Content-Type": "application/json"
        }

        # Build contents structure
        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
            
        # Add current user message
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        data = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.3)
            }
        }

        if system_instruction:
            data["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        start_time = time.time()
        try:
            res = requests.post(url, json=data, headers=headers, timeout=60)
            latency = time.time() - start_time
            if res.status_code == 200:
                res_data = res.json()
                # Parse content
                content = ""
                candidates = res_data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        content = parts[0].get("text", "")
                
                usage = res_data.get("usageMetadata", {})
                prompt_tokens = usage.get("promptTokenCount", 0)
                completion_tokens = usage.get("candidatesTokenCount", 0)
                
                return content, {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "latency": latency,
                    "success": True
                }
            else:
                logger.error(f"Gemini API error {res.status_code}: {res.text}")
                return f"Error {res.status_code}: {res.text}", {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "latency": latency,
                    "success": False
                }
        except Exception as e:
            logger.error(f"Gemini Network error: {e}")
            return f"Network Error: {str(e)}", {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "latency": time.time() - start_time,
                "success": False
            }

    def get_available_models(self, api_key: str, **kwargs) -> List[str]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        default_models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"]
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                models = []
                for m in data.get("models", []):
                    name = m.get("name", "")
                    # Extract the model id, removing the "models/" prefix
                    model_id = name.split("/")[-1] if "/" in name else name
                    # Filter out models that support generation
                    if "generateContent" in m.get("supportedGenerationMethods", []):
                        # Filter to standard gemini models to avoid cluttering dropdown
                        if "gemini" in model_id:
                            models.append(model_id)
                return sorted(models) if models else default_models
            return default_models
        except Exception as e:
            logger.error(f"Failed to fetch Gemini models: {e}")
            return default_models

    def test_connection(self, api_key: str, **kwargs) -> bool:
        # Use a quick model fetch to verify key
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        try:
            res = requests.get(url, timeout=10)
            return res.status_code == 200
        except Exception:
            return False
