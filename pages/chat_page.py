import json
import logging
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QComboBox, QTextBrowser, QTextEdit, QListWidget, QListWidgetItem, 
                             QSplitter, QFrame, QDialog, QListWidget, QMessageBox, QInputDialog)
from PySide6.QtCore import Qt
from services.db_service import DatabaseService
from services.settings_service import SettingsService
from services.rag_service import RAGService
from services.llm_service import LLMService
from services.export_service import ExportService
from ui.workers import ChatWorker
from ui.components.toast import ToastNotification

logger = logging.getLogger("app")

class ChatPage(QWidget):
    def __init__(self, 
                 db_service: DatabaseService, 
                 settings_service: SettingsService, 
                 rag_service: RAGService,
                 llm_service: LLMService,
                 export_service: ExportService,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_service
        self.settings = settings_service
        self.rag = rag_service
        self.llm = llm_service
        self.export = export_service
        
        self.active_session_id: Optional[str] = None
        self.selected_papers_filter: Optional[List[str]] = None  # None means chat with all papers
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Main horizontal splitter (Sessions List -> Chat Main Area -> Citations Panel)
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setObjectName("ContentFrame")

        # Left Column: Sessions List Pane
        sessions_frame = QFrame()
        sessions_frame.setObjectName("SidebarFrame")
        sessions_layout = QVBoxLayout(sessions_frame)
        sessions_layout.setContentsMargins(10, 10, 10, 10)
        
        sess_title = QLabel("Research Sessions")
        sess_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #4F46E5;")
        sessions_layout.addWidget(sess_title)
        
        self.sessions_list = QListWidget()
        self.sessions_list.itemClicked.connect(self.on_session_clicked)
        sessions_layout.addWidget(self.sessions_list)

        btn_box = QHBoxLayout()
        new_sess_btn = QPushButton("New Chat")
        new_sess_btn.setObjectName("PrimaryBtn")
        new_sess_btn.clicked.connect(self.create_new_session)
        
        del_sess_btn = QPushButton("Delete")
        del_sess_btn.setObjectName("WarningBtn")
        del_sess_btn.clicked.connect(self.delete_session)

        btn_box.addWidget(new_sess_btn)
        btn_box.addWidget(del_sess_btn)
        sessions_layout.addLayout(btn_box)
        
        self.main_splitter.addWidget(sessions_frame)

        # Center Column: Chat Bubble Area
        chat_frame = QFrame()
        chat_layout = QVBoxLayout(chat_frame)
        chat_layout.setContentsMargins(15, 15, 15, 15)
        chat_layout.setSpacing(10)

        # Chat Control Panel (Mode Selection & Paper Targeting)
        controls_bar = QHBoxLayout()
        
        mode_label = QLabel("Assistant Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["General", "Paper Reviewer", "Literature Review Assistant", "Thesis Assistant", "Comparison Expert"])
        
        self.paper_select_btn = QPushButton("Scope: All Papers")
        self.paper_select_btn.setObjectName("SecondaryBtn")
        self.paper_select_btn.clicked.connect(self.open_paper_scope_dialog)
        
        export_btn = QPushButton("Export Transcript")
        export_btn.setObjectName("SecondaryBtn")
        export_btn.clicked.connect(self.export_chat_transcript)

        controls_bar.addWidget(mode_label)
        controls_bar.addWidget(self.mode_combo, 1)
        controls_bar.addWidget(self.paper_select_btn)
        controls_bar.addWidget(export_btn)
        chat_layout.addLayout(controls_bar)

        # Chat Dialog Viewer
        self.chat_display = QTextBrowser()
        self.chat_display.setStyleSheet("background-color: #111827; border: 1px solid #1F2937;")
        self.chat_display.setOpenExternalLinks(True)
        chat_layout.addWidget(self.chat_display)

        # Input Box
        input_bar = QHBoxLayout()
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Ask a question about the uploaded papers (Press Ctrl+Enter to send)...")
        self.message_input.setFixedHeight(50)
        self.message_input.installEventFilter(self) # Catch Enter vs Shift-Enter keys
        
        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("PrimaryBtn")
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setFixedHeight(50)

        input_bar.addWidget(self.message_input, 1)
        input_bar.addWidget(self.send_btn)
        chat_layout.addLayout(input_bar)

        self.main_splitter.addWidget(chat_frame)

        # Right Column: Source Citations Drawer
        cite_frame = QFrame()
        cite_frame.setObjectName("SidebarFrame")
        cite_layout = QVBoxLayout(cite_frame)
        cite_layout.setContentsMargins(12, 12, 12, 12)
        
        cite_title = QLabel("Source Attributions")
        cite_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #4F46E5;")
        cite_layout.addWidget(cite_title)
        
        self.citations_list = QListWidget()
        self.citations_list.setStyleSheet("background-color: #111827; border: 1px solid #1F2937;")
        self.citations_list.itemClicked.connect(self.on_citation_clicked)
        cite_layout.addWidget(self.citations_list)

        self.citation_detail = QTextBrowser()
        self.citation_detail.setFixedHeight(180)
        cite_layout.addWidget(self.citation_detail)

        self.main_splitter.addWidget(cite_frame)

        # Adjust default panel sizes
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 5)
        self.main_splitter.setStretchFactor(2, 3)
        
        main_layout.addWidget(self.main_splitter)

    def eventFilter(self, obj, event) -> bool:
        """Capture Ctrl+Enter in text edit input."""
        from PySide6.QtGui import QKeyEvent
        if obj is self.message_input and event.type() == event.Type.KeyPress:
            key_event = QKeyEvent(event)
            if key_event.key() == Qt.Key_Return:
                if key_event.modifiers() & Qt.ControlModifier:
                    self.send_message()
                    return True
        return super().eventFilter(obj, event)

    def refresh(self) -> None:
        """Refresh conversations history log and select last session if available."""
        project_id = self.settings.get_active_project_id()
        if not project_id:
            return
            
        self.sessions_list.clear()
        sessions = self.db.get_sessions(project_id)
        
        active_idx = -1
        last_session_id = self.settings.get_last_session_id()

        for idx, s in enumerate(sessions):
            item = QListWidgetItem(s["name"])
            item.setData(Qt.UserRole, s["id"])
            self.sessions_list.addItem(item)
            
            if s["id"] == last_session_id:
                active_idx = idx

        # Auto-select the last active session
        if active_idx >= 0:
            self.sessions_list.setCurrentRow(active_idx)
            self.active_session_id = last_session_id
            self.load_active_session()
        elif sessions:
            self.sessions_list.setCurrentRow(0)
            self.active_session_id = sessions[0]["id"]
            self.settings.set_last_session_id(self.active_session_id)
            self.load_active_session()
        else:
            self.active_session_id = None
            self.chat_display.clear()
            self.citations_list.clear()
            self.citation_detail.clear()

        # Reset papers filter
        self.selected_papers_filter = None
        self.paper_select_btn.setText("Scope: All Papers")

    def create_new_session(self) -> None:
        name, ok = QInputDialog.getText(self, "New Chat Session", "Enter session name:")
        if ok and name.strip():
            user_id = self.settings.get_active_user_id()
            project_id = self.settings.get_active_project_id()
            sess = self.db.create_session(user_id, project_id, name.strip())
            
            self.settings.set_last_session_id(sess["id"])
            ToastNotification(f"Created chat session '{name}'", self.window(), duration=3000, success=True)
            self.refresh()

    def rename_session(self) -> None:
        if not self.active_session_id:
            return
        sess = self.db.get_session(self.active_session_id)
        if not sess:
            return
        name, ok = QInputDialog.getText(self, "Rename Session", "Enter new session name:", QLineEdit.Normal, sess["name"])
        if ok and name.strip():
            self.db.rename_session(self.active_session_id, name.strip())
            self.refresh()

    def delete_session(self) -> None:
        if not self.active_session_id:
            return
        reply = QMessageBox.question(
            self,
            "Delete Session",
            "Are you sure you want to delete this chat session and its transcripts?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_session(self.active_session_id)
            self.settings.set_last_session_id("")
            ToastNotification("Session deleted.", self.window(), duration=3000, success=True)
            self.refresh()

    def on_session_clicked(self, item: QListWidgetItem) -> None:
        self.active_session_id = item.data(Qt.UserRole)
        self.settings.set_last_session_id(self.active_session_id)
        self.load_active_session()

    def load_active_session(self) -> None:
        """Display chat history bubbles and clear citation sideboards."""
        self.chat_display.clear()
        self.citations_list.clear()
        self.citation_detail.clear()
        
        if not self.active_session_id:
            return
            
        history = self.db.get_chat_history(self.active_session_id)
        html = ""
        for msg in history:
            role = msg["role"]
            content = msg["content"]
            
            # Format text as clean HTML
            # Convert basic markdown linebreaks and code styling
            formatted = content.replace("\n", "<br/>")
            # Highlight bold sections
            formatted = formatted.replace("**", "<b>", 1).replace("**", "</b>", 1)
            
            if role == "user":
                html += f"""
                <div style="margin: 10px 0px; text-align: right;">
                    <div style="display: inline-block; background-color: #374151; color: #FFFFFF; border-radius: 12px; padding: 10px 14px; text-align: left; max-width: 75%;">
                        {formatted}
                    </div>
                </div>
                """
            else:
                html += f"""
                <div style="margin: 10px 0px; text-align: left;">
                    <div style="display: inline-block; background-color: #1F2937; color: #F3F4F6; border-radius: 12px; border: 1px solid #374151; padding: 10px 14px; max-width: 75%;">
                        <span style="color: #4F46E5; font-weight: bold; font-size: 11px;">ASSISTANT:</span><br/>
                        {formatted}
                    </div>
                </div>
                """
        self.chat_display.setHtml(html)
        
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())

        # If last assistant message contains citations, populate them
        assistant_msgs = [m for m in history if m["role"] == "assistant"]
        if assistant_msgs:
            last_msg = assistant_msgs[-1]
            self.populate_citations(last_msg.get("citations_json", "[]"))

    # --- Scope Selector (Subset RAG Retrieval) ---
    def open_paper_scope_dialog(self) -> None:
        proj_id = self.settings.get_active_project_id()
        if not proj_id:
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Targeted Papers")
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        label = QLabel("Choose papers to focus vector search retrieval:")
        layout.addWidget(label)
        
        list_widget = QListWidget()
        papers = self.db.get_papers(proj_id)
        
        # Populate checkboxes
        for p in papers:
            item = QListWidgetItem(p["name"])
            item.setData(Qt.UserRole, p["id"])
            # Set checkbox
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            # Check if it was previously checked
            if self.selected_papers_filter and p["id"] in self.selected_papers_filter:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            list_widget.addItem(item)
            
        layout.addWidget(list_widget)
        
        btn_box = QHBoxLayout()
        ok_btn = QPushButton("Apply Filter")
        ok_btn.setObjectName("PrimaryBtn")
        ok_btn.clicked.connect(dialog.accept)
        clear_btn = QPushButton("Reset All")
        clear_btn.setObjectName("SecondaryBtn")
        clear_btn.clicked.connect(lambda: [list_widget.item(i).setCheckState(Qt.Unchecked) for i in range(list_widget.count())])
        
        btn_box.addWidget(ok_btn)
        btn_box.addWidget(clear_btn)
        layout.addLayout(btn_box)
        
        if dialog.exec() == QDialog.Accepted:
            selected_ids = []
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    selected_ids.append(item.data(Qt.UserRole))
            
            if selected_ids:
                self.selected_papers_filter = selected_ids
                self.paper_select_btn.setText(f"Scope: {len(selected_ids)} Target Papers")
                ToastNotification(f"Retriever set to search {len(selected_ids)} selected papers.", self.window(), duration=3000, success=True)
            else:
                self.selected_papers_filter = None
                self.paper_select_btn.setText("Scope: All Papers")
                ToastNotification("Retriever set to search all project papers.", self.window(), duration=3000, success=True)

    # --- Dispatch Chat Requests ---
    def send_message(self) -> None:
        user_id = self.settings.get_active_user_id()
        project_id = self.settings.get_active_project_id()
        
        if not self.active_session_id:
            ToastNotification("Error: Please select or create a Chat Session first.", self.window(), duration=3000, success=False)
            return
            
        text = self.message_input.toPlainText().strip()
        if not text:
            return
            
        self.message_input.clear()
        
        # Save user message to database
        self.db.save_message(self.active_session_id, "user", text)
        self.load_active_session()
        
        # Append thinking spacer in viewer
        current_html = self.chat_display.toHtml()
        thinking_html = current_html + """
        <div id="thinking-msg" style="margin: 10px 0px; text-align: left;">
            <div style="display: inline-block; background-color: #1F2937; color: #9CA3AF; border-radius: 12px; padding: 10px 14px;">
                Assistant is thinking...
            </div>
        </div>
        """
        self.chat_display.setHtml(thinking_html)
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
        
        # Set controls disabled while processing
        self.send_btn.setEnabled(False)
        self.message_input.setEnabled(False)

        # Retrieve settings parameters
        model_name = self.settings.get_embedding_model(user_id)
        mode = self.mode_combo.currentText()
        history = self.db.get_chat_history(self.active_session_id)[:-1] # Exclude user's latest query
        
        # Spawn async ChatWorker QThread
        self.chat_thread = ChatWorker(
            user_id=user_id,
            project_id=project_id,
            prompt=text,
            embedding_model=model_name,
            history=history,
            mode=mode,
            paper_ids=self.selected_papers_filter,
            rag_service=self.rag,
            llm_service=self.llm
        )
        
        self.chat_thread.finished.connect(self.on_chat_finished)
        self.chat_thread.error.connect(self.on_chat_error)
        self.chat_thread.start()

    def on_chat_finished(self, response: str, citations: list) -> None:
        self.send_btn.setEnabled(True)
        self.message_input.setEnabled(True)
        self.message_input.setFocus()
        
        # Save response in database
        self.db.save_message(
            session_id=self.active_session_id,
            role="assistant",
            content=response,
            citations_json=json.dumps(citations)
        )
        self.load_active_session()

    def on_chat_error(self, err_msg: str) -> None:
        self.send_btn.setEnabled(True)
        self.message_input.setEnabled(True)
        
        # Remove thinking indicator
        self.load_active_session()
        
        # Alert warning dialog
        QMessageBox.warning(self, "AI Request Failed", f"An error occurred while generating a response:\n\n{err_msg}")

    # --- Citation Viewings ---
    def populate_citations(self, citations_json_str: str) -> None:
        self.citations_list.clear()
        self.citation_detail.clear()
        
        try:
            citations = json.loads(citations_json_str)
            for idx, cit in enumerate(citations):
                label = f"[{idx+1}] {cit.get('paper_name')} (p.{cit.get('page_number')})"
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, cit)
                self.citations_list.addItem(item)
        except Exception:
            pass

    def on_citation_clicked(self, item: QListWidgetItem) -> None:
        cit = item.data(Qt.UserRole)
        if not cit:
            return
            
        score = cit.get("similarity_score", 0.0)
        html = f"""
        <b>Document:</b> {cit.get('paper_name')}<br/>
        <b>Page Number:</b> {cit.get('page_number')}<br/>
        <b>Vector Confidence Similarity:</b> {score:.4f}<hr/>
        <i>Snippet:</i><br/>
        "{cit.get('snippet')}"
        """
        self.citation_detail.setHtml(html)

    # --- Export ---
    def export_chat_transcript(self) -> None:
        if not self.active_session_id:
            return
        sess = self.db.get_session(self.active_session_id)
        if not sess:
            return
            
        history = self.db.get_chat_history(self.active_session_id)
        if not history:
            ToastNotification("Warning: No chat history to export.", self.window(), duration=3000, success=False)
            return

        filename = f"chat_{self.active_session_id[:8]}.pdf"
        try:
            file_path = self.export.export_chat_pdf(sess["name"], history, filename)
            ToastNotification(f"Transcript exported as PDF to exports/ folder!", self.window(), duration=4000, success=True)
            
            # Show file path details
            QMessageBox.information(self, "Export Successful", f"Chat transcript exported to:\n\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Failed to export chat transcript:\n\n{e}")
