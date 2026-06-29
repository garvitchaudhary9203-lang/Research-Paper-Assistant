import json
import logging
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, 
                             QListWidgetItem, QSplitter, QFrame, QTextBrowser, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal
from services.db_service import DatabaseService
from services.settings_service import SettingsService
from services.llm_service import LLMService
from services.export_service import ExportService
from ui.components.toast import ToastNotification

logger = logging.getLogger("app")

# --- Async Comparison LLM Thread ---
class ComparisonWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, 
                 user_id: str, 
                 project_id: str,
                 selected_papers: List[Dict[str, Any]], 
                 llm_service: LLMService):
        super().__init__()
        self.user_id = user_id
        self.project_id = project_id
        self.papers = selected_papers
        self.llm = llm_service

    def run(self) -> None:
        """Concatenate summaries and ask LLM to synthesize comparative analysis."""
        try:
            # 1. Compile summaries context
            context = ""
            for p in self.papers:
                summary_data = p.get("summary_json", "{}")
                try:
                    summary = json.loads(summary_data)
                except Exception:
                    summary = {}
                    
                context += f"\n=== PAPER: {p['name']} ===\n"
                context += f"Title: {p.get('title')}\n"
                context += f"Authors: {p.get('authors')}\n"
                context += f"Objective: {summary.get('objective', 'N/A')}\n"
                context += f"Methodology: {summary.get('methodology', 'N/A')}\n"
                context += f"Results: {summary.get('results', 'N/A')}\n"
                context += f"Contributions: {', '.join(summary.get('contributions', []))}\n"
                context += f"Limitations: {json.dumps(summary.get('limitations', {}))}\n"
                context += f"Future Work: {json.dumps(summary.get('future_work', {}))}\n"
                context += "========================================\n"

            prompt = (
                f"Evaluate the following research summaries and perform a comparative analysis. "
                f"Generate a JSON object containing the comparison matrix and general synthesis. "
                f"The JSON object must have exactly the following structure:\n"
                f"{{\n"
                f"  \"matrix\": {{\n"
                # For each paper, detail their columns
                f"    \"<paper_id_1>\": {{\n"
                f"      \"research_problem\": \"Summary of research problem\",\n"
                f"      \"methodology\": \"Summary of methodology\",\n"
                f"      \"dataset\": \"Dataset detail\",\n"
                f"      \"results\": \"Key results\",\n"
                f"      \"contributions\": \"Main contribution\",\n"
                f"      \"limitations\": \"Main limit\"\n"
                f"    }},\n"
                f"    ...\n"
                f"  }},\n"
                f"  \"synthesis\": {{\n"
                f"    \"analysis\": \"Sleek comparative synthesis paragraph.\",\n"
                f"    \"strengths\": \"Common strengths across papers.\",\n"
                f"    \"weaknesses\": \"Common limitations and gaps in literature.\"\n"
                f"  }}\n"
                f"}}\n\n"
                f"Papers Context:\n{context}"
            )

            res, _ = self.llm.generate(
                user_id=self.user_id,
                prompt=prompt,
                context_chunks=[],
                history=[],
                mode="Comparison Expert",
                custom_system_prompt="You are a senior academic reviewer. Output raw JSON objects matching the schema."
            )
            
            # Check for API connection or authentication errors
            if res.startswith("Error") or res.startswith("Network Error") or res.startswith("Local Ollama error") or "unreachable" in res:
                self.error.emit(res)
                return

            # Clean markdown codeblocks
            json_str = res.replace("```json", "").replace("```", "").strip()
            try:
                result_data = json.loads(json_str)
                self.finished.emit(result_data)
            except json.JSONDecodeError as je:
                logger.error(f"Failed to parse LLM comparison JSON: {je}. Raw: {res}")
                self.error.emit(f"The AI provider failed to output a structured comparison table. Details: {str(je)}\n\nRaw Response: {res[:300]}")
        except Exception as e:
            logger.error(f"Comparison worker thread failed: {e}")
            self.error.emit(str(e))

