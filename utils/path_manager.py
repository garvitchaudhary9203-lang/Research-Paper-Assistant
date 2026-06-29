import os
import sys

class PathManager:
    _portable = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize the PathManager and detect if portable mode is active."""
        app_dir = cls.get_app_dir()
        portable_file = os.path.join(app_dir, "portable.txt")
        cls._portable = os.path.exists(portable_file)

    @classmethod
    def get_app_dir(cls) -> str:
        """Returns the directory containing the main.py or the compiled executable."""
        if getattr(sys, 'frozen', False):
            # Bundled executable
            return os.path.dirname(sys.executable)
        else:
            # Python script (root directory is the parent of utils/)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.dirname(current_dir)

    @classmethod
    def set_portable(cls, enabled: bool) -> None:
        """Enable or disable portable mode by creating/deleting a marker file."""
        cls._portable = enabled
        app_dir = cls.get_app_dir()
        portable_file = os.path.join(app_dir, "portable.txt")
        if enabled:
            try:
                with open(portable_file, "w") as f:
                    f.write("portable")
            except Exception:
                pass
        else:
            if os.path.exists(portable_file):
                try:
                    os.remove(portable_file)
                except Exception:
                    pass

    @classmethod
    def is_portable(cls) -> bool:
        """Check if portable mode is active."""
        return cls._portable

    @classmethod
    def get_base_data_dir(cls) -> str:
        """Get the base data directory (root app directory or APPDATA)."""
        if cls.is_portable():
            return cls.get_app_dir()
        else:
            appdata = os.environ.get("LOCALAPPDATA")
            if not appdata:
                appdata = os.path.expanduser("~")
            base_dir = os.path.join(appdata, "ResearchPaperAssistantPro")
            os.makedirs(base_dir, exist_ok=True)
            return base_dir

    @classmethod
    def get_path(cls, folder_name: str) -> str:
        """Get the absolute path of a sub-folder and ensure it exists."""
        base_dir = cls.get_base_data_dir()
        target_dir = os.path.join(base_dir, folder_name)
        os.makedirs(target_dir, exist_ok=True)
        return target_dir
