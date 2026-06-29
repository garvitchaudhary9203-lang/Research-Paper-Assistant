import sys
# Shiboken PySide6 / six.moves import hook crash workaround
try:
    import six
    import six.moves
except ImportError:
    pass

import os
import logging
import datetime
import traceback
from PySide6.QtWidgets import QApplication

from utils.path_manager import PathManager
from services.db_service import DatabaseService
from services.settings_service import SettingsService
from services.rag_service import RAGService
from services.llm_service import LLMService
from services.export_service import ExportService
from services.plugin_manager import PluginManager
from ui.main_window import MainWindow

# Global exception handler hook to prevent silent crashes and record stacktraces
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
        
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.critical(f"Unhandled Exception: {error_msg}")
    
    # Show user-friendly critical messagebox if app was running
    try:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "Application Error",
            f"Research Paper Assistant Pro encountered an unexpected error:\n\n{exc_value}\n\n"
            f"Details have been written to the logs folder (logs/app.log)."
        )
    except Exception:
        pass
    
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

# Set custom exception hook
sys.excepthook = handle_exception

def bootstrap_application() -> None:
    # 1. Initialize PathManager to determine storage directories (portable vs localappdata)
    PathManager.initialize()
    
    # Get directories
    logs_dir = PathManager.get_path("logs")
    db_dir = PathManager.get_path("database")
    settings_dir = PathManager.get_path("settings")
    vector_db_dir = PathManager.get_path("vector_db")
    exports_dir = PathManager.get_path("exports")
    plugins_dir = os.path.join(PathManager.get_app_dir(), "plugins")
    
    # 2. Setup Logging to logs/app.log
    log_file = os.path.join(logs_dir, "app.log")
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] (%(filename)s:%(lineno)d) %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("app")
    logger.info("=" * 60)
    logger.info(f"Research Paper Assistant Pro Bootstrapping at {datetime.datetime.now()}")
    logger.info(f"Portable Mode: {PathManager.is_portable()}")
    logger.info(f"Data Directory: {PathManager.get_base_data_dir()}")
    
    # 3. Instantiate Service Registry (Dependency Injection)
    logger.info("Initializing services...")
    settings_service = SettingsService(settings_dir)
    db_service = DatabaseService(db_dir)
    rag_service = RAGService(vector_db_dir)
    llm_service = LLMService(db_service, settings_service)
    export_service = ExportService(exports_dir)
    
    # Bundle services
    services = {
        "settings": settings_service,
        "db": db_service,
        "rag": rag_service,
        "llm": llm_service,
        "export": export_service
    }
    
    # 4. Load Dynamic Plugins
    plugin_manager = PluginManager(plugins_dir, services)
    plugin_manager.load_plugins()
    services["plugins"] = plugin_manager
    
    # 5. Boot QEventLoop
    logger.info("Initializing UI Main Window...")
    app = QApplication(sys.argv)
    
    # Standard application metadata
    app.setApplicationName("ResearchPaperAssistantPro")
    app.setOrganizationName("GoogleDeepMind")
    app.setOrganizationDomain("google.com")
    
    window = MainWindow(services)
    window.show()
    
    logger.info("Qt Event Loop running.")
    sys.exit(app.exec())

if __name__ == "__main__":
    bootstrap_application()
