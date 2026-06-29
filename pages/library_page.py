import json
import logging
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QLineEdit, QCheckBox, QDialog, QFormLayout, QTextBrowser, 
                             QSplitter, QFrame, QApplication, QMessageBox, QInputDialog)
from PySide6.QtCore import Qt
from services.db_service import DatabaseService
from services.settings_service import SettingsService
from services.rag_service import RAGService
from utils.citations import CitationsGenerator
from ui.components.toast import ToastNotification

logger = logging.getLogger("app")

class LibraryPage(QWidget):
    def __init__(self, 
                 db_service: DatabaseService, 
                 settings_service: SettingsService, 
                 rag_service: RAGService,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_service
        self.settings = settings_service
        self.rag = rag_service
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. Top Controls Bar: Projects Selection & Smart Collections
        top_bar = QHBoxLayout()
        
        # Project Selector
        project_label = QLabel("Active Project:")
        project_label.setStyleSheet("font-weight: bold;")
        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        
        add_project_btn = QPushButton("New Project")
        add_project_btn.setObjectName("PrimaryBtn")
        add_project_btn.clicked.connect(self.create_project)
        
        del_project_btn = QPushButton("Delete")
        del_project_btn.setObjectName("WarningBtn")
        del_project_btn.clicked.connect(self.delete_project)

        top_bar.addWidget(project_label)
        top_bar.addWidget(self.project_combo, 1)
        top_bar.addWidget(add_project_btn)
        top_bar.addWidget(del_project_btn)
        
        main_layout.addLayout(top_bar)

        # Smart Collections Bar
        col_bar = QHBoxLayout()
        col_label = QLabel("Collection:")
        col_label.setStyleSheet("font-weight: bold;")
        self.col_combo = QComboBox()
        self.col_combo.currentIndexChanged.connect(self.on_collection_changed)
        
        add_col_btn = QPushButton("New Smart Collection")
        add_col_btn.setObjectName("SecondaryBtn")
        add_col_btn.clicked.connect(self.create_smart_collection)
        
        top_bar.addWidget(col_label)
        top_bar.addWidget(self.col_combo, 1)
        top_bar.addWidget(add_col_btn)

        # 2. Search Area
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search papers or semantic passages...")
        self.search_input.returnPressed.connect(self.run_search)
        
        self.semantic_checkbox = QCheckBox("Semantic Vector Search")
        self.semantic_checkbox.setChecked(True)
        
        search_btn = QPushButton("Search")
        search_btn.setObjectName("PrimaryBtn")
        search_btn.clicked.connect(self.run_search)

        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.semantic_checkbox)
        search_layout.addWidget(search_btn)
        main_layout.addLayout(search_layout)

        # 3. Main Splitter Layout (Table vs Meta-Drawer)
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel: Table or Search Passages List
        self.table_frame = QFrame()
        self.table_layout = QVBoxLayout(self.table_frame)
        self.table_layout.setContentsMargins(0, 0, 0, 0)
        
        self.papers_table = QTableWidget(0, 5)
        self.papers_table.setHorizontalHeaderLabels(["Filename", "Title", "Authors", "Year", "Action"])
        self.papers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.papers_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.papers_table.setSelectionMode(QTableWidget.SingleSelection)
        self.papers_table.itemSelectionChanged.connect(self.on_selection_changed)
        
        self.table_layout.addWidget(self.papers_table)
        
        # Semantic search results display (initially hidden)
        self.search_results_browser = QTextBrowser()
        self.search_results_browser.setVisible(False)
        self.table_layout.addWidget(self.search_results_browser)

        self.splitter.addWidget(self.table_frame)

        # Right Panel: Paper Details Drawer (collapsible)
        self.drawer_frame = QFrame()
        self.drawer_frame.setObjectName("SidebarFrame")
        self.drawer_frame.setStyleSheet("border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        
        drawer_layout = QVBoxLayout(self.drawer_frame)
        drawer_layout.setContentsMargins(15, 15, 15, 15)
        
        drawer_title = QLabel("Paper Details & Insights")
        drawer_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4F46E5;")
        drawer_layout.addWidget(drawer_title)
        
        self.details_browser = QTextBrowser()
        self.details_browser.setOpenExternalLinks(True)
        drawer_layout.addWidget(self.details_browser)
        
        # Action Buttons inside Drawer
        btn_layout = QHBoxLayout()
        self.copy_cite_btn = QPushButton("Copy Citation")
        self.copy_cite_btn.setObjectName("SecondaryBtn")
        self.copy_cite_btn.clicked.connect(self.copy_citation)
        self.copy_cite_btn.setEnabled(False)
        
        self.del_paper_btn = QPushButton("Delete Paper")
        self.del_paper_btn.setObjectName("WarningBtn")
        self.del_paper_btn.clicked.connect(self.delete_selected_paper)
        self.del_paper_btn.setEnabled(False)
        
        btn_layout.addWidget(self.copy_cite_btn)
        btn_layout.addWidget(self.del_paper_btn)
        drawer_layout.addLayout(btn_layout)

        self.splitter.addWidget(self.drawer_frame)
        
        # Give more stretch to the table on the left
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(self.splitter)

        self.selected_paper_id: Optional[str] = None
        self.current_papers_list: List[Dict[str, Any]] = []

    def refresh(self) -> None:
        """Load and populate active user, projects, smart collections, and papers."""
        user_id = self.settings.get_active_user_id()
        if not user_id:
            return

        # Disable signals temporarily
        self.project_combo.blockSignals(True)
        self.col_combo.blockSignals(True)
        
        # Populate Projects dropdown
        self.project_combo.clear()
        projects = self.db.get_projects(user_id)
        
        active_proj_id = self.settings.get_active_project_id()
        active_idx = 0
        
        for idx, p in enumerate(projects):
            self.project_combo.addItem(p["name"], p["id"])
            if p["id"] == active_proj_id:
                active_idx = idx

        # If no projects exist, create a default one
        if not projects:
            p = self.db.create_project(user_id, "Default Project", "Default workspace for research.")
            self.project_combo.addItem(p["name"], p["id"])
            self.settings.set_active_project_id(p["id"])
            active_idx = 0

        self.project_combo.setCurrentIndex(active_idx)
        
        # Populate Smart Collections
        self.col_combo.clear()
        self.col_combo.addItem("All Papers", None)
        
        proj_id = self.settings.get_active_project_id()
        cols = self.db.get_collections(proj_id)
        for c in cols:
            self.col_combo.addItem(c["name"], c["id"])

        self.project_combo.blockSignals(False)
        self.col_combo.blockSignals(False)
        
        # Reload table
        self.load_papers_table()

    def on_project_changed(self, idx: int) -> None:
        if idx < 0:
            return
        proj_id = self.project_combo.itemData(idx)
        self.settings.set_active_project_id(proj_id)
        
        # Reload collections dropdown since they are project-bound
        self.col_combo.blockSignals(True)
        self.col_combo.clear()
        self.col_combo.addItem("All Papers", None)
        cols = self.db.get_collections(proj_id)
        for c in cols:
            self.col_combo.addItem(c["name"], c["id"])
        self.col_combo.blockSignals(False)
        
        self.load_papers_table()

    def on_collection_changed(self, idx: int) -> None:
        self.load_papers_table()

    def load_papers_table(self) -> None:
        """Fetch papers from DB based on selection filters and display in Table."""
        proj_id = self.settings.get_active_project_id()
        if not proj_id:
            return
            
        col_idx = self.col_combo.currentIndex()
        col_id = self.col_combo.itemData(col_idx) if col_idx >= 0 else None

        if col_id:
            # Query Smart Collection papers
            self.current_papers_list = self.db.get_collection_papers(col_id)
        else:
            # Query standard project papers
            self.current_papers_list = self.db.get_papers(proj_id)

        self.papers_table.setRowCount(len(self.current_papers_list))
        for idx, paper in enumerate(self.current_papers_list):
            filename_item = QTableWidgetItem(paper.get("name", ""))
            title_item = QTableWidgetItem(paper.get("title", ""))
            author_item = QTableWidgetItem(paper.get("authors", ""))
            year_item = QTableWidgetItem(str(paper.get("pub_year", "")))
            
            # Action Button
            action_btn = QPushButton("Open PDF")
            action_btn.setObjectName("SecondaryBtn")
            action_btn.clicked.connect(lambda checked, path=paper.get("file_path"): self.open_pdf_file(path))
            
            self.papers_table.setItem(idx, 0, filename_item)
            self.papers_table.setItem(idx, 1, title_item)
            self.papers_table.setItem(idx, 2, author_item)
            self.papers_table.setItem(idx, 3, year_item)
            self.papers_table.setCellWidget(idx, 4, action_btn)

        # Clear active details selection
        self.selected_paper_id = None
        self.details_browser.clear()
        self.copy_cite_btn.setEnabled(False)
        self.del_paper_btn.setEnabled(False)
        
        # Reset search displays
        self.papers_table.setVisible(True)
        self.search_results_browser.setVisible(False)

    def open_pdf_file(self, filepath: str) -> None:
        if not filepath or not os.path.exists(filepath):
            ToastNotification("Error: PDF file does not exist locally.", self.window(), duration=3000, success=False)
            return
        try:
            # Platform specific file opener
            import platform
            if platform.system() == "Windows":
                os.startfile(filepath)
            elif platform.system() == "Darwin": # macOS
                import subprocess
                subprocess.Popen(["open", filepath])
            else: # Linux
                import subprocess
                subprocess.Popen(["xdg-open", filepath])
        except Exception as e:
            logger.error(f"Failed to open PDF file: {e}")
            ToastNotification(f"Failed to open file: {e}", self.window(), duration=3000, success=False)

    def on_selection_changed(self) -> None:
        """Handle selection and populate details metadata drawer on the right."""
        selected_rows = self.papers_table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row_idx = selected_rows[0].row()
        if row_idx >= len(self.current_papers_list):
            return
            
        paper = self.current_papers_list[row_idx]
        self.selected_paper_id = paper["id"]
        
        # Enable actions
        self.copy_cite_btn.setEnabled(True)
        self.del_paper_btn.setEnabled(True)

        # Populate Meta Details Browser
        summary_str = paper.get("summary_json", "{}")
        try:
            summary = json.loads(summary_str) if summary_str else {}
        except Exception:
            summary = {}

        apa = CitationsGenerator.to_apa(paper)
        bibtex = CitationsGenerator.to_bibtex(paper)

        html = f"""
        <h3>{paper.get('title') if paper.get('title') else paper.get('name')}</h3>
        <p><b>Authors:</b> {paper.get('authors')}</p>
        <p><b>Year:</b> {paper.get('pub_year')} | <b>DOI:</b> {paper.get('doi')}</p>
        <p><b>Page Count:</b> {paper.get('pages')}</p>
        <hr/>
        
        <h4>Executive Summary</h4>
        <p>{summary.get('executive_summary', 'Not summarized yet. Please wait.')}</p>
        
        <h4>Key Contributions</h4>
        <ul>
        """
        for c in summary.get("contributions", []):
            html += f"<li>{c}</li>"
        html += f"""
        </ul>
        
        <h4>Citations Bibliography</h4>
        <p><b>APA:</b> {apa}</p>
        <pre style="background-color: #1F2937; padding: 8px; border-radius: 4px; color: #F3F4F6;">{bibtex}</pre>
        """
        self.details_browser.setHtml(html)

    # --- Global Search (Semantic & SQL) ---
    def run_search(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            self.load_papers_table()
            return
            
        proj_id = self.settings.get_active_project_id()
        user_id = self.settings.get_active_user_id()
        
        # Toggle displays
        if self.semantic_checkbox.isChecked():
            # Run Semantic Vector Search
            self.papers_table.setVisible(False)
            self.search_results_browser.setVisible(True)
            self.search_results_browser.setHtml("<p>Searching vector embeddings database...</p>")
            
            model_name = self.settings.get_embedding_model(user_id)
            # Fetch passages
            chunks = self.rag.retrieve_context(
                user_id=user_id,
                project_id=proj_id,
                query=query,
                embedding_model_name=model_name,
                k=8
            )
            
            if not chunks:
                self.search_results_browser.setHtml("<h4>No relevant matching passages found.</h4>")
                return

            html = f"<h3>Semantic Search Results for: '{query}'</h3><hr/>"
            for idx, c in enumerate(chunks):
                score = c.get("score", 0.0)
                html += f"""
                <div style="margin-bottom: 12px; padding: 10px; background-color: rgba(79, 70, 229, 0.05); border-left: 3px solid #4F46E5;">
                    <b>{c.get('paper_name')} (Page {c.get('page_number')})</b> 
                    <span style="color: #10B981; margin-left: 10px;">[Similarity Score: {score:.3f}]</span>
                    <p style="margin-top: 5px; font-style: italic;">\"{c.get('content')}\"</p>
                </div>
                """
            self.search_results_browser.setHtml(html)
        else:
            # Metadata SQL search
            self.papers_table.setVisible(True)
            self.search_results_browser.setVisible(False)
            self.current_papers_list = self.db.global_search_metadata(proj_id, query)
            
            self.papers_table.setRowCount(len(self.current_papers_list))
            for idx, paper in enumerate(self.current_papers_list):
                filename_item = QTableWidgetItem(paper.get("name", ""))
                title_item = QTableWidgetItem(paper.get("title", ""))
                author_item = QTableWidgetItem(paper.get("authors", ""))
                year_item = QTableWidgetItem(str(paper.get("pub_year", "")))
                
                action_btn = QPushButton("Open PDF")
                action_btn.setObjectName("SecondaryBtn")
                action_btn.clicked.connect(lambda checked, path=paper.get("file_path"): self.open_pdf_file(path))
                
                self.papers_table.setItem(idx, 0, filename_item)
                self.papers_table.setItem(idx, 1, title_item)
                self.papers_table.setItem(idx, 2, author_item)
                self.papers_table.setItem(idx, 3, year_item)
                self.papers_table.setCellWidget(idx, 4, action_btn)

    # --- Copy Citations to Clipboard ---
    def copy_citation(self) -> None:
        if not self.selected_paper_id:
            return
        paper = self.db.get_paper(self.selected_paper_id)
        if not paper:
            return
            
        # Get APA format
        apa = CitationsGenerator.to_apa(paper)
        QApplication.clipboard().setText(apa)
        ToastNotification("APA Citation copied to clipboard!", self.window(), duration=2000, success=True)

    # --- Project Management Commands ---
    def create_project(self) -> None:
        name, ok = QInputDialog.getText(self, "New Project", "Enter project name:")
        if ok and name.strip():
            user_id = self.settings.get_active_user_id()
            self.db.create_project(user_id, name.strip())
            ToastNotification(f"Project '{name}' created!", self.window(), duration=3000, success=True)
            self.refresh()

    def delete_project(self) -> None:
        proj_id = self.settings.get_active_project_id()
        proj = self.db.get_project(proj_id)
        if not proj:
            return
            
        reply = QMessageBox.critical(
            self,
            "Delete Project",
            f"Are you sure you want to delete the project '{proj['name']}'?\nAll associated papers, chat history, and summaries will be permanently deleted.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db.delete_project(proj_id)
            self.settings.set_active_project_id("")
            ToastNotification("Project deleted successfully.", self.window(), duration=3000, success=True)
            self.refresh()

    # --- Smart Collection Commands ---
    def create_smart_collection(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Create Smart Collection")
        dialog.setFixedWidth(350)
        
        form = QFormLayout(dialog)
        
        name_input = QLineEdit()
        kw_input = QLineEdit()
        kw_input.setPlaceholderText("comma-separated e.g. transformer, attention")
        year_min = QLineEdit()
        year_max = QLineEdit()

        form.addRow("Collection Name:", name_input)
        form.addRow("Keywords Filter:", kw_input)
        form.addRow("Min Pub Year:", year_min)
        form.addRow("Max Pub Year:", year_max)

        btn_box = QHBoxLayout()
        save_btn = QPushButton("Save Collection")
        save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(dialog.reject)
        
        btn_box.addWidget(save_btn)
        btn_box.addWidget(cancel_btn)
        form.addRow(btn_box)

        if dialog.exec() == QDialog.Accepted:
            name = name_input.text().strip()
            if not name:
                ToastNotification("Collection name cannot be empty.", self.window(), duration=3000, success=False)
                return

            # Parse keywords
            keywords = [k.strip() for k in kw_input.text().split(",") if k.strip()]
            
            # Parse years
            ymin = int(year_min.text()) if year_min.text().isdigit() else None
            ymax = int(year_max.text()) if year_max.text().isdigit() else None

            rules = {
                "keywords": keywords,
                "year_min": ymin,
                "year_max": ymax
            }

            user_id = self.settings.get_active_user_id()
            proj_id = self.settings.get_active_project_id()
            self.db.create_collection(user_id, proj_id, name, rules)
            ToastNotification(f"Smart Collection '{name}' created!", self.window(), duration=3000, success=True)
            self.refresh()

    # --- Delete Paper ---
    def delete_selected_paper(self) -> None:
        if not self.selected_paper_id:
            return
        paper = self.db.get_paper(self.selected_paper_id)
        if not paper:
            return

        reply = QMessageBox.warning(
            self,
            "Delete Paper",
            f"Are you sure you want to permanently delete the paper '{paper['name']}' from the library and database?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            user_id = self.settings.get_active_user_id()
            proj_id = self.settings.get_active_project_id()
            model_name = self.settings.get_embedding_model(user_id)
            
            # Delete physical copy if it is stored inside uploads directory
            if "uploads" in paper["file_path"] and os.path.exists(paper["file_path"]):
                try:
                    os.remove(paper["file_path"])
                except Exception as e:
                    logger.error(f"Failed to delete paper file: {e}")

            # Delete database records & FAISS vectors
            self.db.delete_paper(self.selected_paper_id)
            self.rag.delete_paper_from_index(user_id, proj_id, self.selected_paper_id, model_name)
            
            ToastNotification(f"Deleted '{paper['name']}' from library.", self.window(), duration=3000, success=True)
            self.refresh()
