import logging
from typing import Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QMessageBox, QFrame
from PySide6.QtCore import Qt
from utils.update_manager import UpdateManager
from ui.components.toast import ToastNotification

logger = logging.getLogger("app")

class AboutPage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("About Research Assistant")
        header.setObjectName("PageTitle")
        layout.addWidget(header)

        # Description Card
        desc_card = QFrame()
        desc_card.setObjectName("MetricCard")
        desc_card.setStyleSheet("border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        
        desc_layout = QVBoxLayout(desc_card)
        desc_layout.setSpacing(10)

        app_title = QLabel("RESEARCH PAPER ASSISTANT PRO")
        app_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4F46E5;")
        desc_layout.addWidget(app_title)

        version_label = QLabel(f"Version: {UpdateManager.CURRENT_VERSION}")
        version_label.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        desc_layout.addWidget(version_label)

        about_text = QTextBrowser()
        about_text.setFrameShape(QFrame.NoFrame)
        about_text.setStyleSheet("background-color: transparent;")
        about_html = """
        <p><b>Research Paper Assistant Pro</b> is an enterprise-grade academic RAG application. 
        It enables researchers, students, and analysts to process multiple PDFs locally, perform Jaccard-filtered semantic searches, 
        conduct side-by-side matrices comparison, track usage billing metrics, and chat with local FAISS vector document databases.</p>
        
        <p><b>Key Capabilities:</b></p>
        <ul>
            <li>Multi-User profiles with isolated credential encryption</li>
            <li>Multi-paper RAG indexing scoped by Project Workspaces</li>
            <li>Interactive spring-embedded Similarity Network Graphs</li>
            <li>Local encrypted API vaults for OpenAI, Gemini, Claude, Groq, OpenRouter, and Ollama</li>
            <li>ReportLab high-fidelity PDF exports (chats, comparisons, executive summaries, and full reports)</li>
            <li>Full Offline mode when combined with Ollama and local embedding downloads</li>
        </ul>
        <hr/>
        <p>Developed as a standalone commercial research utility. Licensed under the MIT License.</p>
        """
        about_text.setHtml(about_html)
        desc_layout.addWidget(about_text)

        # Update button row
        btn_layout = QHBoxLayout()
        self.update_btn = QPushButton("Check for Updates")
        self.update_btn.setObjectName("PrimaryBtn")
        self.update_btn.clicked.connect(self.check_updates)
        btn_layout.addWidget(self.update_btn)
        btn_layout.addStretch()

        desc_layout.addLayout(btn_layout)
        layout.addWidget(desc_card)
        layout.addStretch()

    def check_updates(self) -> None:
        self.update_btn.setEnabled(False)
        self.update_btn.setText("Checking...")
        
        # Call update checker
        result = UpdateManager.check_for_updates()
        
        self.update_btn.setEnabled(True)
        self.update_btn.setText("Check for Updates")

        if result["update_available"]:
            reply = QMessageBox.information(
                self,
                "Update Available!",
                f"A new version of Research Paper Assistant Pro is available: <b>v{result['latest_version']}</b>\n\n"
                f"Release Notes:\n{result['release_notes']}\n\n"
                f"Do you want to download the installer now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes and result["download_url"]:
                # Open download page in default browser
                import webbrowser
                webbrowser.open(result["download_url"])
        else:
            ToastNotification("You are running the latest version of the application.", self.window(), duration=3000, success=True)
            QMessageBox.information(self, "No Updates", f"You are currently running the latest version (v{UpdateManager.CURRENT_VERSION}).")

    def refresh(self) -> None:
        pass