class ComparisonPage(QWidget):
    def __init__(self, 
                 db_service: DatabaseService, 
                 settings_service: SettingsService, 
                 llm_service: LLMService,
                 export_service: ExportService,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_service
        self.settings = settings_service
        self.llm = llm_service
        self.export = export_service
        
        self.active_comparison_record: Optional[Dict[str, Any]] = None
        self.active_papers: List[Dict[str, Any]] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("Compare Research Papers")
        header.setObjectName("PageTitle")
        layout.addWidget(header)

        # Main Splitter Layout (Left Papers selector -> Right Table & Synthesis)
        self.splitter = QSplitter(Qt.Horizontal)

        # Left Panel: Checkable Papers list
        selector_frame = QFrame()
        selector_frame.setObjectName("SidebarFrame")
        selector_layout = QVBoxLayout(selector_frame)
        selector_layout.setContentsMargins(10, 10, 10, 10)
        
        sel_title = QLabel("Select Papers (Min 2)")
        sel_title.setStyleSheet("font-weight: bold; color: #4F46E5;")
        selector_layout.addWidget(sel_title)
        
        self.papers_list = QListWidget()
        selector_layout.addWidget(self.papers_list)

        self.compare_btn = QPushButton("Generate Comparison")
        self.compare_btn.setObjectName("PrimaryBtn")
        self.compare_btn.clicked.connect(self.run_comparison)
        selector_layout.addWidget(self.compare_btn)

        self.splitter.addWidget(selector_frame)

        # Right Panel: Results Matrix Display
        results_frame = QFrame()
        results_layout = QVBoxLayout(results_frame)
        results_layout.setContentsMargins(0, 0, 0, 0)
        
        # Grid Table Matrix
        self.comp_table = QTableWidget(0, 3)
        self.comp_table.setHorizontalHeaderLabels(["Criterion", "Paper 1", "Paper 2"])
        self.comp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.comp_table.verticalHeader().setVisible(False)
        self.comp_table.setEditTriggers(QTableWidget.NoEditTriggers)
        results_layout.addWidget(self.comp_table)

        # Synthesis Text browser
        self.synthesis_browser = QTextBrowser()
        self.synthesis_browser.setStyleSheet("background-color: #111827; border: 1px solid #1F2937;")
        self.synthesis_browser.setFixedHeight(220)
        results_layout.addWidget(self.synthesis_browser)

        # Export Buttons
        btn_bar = QHBoxLayout()
        self.export_report_btn = QPushButton("Export Comparison PDF")
        self.export_report_btn.setObjectName("SecondaryBtn")
        self.export_report_btn.clicked.connect(self.export_comparison)
        self.export_report_btn.setEnabled(False)

        self.export_full_project_btn = QPushButton("Export Full Workspace Report")
        self.export_full_project_btn.setObjectName("PrimaryBtn")
        self.export_full_project_btn.clicked.connect(self.export_full_workspace_report)
        self.export_full_project_btn.setEnabled(False)
        
        btn_bar.addWidget(self.export_report_btn)
        btn_bar.addWidget(self.export_full_project_btn)
        results_layout.addLayout(btn_bar)

        self.splitter.addWidget(results_frame)
        
        # Setup sizes
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        layout.addWidget(self.splitter)

    def refresh(self) -> None:
        """Load checkbox list of papers in the active project."""
        proj_id = self.settings.get_active_project_id()
        if not proj_id:
            return
            
        self.papers_list.clear()
        papers = self.db.get_papers(proj_id)
        
        for p in papers:
            # Check if summary has been generated for this paper
            summary_str = p.get("summary_json", "")
            has_summary = False
            try:
                if summary_str and json.loads(summary_str).get("executive_summary"):
                    has_summary = True
            except Exception:
                pass
                
            suffix = "" if has_summary else " (Missing Summary)"
            
            item = QListWidgetItem(p["name"] + suffix)
            item.setData(Qt.UserRole, p)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            
            # Disable item check state if no summary available
            if not has_summary:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Unchecked)
                
            self.papers_list.addItem(item)

        # Clear results panel
        self.comp_table.setRowCount(0)
        self.synthesis_browser.clear()
        self.export_report_btn.setEnabled(False)
        self.export_full_project_btn.setEnabled(False)
        self.active_comparison_record = None

    def run_comparison(self) -> None:
        """Identify checked papers and spawn comparison thread."""
        user_id = self.settings.get_active_user_id()
        project_id = self.settings.get_active_project_id()
        
        # Gather checked papers
        self.active_papers.clear()
        for i in range(self.papers_list.count()):
            item = self.papers_list.item(i)
            if item.checkState() == Qt.Checked:
                self.active_papers.append(item.data(Qt.UserRole))

        if len(self.active_papers) < 2:
            ToastNotification("Warning: Please select at least 2 summarized papers to compare.", self.window(), duration=3000, success=False)
            return

        # Disable buttons during comparison
        self.compare_btn.setEnabled(False)
        self.synthesis_browser.setHtml("<p>AI Expert is analyzing methodology, dataset parameters, and results. Please wait...</p>")
        
        # Spawn thread
        self.comp_thread = ComparisonWorker(user_id, project_id, self.active_papers, self.llm)
        self.comp_thread.finished.connect(self.on_comparison_finished)
        self.comp_thread.error.connect(self.on_comparison_failed)
        self.comp_thread.start()

    def on_comparison_finished(self, data: dict) -> None:
        self.compare_btn.setEnabled(True)
        user_id = self.settings.get_active_user_id()
        project_id = self.settings.get_active_project_id()

        # Save to database
        paper_ids = [p["id"] for p in self.active_papers]
        self.active_comparison_record = self.db.save_comparison(user_id, project_id, paper_ids, data)

        self.display_comparison(data)
        
        # Enable PDF exports
        self.export_report_btn.setEnabled(True)
        self.export_full_project_btn.setEnabled(True)
        ToastNotification("AI Comparison Matrix generated successfully!", self.window(), duration=3000, success=True)

    def on_comparison_failed(self, err: str) -> None:
        self.compare_btn.setEnabled(True)
        self.synthesis_browser.clear()
        QMessageBox.warning(self, "Comparison Generation Failed", f"An error occurred while compiling comparison report:\n\n{err}")

    def display_comparison(self, data: dict) -> None:
        """Render results onto the comparison table and text panel."""
        matrix = data.get("matrix", {})
        synthesis = data.get("synthesis", {})

        # Set up table header
        headers = ["Criterion"] + [p["name"][:18] + "..." if len(p["name"]) > 18 else p["name"] for p in self.active_papers]
        self.comp_table.setColumnCount(len(headers))
        self.comp_table.setHorizontalHeaderLabels(headers)
        self.comp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        criteria = [
            ("Research Problem", "research_problem"),
            ("Methodology", "methodology"),
            ("Dataset Parameters", "dataset"),
            ("Key Results", "results"),
            ("Contributions", "contributions"),
            ("Limitations", "limitations")
        ]

        self.comp_table.setRowCount(len(criteria))
        for row_idx, (crit_name, crit_key) in enumerate(criteria):
            self.comp_table.setItem(row_idx, 0, QTableWidgetItem(crit_name))
            for col_idx, p in enumerate(self.active_papers):
                p_id = p["id"]
                # Retrieve from comparison matrix json
                val = matrix.get(p_id, {}).get(crit_key, "N/A")
                self.comp_table.setItem(row_idx, col_idx + 1, QTableWidgetItem(str(val)))

        # Display Synthesis
        html = f"""
        <h3>AI Comparative Synthesis</h3>
        <p>{synthesis.get('analysis', '')}</p>
        <h4>Shared Strengths</h4>
        <p>{synthesis.get('strengths', '')}</p>
        <h4>Shared Limitations & Gaps</h4>
        <p>{synthesis.get('weaknesses', '')}</p>
        """
        self.synthesis_browser.setHtml(html)

    # --- Exports ---
    def export_comparison(self) -> None:
        if not self.active_comparison_record:
            return
        filename = f"comparison_{self.active_comparison_record['id'][:8]}.pdf"
        try:
            file_path = self.export.export_comparison_pdf(
                self.active_comparison_record, 
                self.active_papers, 
                filename
            )
            QMessageBox.information(self, "Export Successful", f"Comparison report exported as PDF to:\n\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Failed to export report PDF:\n\n{e}")

    def export_full_workspace_report(self) -> None:
        proj_id = self.settings.get_active_project_id()
        proj = self.db.get_project(proj_id)
        if not proj:
            return
            
        papers = self.db.get_papers(proj_id)
        comparisons = self.db.get_comparisons(proj_id)

        filename = f"workspace_report_{proj_id[:8]}.pdf"
        try:
            file_path = self.export.export_full_report_pdf(
                proj["name"],
                papers,
                comparisons,
                filename
            )
            QMessageBox.information(self, "Workspace Export Successful", f"Comprehensive Project Report generated successfully:\n\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Workspace Export Failed", f"Failed to generate comprehensive report:\n\n{e}")
