import os
import zipfile
import shutil
import logging
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                             QLineEdit, QPushButton, QFormLayout, QDialog, QFrame, 
                             QMessageBox, QInputDialog, QFileDialog, QCheckBox)
from PySide6.QtCore import Qt
from services.db_service import DatabaseService
from services.settings_service import SettingsService
from services.llm_service import LLMService
from utils.path_manager import PathManager
from ui.components.toast import ToastNotification

logger = logging.getLogger("app")

class SettingsPage(QWidget):
    def __init__(self, 
                 db_service: DatabaseService, 
                 settings_service: SettingsService, 
                 llm_service: LLMService,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_service
        self.settings = settings_service
        self.llm = llm_service
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("Application Settings")
        header.setObjectName("PageTitle")
        layout.addWidget(header)

        # Splitter Layout (Left Settings Form -> Right Backups/Maintenance)
        main_layout = QHBoxLayout()
        main_layout.setSpacing(25)

        # Left Column: User Profiles & Provider settings
        left_frame = QFrame()
        left_frame.setObjectName("SidebarFrame")
        left_frame.setStyleSheet("border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        form_layout = QFormLayout(left_frame)
        form_layout.setContentsMargins(15, 15, 15, 15)

        # 1. Profile Management
        profile_title = QLabel("User Profile Management")
        profile_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #4F46E5;")
        form_layout.addRow(profile_title)

        self.user_combo = QComboBox()
        self.user_combo.currentIndexChanged.connect(self.on_user_changed)
        
        prof_btns = QHBoxLayout()
        create_prof_btn = QPushButton("New Profile")
        create_prof_btn.setObjectName("SecondaryBtn")
        create_prof_btn.clicked.connect(self.create_profile)
        
        del_prof_btn = QPushButton("Delete Profile")
        del_prof_btn.setObjectName("WarningBtn")
        del_prof_btn.clicked.connect(self.delete_profile)
        
        prof_btns.addWidget(create_prof_btn)
        prof_btns.addWidget(del_prof_btn)
        
        form_layout.addRow("Select Profile:", self.user_combo)
        form_layout.addRow("", prof_btns)
        form_layout.addRow(SpacerFrame())

        # 2. Embedding Model selection
        embed_title = QLabel("RAG Vector Embeddings Model")
        embed_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #4F46E5;")
        form_layout.addRow(embed_title)
        
        self.embed_combo = QComboBox()
        self.embed_combo.addItems(["all-MiniLM-L6-v2", "bge-small", "bge-base", "e5-large"])
        self.embed_combo.currentIndexChanged.connect(self.on_embedding_model_changed)
        form_layout.addRow("Embedding Model:", self.embed_combo)
        form_layout.addRow(SpacerFrame())

        # 3. LLM API Providers Settings
        provider_title = QLabel("AI LLM Provider Credentials")
        provider_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #4F46E5;")
        form_layout.addRow(provider_title)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["openai", "gemini", "claude", "groq", "openrouter", "ollama"])
        self.provider_combo.currentIndexChanged.connect(self.on_provider_selection_changed)
        form_layout.addRow("Select LLM Provider:", self.provider_combo)

        # Dynamic Field Row Inputs
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setPlaceholderText("Paste API key here...")
        self.key_input.textChanged.connect(self.save_provider_credentials)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("e.g. http://localhost:11434")
        self.url_input.textChanged.connect(self.save_provider_credentials)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True) # Allow custom models typing
        self.model_combo.currentTextChanged.connect(self.save_provider_credentials)

        # Connection verify button
        self.verify_btn = QPushButton("Test Connection & Fetch Models")
        self.verify_btn.setObjectName("PrimaryBtn")
        self.verify_btn.clicked.connect(self.verify_connection)

        self.key_label_idx = form_layout.addRow("API Key:", self.key_input)
        self.url_label_idx = form_layout.addRow("Local URL:", self.url_input)
        self.model_label_idx = form_layout.addRow("Select Model:", self.model_combo)
        form_layout.addRow("", self.verify_btn)

        main_layout.addWidget(left_frame, 3)

        # Right Column: UI Preferences & Backups
        right_frame = QFrame()
        right_frame.setObjectName("SidebarFrame")
        right_frame.setStyleSheet("border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(15)

        pref_title = QLabel("App Preferences")
        pref_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #4F46E5;")
        right_layout.addWidget(pref_title)

        # Theme toggle checkbox
        self.theme_checkbox = QCheckBox("Dark Mode Theme")
        self.theme_checkbox.stateChanged.connect(self.toggle_theme)
        right_layout.addWidget(self.theme_checkbox)

        # Portable Mode checkbox
        self.portable_checkbox = QCheckBox("Portable Mode (Local Storage)")
        self.portable_checkbox.stateChanged.connect(self.toggle_portable_mode)
        right_layout.addWidget(self.portable_checkbox)

        right_layout.addWidget(SpacerFrame())

        backup_title = QLabel("Workspace Backup & Recovery")
        backup_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #4F46E5;")
        right_layout.addWidget(backup_title)

        backup_btn = QPushButton("Backup Workspace (.zip)")
        backup_btn.setObjectName("SecondaryBtn")
        backup_btn.clicked.connect(self.backup_workspace)
        right_layout.addWidget(backup_btn)

        restore_btn = QPushButton("Restore Workspace (.zip)")
        restore_btn.setObjectName("SecondaryBtn")
        restore_btn.clicked.connect(self.restore_workspace)
        right_layout.addWidget(restore_btn)

        right_layout.addStretch()
        main_layout.addWidget(right_frame, 2)
        
        layout.addLayout(main_layout)

    def refresh(self) -> None:
        """Populate select selectors from current configuration."""
        user_id = self.settings.get_active_user_id()
        
        # Load user list
        self.user_combo.blockSignals(True)
        self.user_combo.clear()
        users = self.db.get_users()
        active_idx = 0
        for idx, u in enumerate(users):
            self.user_combo.addItem(u["username"], u["id"])
            if u["id"] == user_id:
                active_idx = idx
        self.user_combo.setCurrentIndex(active_idx)
        self.user_combo.blockSignals(False)

        # Load embedding model selector
        self.embed_combo.blockSignals(True)
        model = self.settings.get_embedding_model(user_id)
        self.embed_combo.setCurrentText(model)
        self.embed_combo.blockSignals(False)

        # Load Theme Preferences
        self.theme_checkbox.blockSignals(True)
        self.theme_checkbox.setChecked(self.settings.get_theme() == "dark")
        self.theme_checkbox.blockSignals(False)

        # Load Portable Preference
        self.portable_checkbox.blockSignals(True)
        self.portable_checkbox.setChecked(self.settings.is_portable())
        self.portable_checkbox.blockSignals(False)

        # Load LLM details
        self.provider_combo.blockSignals(True)
        active_prov = self.settings.get_active_provider(user_id)
        prov_idx = self.provider_combo.findText(active_prov)
        if prov_idx >= 0:
            self.provider_combo.setCurrentIndex(prov_idx)
        self.provider_combo.blockSignals(False)
        
        self.on_provider_selection_changed(self.provider_combo.currentIndex())

    def on_user_changed(self, idx: int) -> None:
        if idx < 0:
            return
        user_id = self.user_combo.itemData(idx)
        self.settings.set_active_user_id(user_id)
        
        # Trigger window refreshes for workspace details
        self.refresh()
        if hasattr(self.window(), "refresh_active_page"):
            self.window().refresh_active_page()

    def create_profile(self) -> None:
        username, ok = QInputDialog.getText(self, "New Profile", "Enter profile username:")
        if ok and username.strip():
            user = self.db.create_user(username.strip())
            self.settings.set_active_user_id(user["id"])
            
            # Create a default project for this user profile automatically
            self.db.create_project(user["id"], "My Workspace", "Default workspace for research.")
            ToastNotification(f"Profile '{username}' created!", self.window(), duration=3000, success=True)
            self.refresh()

    def delete_profile(self) -> None:
        user_id = self.settings.get_active_user_id()
        user = self.db.get_user(user_id)
        if not user:
            return
            
        reply = QMessageBox.critical(
            self,
            "Delete Profile",
            f"Are you sure you want to delete profile '{user['username']}'?\nAll projects, uploaded files, and history will be permanently deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_user(user_id)
            self.settings.set_active_user_id("")
            ToastNotification("Profile deleted.", self.window(), duration=3000, success=True)
            self.refresh()
            if hasattr(self.window(), "refresh_active_page"):
                self.window().refresh_active_page()

    def on_embedding_model_changed(self, idx: int) -> None:
        user_id = self.settings.get_active_user_id()
        model_name = self.embed_combo.currentText()
        self.settings.set_embedding_model(user_id, model_name)
        ToastNotification(f"Embedding model changed to: {model_name}", self.window(), duration=3000, success=True)

    def on_provider_selection_changed(self, idx: int) -> None:
        """Toggle input field visibility depending on the active provider."""
        provider = self.provider_combo.currentText()
        user_id = self.settings.get_active_user_id()
        if user_id:
            self.settings.set_active_provider(user_id, provider)
        
        self.key_input.blockSignals(True)
        self.url_input.blockSignals(True)
        self.model_combo.blockSignals(True)

        # Set API key
        self.key_input.setText(self.settings.get_api_key(user_id, provider))
        
        # Populate defaults or saved model name
        saved_model = self.settings.get_provider_model(user_id, provider)
        self.model_combo.clear()
        
        # Hide/Show API key or Local URL fields based on provider type
        if provider == "ollama":
            # Ollama needs Local URL instead of API key
            self.key_input.setVisible(False)
            self.url_input.setVisible(True)
            self.url_input.setText(self.settings.get_ollama_url(user_id))
            
            # Populate standard Ollama models
            self.model_combo.addItems(["llama3", "mistral", "phi3", "gemma", "deepseek-coder"])
        else:
            self.key_input.setVisible(True)
            self.url_input.setVisible(False)
            
            # Populate default provider models list
            defaults = {
                "openai": ["gpt-4o-mini", "gpt-4o", "gpt-4"],
                "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"],
                "claude": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
                "groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "deepseek-r1-distill-llama-70b"],
                "openrouter": ["google/gemini-2.5-flash", "anthropic/claude-3.5-sonnet", "openai/gpt-4o-mini"]
            }
            self.model_combo.addItems(defaults.get(provider, []))

        if saved_model:
            self.model_combo.setCurrentText(saved_model)
        else:
            self.settings.set_provider_model(user_id, provider, self.model_combo.currentText())

        self.key_input.blockSignals(False)
        self.url_input.blockSignals(False)
        self.model_combo.blockSignals(False)

    def save_provider_credentials(self) -> None:
        """Persist changes in inputs directly into settings.json."""
        provider = self.provider_combo.currentText()
        user_id = self.settings.get_active_user_id()
        if not user_id:
            return
            
        if provider == "ollama":
            self.settings.set_ollama_url(user_id, self.url_input.text().strip())
        else:
            self.settings.set_api_key(user_id, provider, self.key_input.text().strip())
            
        self.settings.set_provider_model(user_id, provider, self.model_combo.currentText().strip())

    # --- Auto Model Detection ---
    def verify_connection(self) -> None:
        provider = self.provider_combo.currentText()
        user_id = self.settings.get_active_user_id()
        
        self.verify_btn.setEnabled(False)
        self.verify_btn.setText("Connecting...")
        
        key = self.key_input.text().strip()
        url = self.url_input.text().strip()
        
        # Test connection in-thread (quick check)
        success = self.llm.test_provider_connection(user_id, provider, key, url)
        
        if success:
            # Fetch models list
            models = self.llm.get_models_for_provider(user_id, provider)
            if models:
                self.model_combo.blockSignals(True)
                self.model_combo.clear()
                self.model_combo.addItems(models)
                self.model_combo.blockSignals(False)
                # Keep the current model if it exists in the new list, otherwise fallback to first
                current_model = self.settings.get_provider_model(user_id, provider)
                if current_model and current_model in models:
                    self.model_combo.setCurrentText(current_model)
                else:
                    # Prefer gemini-2.5-flash for Gemini if available, otherwise default to first
                    if provider == "gemini" and "gemini-2.5-flash" in models:
                        best_model = "gemini-2.5-flash"
                    else:
                        best_model = models[0]
                    self.settings.set_provider_model(user_id, provider, best_model)
                    self.model_combo.setCurrentText(best_model)
            
            ToastNotification(f"Success! {provider.upper()} connection verified.", self.window(), duration=3000, success=True)
        else:
            QMessageBox.warning(self, "Connection Test Failed", f"Could not establish connection to {provider.upper()}.\nPlease verify your credentials or URL.")
            
        self.verify_btn.setEnabled(True)
        self.verify_btn.setText("Test Connection & Fetch Models")

    # --- Theme and Preferences toggling ---
    def toggle_theme(self, state: int) -> None:
        theme = "dark" if state == Qt.Checked else "light"
        self.settings.set_theme(theme)
        
        # Apply stylesheet to parent QMainWindow dynamically
        main_win = self.window()
        if hasattr(main_win, "apply_stylesheet"):
            main_win.apply_stylesheet()
        ToastNotification(f"Theme switched to {theme} mode.", self.window(), duration=3000, success=True)

    def toggle_portable_mode(self, state: int) -> None:
        enabled = state == Qt.Checked
        self.settings.set_portable(enabled)
        ToastNotification(f"Portable mode: {'Enabled' if enabled else 'Disabled'}.\nPlease restart application to apply folder routing changes.", self.window(), duration=4000, success=True)

    # --- Backup & Restore (ZIP workspace) ---
    def backup_workspace(self) -> None:
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Backup Research Workspace",
            "ResearchPaperAssistant_Backup.zip",
            "Zip Archive (*.zip)"
        )
        if not save_path:
            return
            
        try:
            # Save current settings before backing up
            self.settings.save_settings()
            
            # Close DB connection temporarily to unlock file
            self.db.close()
            
            base_dir = PathManager.get_base_data_dir()
            
            # Compile zip file
            with zipfile.ZipFile(save_path, "w", zipfile.ZIP_DEFLATED) as zip_f:
                # Walk through base data folder
                for root, dirs, files in os.walk(base_dir):
                    # Skip zipping logs folder
                    if "logs" in root:
                        continue
                    for file in files:
                        filepath = os.path.join(root, file)
                        # Relative path inside zip
                        rel_path = os.path.relpath(filepath, base_dir)
                        zip_f.write(filepath, rel_path)
            
            # Reopen DB connection
            self.db._init_db()
            
            ToastNotification("Workspace backup generated successfully!", self.window(), duration=4000, success=True)
            QMessageBox.information(self, "Backup Success", f"Workspace successfully exported to:\n\n{save_path}")
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            self.db._init_db() # Ensure DB reopens
            QMessageBox.critical(self, "Backup Failed", f"Failed to generate zip backup: {e}")

    def restore_workspace(self) -> None:
        open_path, _ = QFileDialog.getOpenFileName(
            self,
            "Restore Research Workspace",
            "",
            "Zip Archive (*.zip)"
        )
        if not open_path:
            return
            
        reply = QMessageBox.critical(
            self,
            "Restore Confirmation",
            "WARNING: Restoring will overwrite all current papers, database records, and settings.\n\nDo you want to proceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
            
        try:
            # 1. Close DB connection
            self.db.close()
            
            # 2. Extract ZIP to base data directory
            base_dir = PathManager.get_base_data_dir()
            
            # Unpack ZIP
            with zipfile.ZipFile(open_path, "r") as zip_f:
                # Close any active file handlers
                zip_f.extractall(base_dir)

            # 3. Reload settings from file
            self.settings.load_settings()
            
            # 4. Re-initialize database
            self.db._init_db()
            
            ToastNotification("Workspace restored successfully!", self.window(), duration=4000, success=True)
            QMessageBox.information(self, "Restore Success", "Your research workspace was successfully restored.\n\nThe application will now refresh.")
            
            # Refresh window
            if hasattr(self.window(), "refresh_active_page"):
                self.window().refresh_active_page()
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            self.db._init_db() # Ensure DB reopens
            QMessageBox.critical(self, "Restore Failed", f"Failed to unpack zip archive: {e}")

# --- Simple divider decoration ---
class SpacerFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setStyleSheet("background-color: rgba(255,255,255,0.05); margin: 8px 0px;")
