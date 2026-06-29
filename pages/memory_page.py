import logging
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QComboBox, QListWidget, QListWidgetItem, QPushButton, QFrame, QMessageBox)
from PySide6.QtCore import Qt
from services.db_service import DatabaseService
from services.settings_service import SettingsService

logger = logging.getLogger("app")

class MemoryPage(QWidget):
    def __init__(self, db_service: DatabaseService, settings_service: SettingsService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_service
        self.settings = settings_service
        
        self.history_items: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("Research Memory & Logs")
        header.setObjectName("PageTitle")
        layout.addWidget(header)

        # Search and Filter Row
        filter_row = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter memory logs by keyword...")
        self.search_input.textChanged.connect(self.filter_logs)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["All Memory", "Papers Indexed", "Chat Conversations", "Comparative Matrices"])
        self.type_combo.currentIndexChanged.connect(self.load_history_logs)

        filter_row.addWidget(self.search_input, 1)
        filter_row.addWidget(self.type_combo)
        layout.addLayout(filter_row)

        # Logs List Widget
        self.logs_list = QListWidget()
        self.logs_list.setStyleSheet("background-color: #111827; border: 1px solid #1F2937; padding: 5px;")
        self.logs_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.logs_list)

        # Action Buttons
        btn_row = QHBoxLayout()
        self.restore_btn = QPushButton("Restore / Reopen Session")
        self.restore_btn.setObjectName("PrimaryBtn")
        self.restore_btn.clicked.connect(self.restore_selected_item)
        
        self.delete_btn = QPushButton("Delete Record")
        self.delete_btn.setObjectName("WarningBtn")
        self.delete_btn.clicked.connect(self.delete_selected_item)

        btn_row.addWidget(self.restore_btn)
        btn_row.addWidget(self.delete_btn)
        layout.addLayout(btn_row)

    def refresh(self) -> None:
        self.load_history_logs()

    def load_history_logs(self) -> None:
        """Fetch papers, chats, comparisons from DB and compile into history_items."""
        self.logs_list.clear()
        self.history_items.clear()
        
        proj_id = self.settings.get_active_project_id()
        if not proj_id:
            return

        filter_type = self.type_combo.currentText()

        # 1. Fetch Papers
        if filter_type in ("All Memory", "Papers Indexed"):
            papers = self.db.get_papers(proj_id)
            for p in papers:
                self.history_items.append({
                    "id": p["id"],
                    "type": "paper",
                    "label": f"📄 Paper: {p['name']} (Indexed: {p['upload_date'][:10]})",
                    "raw": p
                })

        # 2. Fetch Sessions (Chats)
        if filter_type in ("All Memory", "Chat Conversations"):
            sessions = self.db.get_sessions(proj_id)
            for s in sessions:
                self.history_items.append({
                    "id": s["id"],
                    "type": "chat",
                    "label": f"💬 Chat Session: '{s['name']}' (Last Active: {s['updated_at'][:10]})",
                    "raw": s
                })

        # 3. Fetch Comparisons
        if filter_type in ("All Memory", "Comparative Matrices"):
            comparisons = self.db.get_comparisons(proj_id)
            for c in comparisons:
                count = len(c.get("papers_compared", []))
                self.history_items.append({
                    "id": c["id"],
                    "type": "comparison",
                    "label": f"📊 Comparison: {count} Papers Analyzed (Created: {c['created_at'][:10]})",
                    "raw": c
                })

        # Sort history items by upload/timestamp if available, let's just keep them categorized
        # Let's populate the widget list
        self.filter_logs()

    def filter_logs(self) -> None:
        """Filters list widget based on search input keywords."""
        self.logs_list.clear()
        query = self.search_input.text().strip().lower()
        
        for item in self.history_items:
            if not query or query in item["label"].lower():
                list_item = QListWidgetItem(item["label"])
                list_item.setData(Qt.UserRole, item)
                self.logs_list.addItem(list_item)

    def on_item_double_clicked(self, item: QListWidgetItem) -> None:
        self.restore_selected_item()

    def restore_selected_item(self) -> None:
        """Route to appropriate main application pages based on history item type."""
        selected = self.logs_list.currentItem()
        if not selected:
            return
            
        item_data = selected.data(Qt.UserRole)
        main_win = self.window()
        if not hasattr(main_win, "navigate_to_page"):
            return

        if item_data["type"] == "paper":
            # Navigate to Library and select paper
            main_win.navigate_to_page("Upload Papers") # Or Library
            # Let library page auto select
            library_page = main_win.findChild(QWidget, "LibraryPage")
            if library_page:
                main_win.navigate_to_page("Research Memory") # Wait, let's route to Library
                main_win.navigate_to_page("Upload Papers")
                # Alternatively just navigate to the dashboard/library directly
                
        elif item_data["type"] == "chat":
            # Restore chat session
            self.settings.set_last_session_id(item_data["id"])
            main_win.navigate_to_page("Research Chat")
            
        elif item_data["type"] == "comparison":
            # Reopen comparison
            main_win.navigate_to_page("Paper Comparison")
            comp_page = main_win.findChild(QWidget, "ComparisonPage")
            if comp_page and hasattr(comp_page, "display_comparison"):
                comp_page.active_comparison_record = item_data["raw"]
                
                # Fetch original papers matching compared ids
                proj_id = self.settings.get_active_project_id()
                all_papers = self.db.get_papers(proj_id)
                compared_ids = item_data["raw"].get("papers_compared", [])
                
                comp_page.active_papers = [p for p in all_papers if p["id"] in compared_ids]
                comp_page.display_comparison(item_data["raw"]["comparison_data"])
                
                comp_page.export_report_btn.setEnabled(True)
                comp_page.export_full_project_btn.setEnabled(True)

    def delete_selected_item(self) -> None:
        selected = self.logs_list.currentItem()
        if not selected:
            return
            
        item_data = selected.data(Qt.UserRole)
        reply = QMessageBox.critical(
            self,
            "Delete Record",
            f"Are you sure you want to permanently delete this {item_data['type']} record?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if item_data["type"] == "paper":
                # Call library deletion directly
                self.db.delete_paper(item_data["id"])
                user_id = self.settings.get_active_user_id()
                proj_id = self.settings.get_active_project_id()
                model_name = self.settings.get_embedding_model(user_id)
                self.rag.delete_paper_from_index(user_id, proj_id, item_data["id"], model_name)
                
            elif item_data["type"] == "chat":
                self.db.delete_session(item_data["id"])
                if self.settings.get_last_session_id() == item_data["id"]:
                    self.settings.set_last_session_id("")
                    
            elif item_data["type"] == "comparison":
                self.db.delete_comparison(item_data["id"])
                
            self.load_history_logs()
