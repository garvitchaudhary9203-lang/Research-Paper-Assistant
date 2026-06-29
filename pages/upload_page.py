import os
import logging
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QFileDialog, QProgressBar, QListWidget, QListWidgetItem, QMessageBox, QFrame)
from PySide6.QtCore import Qt, QThreadPool
from services.db_service import DatabaseService
from services.settings_service import SettingsService
from services.rag_service import RAGService
from services.llm_service import LLMService
from utils.path_manager import PathManager
from ui.workers import ExtractionWorker, IndexingWorker
from ui.components.toast import ToastNotification

logger = logging.getLogger("app")

class UploadPage(QWidget):
    def __init__(self, 
                 db_service: DatabaseService, 
                 settings_service: SettingsService, 
                 rag_service: RAGService,
                 llm_service: LLMService,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_service
        self.settings = settings_service
        self.rag = rag_service
        self.llm = llm_service
        self.thread_pool = QThreadPool.globalInstance()
        
        self.setAcceptDrops(True)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("Upload Research Papers")
        header.setObjectName("PageTitle")
        layout.addWidget(header)

        # Drop Zone Area
        self.drop_zone = QFrame()
        self.drop_zone.setObjectName("MetricCard")
        self.drop_zone.setStyleSheet("""
            QFrame#MetricCard {
                border: 2px dashed #4F46E5;
                border-radius: 12px;
                background-color: rgba(79, 70, 229, 0.05);
            }
        """)
        self.drop_zone.setFixedHeight(200)
        
        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel("📥")
        icon_label.setStyleSheet("font-size: 40px;")
        drop_layout.addWidget(icon_label, 0, Qt.AlignCenter)
        
        text_label = QLabel("Drag & Drop PDF files here, or click to browse")
        text_label.setStyleSheet("font-size: 14px; color: #9CA3AF; font-weight: 500;")
        drop_layout.addWidget(text_label, 0, Qt.AlignCenter)
        
        browse_btn = QPushButton("Browse Files")
        browse_btn.setObjectName("SecondaryBtn")
        browse_btn.clicked.connect(self.browse_files)
        drop_layout.addWidget(browse_btn, 0, Qt.AlignCenter)
        
        layout.addWidget(self.drop_zone)

        # Progress Section
        progress_header = QLabel("Indexing Queue")
        progress_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #4F46E5;")
        layout.addWidget(progress_header)

        self.queue_list = QListWidget()
        self.queue_list.setSelectionMode(QListWidget.NoSelection)
        self.queue_list.setStyleSheet("background-color: #111827; border: 1px solid #1F2937;")
        layout.addWidget(self.queue_list)

        # Bottom Bar Status
        self.status_bar = QHBoxLayout()
        self.global_progress = QProgressBar()
        self.global_progress.setValue(0)
        self.global_progress.setVisible(False)
        self.status_bar.addWidget(self.global_progress)
        
        layout.addLayout(self.status_bar)

    # --- Drag and Drop Overrides ---
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            # Check if any url is a PDF
            has_pdf = False
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    has_pdf = True
                    break
            if has_pdf:
                event.acceptProposedAction()
                self.drop_zone.setStyleSheet("""
                    QFrame#MetricCard {
                        border: 2px dashed #10B981;
                        background-color: rgba(16, 185, 129, 0.05);
                    }
                """)

    def dragLeaveEvent(self, event) -> None:
        self.drop_zone.setStyleSheet("""
            QFrame#MetricCard {
                border: 2px dashed #4F46E5;
                background-color: rgba(79, 70, 229, 0.05);
            }
        """)

    def dropEvent(self, event) -> None:
        self.dragLeaveEvent(None)
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                files.append(path)
                
        if files:
            self.process_files(files)

    # --- File Browser ---
    def browse_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Research Papers",
            "",
            "PDF Files (*.pdf)"
        )
        if files:
            self.process_files(files)

    # --- Orchestrate Worker Threads ---
    def process_files(self, file_paths: List[str], force: bool = False) -> None:
        user_id = self.settings.get_active_user_id()
        project_id = self.settings.get_active_project_id()
        
        if not user_id or not project_id:
            ToastNotification("Error: Please select a User Profile and Project first in Settings/Library.", self.window(), duration=4000, success=False)
            return

        for filepath in file_paths:
            filename = os.path.basename(filepath)
            
            # Create list item for progress mapping
            list_item = QListWidgetItem(self.queue_list)
            progress_widget = QWidget()
            widget_layout = QHBoxLayout(progress_widget)
            widget_layout.setContentsMargins(10, 5, 10, 5)
            
            name_label = QLabel(filename)
            name_label.setStyleSheet("font-weight: 500;")
            status_label = QLabel("Queued")
            status_label.setStyleSheet("color: #9CA3AF;")
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_bar.setFixedWidth(120)
            
            widget_layout.addWidget(name_label, 1)
            widget_layout.addWidget(status_label)
            widget_layout.addWidget(progress_bar)
            
            list_item.setSizeHint(progress_widget.sizeHint())
            self.queue_list.addItem(list_item)
            self.queue_list.setItemWidget(list_item, progress_widget)
            
            # Spawn extraction runnable
            worker = ExtractionWorker(
                file_path=filepath,
                user_id=user_id,
                project_id=project_id,
                db_service=self.db,
                rag_service=self.rag,
                llm_service=self.llm,
                settings_service=self.settings,
                force_upload=force
            )
            
            # Connect signals
            worker.signals.progress.connect(lambda val, msg, pb=progress_bar, sl=status_label: self.update_status(pb, sl, val, msg))
            worker.signals.error.connect(lambda err_msg, sl=status_label, pb=progress_bar: self.handle_error(sl, pb, err_msg))
            worker.signals.finished.connect(lambda res, item=list_item, pb=progress_bar, sl=status_label: self.start_indexing(res, item, pb, sl))
            worker.signals.duplicate_found.connect(lambda f_name, m_type, p_id, path=filepath: self.handle_duplicate(f_name, m_type, path))
            
            self.thread_pool.start(worker)

    def update_status(self, pb: QProgressBar, sl: QLabel, value: int, msg: str) -> None:
        pb.setValue(value)
        sl.setText(msg)

    def handle_error(self, sl: QLabel, pb: QProgressBar, err: str) -> None:
        sl.setText("Failed")
        sl.setStyleSheet("color: #EF4444;")
        pb.setVisible(False)
        ToastNotification(f"Upload Error: {err}", self.window(), duration=4000, success=False)

    def handle_duplicate(self, filename: str, match_type: str, paper_id: str, filepath: str) -> None:
        reply = QMessageBox.warning(
            self,
            "Duplicate Paper Detected",
            f"The paper '{filename}' matches an existing document in this project by {match_type}.\n\nDo you want to re-upload and overwrite it?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Overwrite by deleting old paper and running the upload with force=True
            self.db.delete_paper(paper_id)
            model_name = self.settings.get_embedding_model(self.settings.get_active_user_id())
            self.rag.delete_paper_from_index(
                user_id=self.settings.get_active_user_id(),
                project_id=self.settings.get_active_project_id(),
                paper_id=paper_id,
                embedding_model_name=model_name
            )
            self.process_files([filepath], force=True)

    def start_indexing(self, res: dict, list_item: QListWidgetItem, pb: QProgressBar, sl: QLabel) -> None:
        """Start embedding generation and FAISS indexing."""
        paper = res["paper"]
        pages_content = res["pages_content"]
        
        user_id = self.settings.get_active_user_id()
        model_name = self.settings.get_embedding_model(user_id)
        
        # Copy file to local uploads directory (for portable/backup mode persistence)
        uploads_dir = PathManager.get_path("uploads")
        dest_path = os.path.join(uploads_dir, paper["id"] + "_" + paper["name"])
        try:
            import shutil
            shutil.copy2(paper["file_path"], dest_path)
            # Update path in DB to internal persistent copy
            self.db.conn.execute("UPDATE papers SET file_path = ? WHERE id = ?;", (dest_path, paper["id"]))
            self.db.conn.commit()
        except Exception as e:
            logger.error(f"Failed to copy paper file to uploads directory: {e}")

        # Spawn Indexer
        idx_worker = IndexingWorker(
            paper=paper,
            pages_content=pages_content,
            embedding_model=model_name,
            rag_service=self.rag,
            db_service=self.db,
            llm_service=self.llm
        )
        
        idx_worker.signals.progress.connect(lambda val, msg: self.update_status(pb, sl, val, msg))
        idx_worker.signals.error.connect(lambda err_msg: self.handle_error(sl, pb, err_msg))
        idx_worker.signals.finished.connect(lambda result: self.finish_indexing(list_item, result))
        
        self.thread_pool.start(idx_worker)

    def finish_indexing(self, list_item: QListWidgetItem, result: dict) -> None:
        # Update queue visual
        progress_widget = self.queue_list.itemWidget(list_item)
        if progress_widget:
            sl = progress_widget.findChild(QLabel, "")
            pb = progress_widget.findChild(QProgressBar, "")
            if sl:
                sl.setText("Indexed")
                sl.setStyleSheet("color: #10B981; font-weight: bold;")
            if pb:
                pb.setVisible(False)
        
        ToastNotification(f"Successfully indexed '{result['paper_name']}'!", self.window(), duration=3000, success=True)
        # Notify dashboard or other pages to update
        if hasattr(self.window(), "refresh_active_page"):
            self.window().refresh_active_page()
