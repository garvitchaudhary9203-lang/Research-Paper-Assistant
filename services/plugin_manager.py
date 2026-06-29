import os
import sys
import json
import importlib.util
import logging
from typing import Dict, Any, List

logger = logging.getLogger("app")

class PluginManager:
    def __init__(self, plugins_dir: str, service_registry: Any):
        """
        Manages loading external extensions/plugins dynamically.
        
        Args:
            plugins_dir: Absolute path to the plugins directory.
            service_registry: The main ServiceRegistry instance of the app.
        """
        self.plugins_dir = plugins_dir
        self.registry = service_registry
        self.loaded_plugins: Dict[str, Any] = {}
        os.makedirs(self.plugins_dir, exist_ok=True)

    def load_plugins(self) -> None:
        """Scan the plugins folder and import valid plugins at runtime."""
        if not os.path.exists(self.plugins_dir):
            return

        # Add plugins directory to sys.path so plugins can import relative scripts
        if self.plugins_dir not in sys.path:
            sys.path.insert(0, self.plugins_dir)

        logger.info(f"Scanning plugins in: {self.plugins_dir}...")
        
        try:
            for item in os.listdir(self.plugins_dir):
                item_path = os.path.join(self.plugins_dir, item)
                
                # Check for directories containing a plugin.json
                if os.path.isdir(item_path):
                    plugin_json_path = os.path.join(item_path, "plugin.json")
                    if os.path.exists(plugin_json_path):
                        self._load_from_json(item_path, plugin_json_path)
        except Exception as e:
            logger.error(f"Error during plugin scanning: {e}")

    def _load_from_json(self, dir_path: str, json_path: str) -> None:
        """Load and register a plugin described by a plugin.json file."""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            
            name = meta.get("name")
            entry_point = meta.get("entry_point", "plugin.py")
            entry_path = os.path.join(dir_path, entry_point)
            
            if not name:
                logger.warning(f"Plugin descriptor at {json_path} is missing a 'name' attribute.")
                return

            if not os.path.exists(entry_path):
                logger.warning(f"Entry point '{entry_point}' for plugin '{name}' does not exist at {entry_path}.")
                return

            logger.info(f"Discovered plugin '{name}', version: {meta.get('version', '0.0.1')}. Importing...")
            self._import_module(name, entry_path)
            
        except Exception as e:
            logger.error(f"Failed to read plugin metadata from {json_path}: {e}")

    def _import_module(self, name: str, filepath: str) -> None:
        """Import the Python module and run register_plugin callback."""
        try:
            # Create module spec
            spec = importlib.util.spec_from_file_location(name, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)
                
                # Verify registration hook
                if hasattr(module, "register_plugin"):
                    # Call registration hook, passing the ServiceRegistry instance
                    module.register_plugin(self.registry)
                    self.loaded_plugins[name] = module
                    logger.info(f"Plugin '{name}' loaded and registered successfully.")
                else:
                    logger.warning(f"Plugin '{name}' imported but does not contain a 'register_plugin' hook function.")
            else:
                logger.error(f"Could not build module loader spec for plugin '{name}' at {filepath}")
        except Exception as e:
            logger.error(f"Error importing plugin module '{name}' from {filepath}: {e}")

    def get_loaded_plugins(self) -> List[str]:
        return list(self.loaded_plugins.keys())
