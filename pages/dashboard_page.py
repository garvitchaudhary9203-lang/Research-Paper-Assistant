import logging
from typing import Dict, Any, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea
from PySide6.QtCore import Qt
from services.db_service import DatabaseService
from services.settings_service import SettingsService

logger = logging.getLogger("app")

class DashboardPage(QWidget):
    def __init__(self, db_service: DatabaseService, settings_service: SettingsService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_service
        self.settings = settings_service
        
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Header
        header_label = QLabel("Analytics Dashboard")
        header_label.setObjectName("PageTitle")
        main_layout.addWidget(header_label)

        # Scroll Area for responsive sizing
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(20)

        # 1. Cards Grid
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(15)
        
        self.papers_card = self._create_card("Total Papers", "0")
        self.chats_card = self._create_card("Conversations", "0")
        self.queries_card = self._create_card("Questions Asked", "0")
        self.cost_card = self._create_card("Est. API Cost", "$0.000")

        self.cards_layout.addWidget(self.papers_card)
        self.cards_layout.addWidget(self.chats_card)
        self.cards_layout.addWidget(self.queries_card)
        self.cards_layout.addWidget(self.cost_card)
        self.scroll_layout.addLayout(self.cards_layout)

        # 2. Benchmarks & Recent Activity Split
        split_layout = QHBoxLayout()
        split_layout.setSpacing(20)

        # Left Column: Provider Benchmarks
        bench_frame = QFrame()
        bench_frame.setObjectName("SidebarFrame")
        bench_frame.setStyleSheet("border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        bench_layout = QVBoxLayout(bench_frame)
        bench_layout.setContentsMargins(15, 15, 15, 15)

        bench_title = QLabel("AI Provider Benchmarks")
        bench_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4F46E5;")
        bench_layout.addWidget(bench_title)

        self.bench_table = QTableWidget(0, 3)
        self.bench_table.setHorizontalHeaderLabels(["Provider", "Requests", "Incurred Cost"])
        self.bench_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bench_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.bench_table.setSelectionMode(QTableWidget.NoSelection)
        self.bench_table.setFixedHeight(220)
        bench_layout.addWidget(self.bench_table)

        split_layout.addWidget(bench_frame, 3)

        # Right Column: Recent Papers
        recent_frame = QFrame()
        recent_frame.setObjectName("SidebarFrame")
        recent_frame.setStyleSheet("border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        recent_layout = QVBoxLayout(recent_frame)
        recent_layout.setContentsMargins(15, 15, 15, 15)

        recent_title = QLabel("Recently Indexed Papers")
        recent_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4F46E5;")
        recent_layout.addWidget(recent_title)

        self.recent_table = QTableWidget(0, 3)
        self.recent_table.setHorizontalHeaderLabels(["Filename", "Authors", "Pages"])
        self.recent_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recent_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recent_table.setFixedHeight(220)
        recent_layout.addWidget(self.recent_table)

        split_layout.addWidget(recent_frame, 4)
        
        self.scroll_layout.addLayout(split_layout)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def _create_card(self, title: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("MetricCard")
        card.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        
        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        
        val_label = QLabel(value)
        val_label.setObjectName("CardValue")
        
        layout.addWidget(title_label)
        layout.addWidget(val_label)
        return card

    def refresh(self) -> None:
        """Update metrics and refresh UI tables."""
        user_id = self.settings.get_active_user_id()
        project_id = self.settings.get_active_project_id()
        if not user_id or not project_id:
            return

        # 1. Fetch count stats
        papers = self.db.get_papers(project_id)
        sessions = self.db.get_sessions(project_id)
        
        total_queries = 0
        for s in sessions:
            history = self.db.get_chat_history(s["id"])
            total_queries += sum(1 for m in history if m["role"] == "user")
            
        metrics = self.db.get_api_usage_metrics(user_id)
        total_cost = metrics.get("total_cost", 0.0)

        # Update card labels
        self.papers_card.findChild(QLabel, "CardValue").setText(str(len(papers)))
        self.chats_card.findChild(QLabel, "CardValue").setText(str(len(sessions)))
        self.queries_card.findChild(QLabel, "CardValue").setText(str(total_queries))
        self.cost_card.findChild(QLabel, "CardValue").setText(f"${total_cost:.3f}")

        # 2. Update Benchmarks Table
        providers_breakdown = metrics.get("provider_breakdown", [])
        self.bench_table.setRowCount(len(providers_breakdown))
        for idx, pb in enumerate(providers_breakdown):
            prov_item = QTableWidgetItem(str(pb.get("provider", "")).upper())
            count_item = QTableWidgetItem(str(pb.get("count", 0)))
            cost_item = QTableWidgetItem(f"${pb.get('cost', 0.0):.4f}")
            
            self.bench_table.setItem(idx, 0, prov_item)
            self.bench_table.setItem(idx, 1, count_item)
            self.bench_table.setItem(idx, 2, cost_item)

        # 3. Update Recent Papers Table
        recent_papers = papers[:5] # Show last 5
        self.recent_table.setRowCount(len(recent_papers))
        for idx, paper in enumerate(recent_papers):
            name_item = QTableWidgetItem(paper.get("name", ""))
            author_item = QTableWidgetItem(paper.get("authors", ""))
            pages_item = QTableWidgetItem(str(paper.get("pages", 0)))
            
            self.recent_table.setItem(idx, 0, name_item)
            self.recent_table.setItem(idx, 1, author_item)
            self.recent_table.setItem(idx, 2, pages_item)
