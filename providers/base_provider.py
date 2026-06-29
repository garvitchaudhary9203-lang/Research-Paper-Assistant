from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple

class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_response(self, 
                          prompt: str, 
                          system_instruction: str, 
                          history: List[Dict[str, str]], 
                          model: str, 
                          api_key: str, 
                          **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        Sends a request to the LLM and returns the text response along with usage metadata.
        
        Args:
            prompt: The user query or final input.
            system_instruction: System guidelines/persona.
            history: List of chat messages (e.g. [{"role": "user", "content": "..."}, ...])
            model: The identifier of the selected LLM.
            api_key: Decrypted API key.
            kwargs: Extra parameters (local_url for Ollama, etc.).

        Returns:
            A tuple of:
            - str: The text content of the response.
            - dict: Usage statistics metadata (e.g., {"prompt_tokens": int, "completion_tokens": int, "latency": float, "success": bool})
        """
        pass

    @abstractmethod
    def get_available_models(self, api_key: str, **kwargs) -> List[str]:
        """
        Fetch available models list from the provider API.
        
        Args:
            api_key: Decrypted API key.
            kwargs: Extra parameters.

        Returns:
            List of model ID strings.
        """
        pass

    @abstractmethod
    def test_connection(self, api_key: str, **kwargs) -> bool:
        """
        Test if the API key and connection are valid.

        Args:
            api_key: Decrypted API key.
            kwargs: Extra parameters.

        Returns:
            True if connection succeeds, False otherwise.
        """
        pass
