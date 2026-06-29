import logging
import requests
from typing import Dict, Any

logger = logging.getLogger("app")

class UpdateManager:
    CURRENT_VERSION = "1.0.0"
    UPDATE_URL = "https://api.github.com/repos/google-deepmind/research-paper-assistant/releases/latest"

    @classmethod
    def check_for_updates(cls) -> Dict[str, Any]:
        """
        Check if a newer version of the application is available.
        Returns a dictionary indicating update availability, version, and download link.
        """
        result = {
            "update_available": False,
            "latest_version": cls.CURRENT_VERSION,
            "release_notes": "You are running the latest version.",
            "download_url": ""
        }
        
        try:
            # Under offline Ollama mode or standard execution, handle lookup timeouts gracefully
            res = requests.get(cls.UPDATE_URL, timeout=5)
            if res.status_code == 200:
                data = res.json()
                latest_tag = data.get("tag_name", "").lstrip("v")
                
                if latest_tag and cls._parse_version(latest_tag) > cls._parse_version(cls.CURRENT_VERSION):
                    result["update_available"] = True
                    result["latest_version"] = latest_tag
                    result["release_notes"] = data.get("body", "No release details provided.")
                    result["download_url"] = data.get("html_url", "")
        except Exception as e:
            logger.warning(f"Version update check failed (offline or server unreachable): {e}")
            # Silently return no update available to avoid crashing in offline mode
            
        return result

    @staticmethod
    def _parse_version(version_str: str) -> tuple:
        """Converts version string into integer tuple for comparison (e.g. 1.0.0 -> (1, 0, 0))."""
        parts = []
        for p in version_str.split("."):
            if p.isdigit():
                parts.append(int(p))
            else:
                # Handle alpha/beta tags
                parts.append(0)
        return tuple(parts)
