import os
import json
import logging
from typing import Dict, Any, Optional
from utils.path_manager import PathManager
from utils.crypto_helper import CryptoHelper

logger = logging.getLogger("app")

class SettingsService:
    def __init__(self, settings_dir: str):
        self.settings_path = os.path.join(settings_dir, "settings.json")
        self.data: Dict[str, Any] = {}
        self.load_settings()

    def load_settings(self) -> None:
        """Load settings from settings.json or initialize with defaults."""
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read settings file: {e}")
                self._initialize_defaults()
        else:
            self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Sets default settings."""
        self.data = {
            "portable": PathManager.is_portable(),
            "theme": "dark",
            "active_user_id": "",
            "active_project_id": "",
            "last_session_id": "",
            "last_page": "Dashboard",
            "users": {}
        }
        self.save_settings()

    def save_settings(self) -> None:
        """Persist settings dict to settings.json file."""
        try:
            # Sync the portable flag with the PathManager state
            self.data["portable"] = PathManager.is_portable()
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to write settings file: {e}")

    # --- Portable Toggle ---
    def set_portable(self, enabled: bool) -> None:
        """Toggle portable mode and save setting."""
        PathManager.set_portable(enabled)
        self.data["portable"] = enabled
        self.save_settings()

    def is_portable(self) -> bool:
        return self.data.get("portable", False)

    # --- Theme ---
    def get_theme(self) -> str:
        return self.data.get("theme", "dark")

    def set_theme(self, theme: str) -> None:
        self.data["theme"] = theme
        self.save_settings()

    # --- Session Recovery / UI State ---
    def get_last_page(self) -> str:
        return self.data.get("last_page", "Dashboard")

    def set_last_page(self, page_name: str) -> None:
        self.data["last_page"] = page_name
        self.save_settings()

    def get_last_session_id(self) -> str:
        return self.data.get("last_session_id", "")

    def set_last_session_id(self, session_id: str) -> None:
        self.data["last_session_id"] = session_id
        self.save_settings()

    def get_active_user_id(self) -> str:
        return self.data.get("active_user_id", "")

    def set_active_user_id(self, user_id: str) -> None:
        self.data["active_user_id"] = user_id
        self.save_settings()

    def get_active_project_id(self) -> str:
        return self.data.get("active_project_id", "")

    def set_active_project_id(self, project_id: str) -> None:
        self.data["active_project_id"] = project_id
        self.save_settings()

    # --- User Specific Configurations ---
    def _ensure_user_section(self, user_id: str) -> None:
        if "users" not in self.data:
            self.data["users"] = {}
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {
                "active_provider": "openai",
                "embedding_model": "all-MiniLM-L6-v2",
                "providers": {
                    "openai": {"api_key_encrypted": "", "model": "gpt-4o-mini"},
                    "gemini": {"api_key_encrypted": "", "model": "gemini-2.5-flash"},
                    "claude": {"api_key_encrypted": "", "model": "claude-3-5-sonnet-20241022"},
                    "groq": {"api_key_encrypted": "", "model": "llama-3.3-70b-versatile"},
                    "openrouter": {"api_key_encrypted": "", "model": "google/gemini-2.5-flash"},
                    "ollama": {"api_key_encrypted": "", "local_url": "http://localhost:11434", "model": "llama3"}
                }
            }

    def get_active_provider(self, user_id: str) -> str:
        if not user_id:
            return "openai"
        self._ensure_user_section(user_id)
        return self.data["users"][user_id].get("active_provider", "openai")

    def set_active_provider(self, user_id: str, provider: str) -> None:
        if not user_id:
            return
        self._ensure_user_section(user_id)
        self.data["users"][user_id]["active_provider"] = provider
        self.save_settings()

    def get_embedding_model(self, user_id: str) -> str:
        if not user_id:
            return "all-MiniLM-L6-v2"
        self._ensure_user_section(user_id)
        return self.data["users"][user_id].get("embedding_model", "all-MiniLM-L6-v2")

    def set_embedding_model(self, user_id: str, model_name: str) -> None:
        if not user_id:
            return
        self._ensure_user_section(user_id)
        self.data["users"][user_id]["embedding_model"] = model_name
        self.save_settings()

    def get_encrypted_api_key(self, user_id: str, provider: str) -> str:
        if not user_id:
            return ""
        self._ensure_user_section(user_id)
        prov_dict = self.data["users"][user_id]["providers"].get(provider, {})
        return prov_dict.get("api_key_encrypted", "")

    def get_api_key(self, user_id: str, provider: str) -> str:
        """Retrieves and decrypts the API key for a provider."""
        enc_key = self.get_encrypted_api_key(user_id, provider)
        if not enc_key:
            return ""
        return CryptoHelper.decrypt(enc_key)

    def set_api_key(self, user_id: str, provider: str, raw_key: str) -> None:
        """Encrypts and stores the API key for a provider."""
        if not user_id:
            return
        self._ensure_user_section(user_id)
        encrypted_key = CryptoHelper.encrypt(raw_key)
        self.data["users"][user_id]["providers"][provider]["api_key_encrypted"] = encrypted_key
        self.save_settings()

    def get_provider_model(self, user_id: str, provider: str) -> str:
        if not user_id:
            return ""
        self._ensure_user_section(user_id)
        return self.data["users"][user_id]["providers"].get(provider, {}).get("model", "")

    def set_provider_model(self, user_id: str, provider: str, model: str) -> None:
        if not user_id:
            return
        self._ensure_user_section(user_id)
        self.data["users"][user_id]["providers"][provider]["model"] = model
        self.save_settings()

    def get_ollama_url(self, user_id: str) -> str:
        if not user_id:
            return "http://localhost:11434"
        self._ensure_user_section(user_id)
        return self.data["users"][user_id]["providers"].get("ollama", {}).get("local_url", "http://localhost:11434")

    def set_ollama_url(self, user_id: str, url: str) -> None:
        if not user_id:
            return
        self._ensure_user_section(user_id)
        self.data["users"][user_id]["providers"]["ollama"]["local_url"] = url
        self.save_settings()
