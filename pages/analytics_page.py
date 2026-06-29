import logging
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSplitter
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from services.db_service import DatabaseService
from services.settings_service import SettingsService
from ui.components.graph_widget import PaperGraphWidget

logger = logging.getLogger("app")

# --- Custom-Drawn Analytics Chart Widget ---
class AnalyticsChartWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.chart_type = "line" # "line" or "bar"
        self.chart_data: List[Dict[str, Any]] = []
        self.x_label_key = "day"
        self.y_label_key = "count"

    def set_data(self, data: List[Dict[str, Any]], chart_type: str = "line", x_key: str = "day", y_key: str = "count") -> None:
        self.chart_data = data
        self.chart_type = chart_type
        self.x_label_key = x_key
        self.y_label_key = y_key
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        bg_col = self.palette().window().color()
        is_dark = bg_col.lightness() < 128
        
        text_color = QColor("#9CA3AF") if is_dark else QColor("#4B5563")
        grid_color = QColor("#1F2937") if is_dark else QColor("#E5E7EB")
        accent_color = QColor("#4F46E5") # Primary Violet
        
        w = self.width()
        h = self.height()
        
        # Grid margins
        left_margin = 45
        right_margin = 15
        top_margin = 20
        bottom_margin = 30
        
        plot_w = w - left_margin - right_margin
        plot_h = h - top_margin - bottom_margin

        # Draw grid frame
        painter.setPen(QPen(grid_color, 1))
        painter.drawRect(left_margin, top_margin, plot_w, plot_h)

        if not self.chart_data:
            painter.setPen(QPen(text_color))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(left_margin + plot_w/2 - 50, top_margin + plot_h/2, "No data logged yet.")
            return

        # Find maximum Y value
        max_y = max(float(item.get(self.y_label_key, 0)) for item in self.chart_data)
        if max_y <= 0:
            max_y = 10.0
            
        # Add padding to top of max Y
        max_y *= 1.2
        
        # Draw Y-axis division gridlines
        y_divs = 4
        painter.setFont(QFont("Segoe UI", 8))
        for i in range(y_divs + 1):
            val = (max_y / y_divs) * i
            y_pos = top_margin + plot_h - (plot_h / y_divs) * i
            
            # Line
            if i > 0 and i < y_divs:
                painter.setPen(QPen(grid_color, 1, Qt.DashLine))
                painter.drawLine(left_margin, int(y_pos), left_margin + plot_w, int(y_pos))
                
            # Text label
            painter.setPen(QPen(text_color))
            y_str = f"{val:.1f}" if val < 1 else f"{int(val)}"
            painter.drawText(left_margin - 35, int(y_pos + 4), y_str)

        # Draw X-axis items
        x_items = len(self.chart_data)
        col_w = plot_w / x_items
        
        # Line Chart mode
        if self.chart_type == "line":
            points = []
            for idx, item in enumerate(self.chart_data):
                val = float(item.get(self.y_label_key, 0))
                x_pos = left_margin + col_w * idx + col_w / 2
                y_pos = top_margin + plot_h - (val / max_y) * plot_h
                points.append(QPointF(x_pos, y_pos))
                
                # Draw small labels under axis
                if x_items < 12 or idx % (x_items // 5 + 1) == 0:
                    label = str(item.get(self.x_label_key, ""))
                    # Shorten date strings e.g. 2026-06-24 -> 06-24
                    if len(label) == 10:
                        label = label[5:]
                    painter.drawText(int(x_pos - 15), top_margin + plot_h + 15, label)

            # Draw lines
            pen = QPen(accent_color, 2.5)
            painter.setPen(pen)
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i+1])
                
            # Draw point circles
            painter.setBrush(QBrush(QColor("#10B981"))) # Green dots
            painter.setPen(Qt.NoPen)
            for pt in points:
                painter.drawEllipse(pt, 4.0, 4.0)

        # Bar Chart mode (e.g. Provider count)
        elif self.chart_type == "bar":
            for idx, item in enumerate(self.chart_data):
                val = float(item.get(self.y_label_key, 0))
                x_pos = left_margin + col_w * idx + 6
                bar_w = col_w - 12
                bar_h = (val / max_y) * plot_h
                y_pos = top_margin + plot_h - bar_h
                
                # Draw Bar
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor("#4F46E5")))
                painter.drawRoundedRect(int(x_pos), int(y_pos), int(bar_w), int(bar_h), 4, 4)
                
                # Draw X Label
                label = str(item.get(self.x_label_key, "")).upper()
                metrics = painter.fontMetrics()
                text_w = metrics.horizontalAdvance(label)
                painter.setPen(QPen(text_color))
                painter.drawText(int(x_pos + bar_w/2 - text_w/2), top_margin + plot_h + 15, label)
                
                # Value on top of bar
                val_str = f"{val:.0f}"
                val_w = metrics.horizontalAdvance(val_str)
                painter.drawText(int(x_pos + bar_w/2 - val_w/2), int(y_pos - 4), val_str)


class AnalyticsPage(QWidget):
    def __init__(self, db_service: DatabaseService, settings_service: SettingsService, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = db_service
        self.settings = settings_service
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header
        header = QLabel("Workspace Analytics & Graphs")
        header.setObjectName("PageTitle")
        main_layout.addWidget(header)

        # Splitter Layout (Left Charts -> Right Similarity Network Graph)
        splitter = QSplitter(Qt.Horizontal)

        # Left Column: Charts Container
        charts_frame = QFrame()
        charts_layout = QVBoxLayout(charts_frame)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        charts_layout.setSpacing(20)

        # Line Chart box: Queries Per Day
        queries_frame = QFrame()
        queries_frame.setObjectName("SidebarFrame")
        queries_frame.setStyleSheet("border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        queries_vbox = QVBoxLayout(queries_frame)
        queries_vbox.setContentsMargins(15, 15, 15, 15)
        
        queries_title = QLabel("Chat Queries Volume (Last 30 Days)")
        queries_title.setStyleSheet("font-weight: bold; color: #4F46E5;")
        queries_vbox.addWidget(queries_title)
        
        self.queries_chart = AnalyticsChartWidget()
        self.queries_chart.setFixedHeight(180)
        queries_vbox.addWidget(self.queries_chart)
        charts_layout.addWidget(queries_frame)

        # Bar Chart box: Provider API Calls
        provider_frame = QFrame()
        provider_frame.setObjectName("SidebarFrame")
        provider_frame.setStyleSheet("border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        provider_vbox = QVBoxLayout(provider_frame)
        provider_vbox.setContentsMargins(15, 15, 15, 15)
        
        provider_title = QLabel("API Requests Count by Provider")
        provider_title.setStyleSheet("font-weight: bold; color: #4F46E5;")
        provider_vbox.addWidget(provider_title)
        
        self.provider_chart = AnalyticsChartWidget()
        self.provider_chart.setFixedHeight(180)
        provider_vbox.addWidget(self.provider_chart)
        charts_layout.addWidget(provider_frame)

        splitter.addWidget(charts_frame)

        # Right Column: Paper Similarity Network Graph
        graph_frame = QFrame()
        graph_frame.setObjectName("SidebarFrame")
        graph_frame.setStyleSheet("border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);")
        graph_vbox = QVBoxLayout(graph_frame)
        graph_vbox.setContentsMargins(15, 15, 15, 15)

        graph_title = QLabel("Literature Inter-Similarity Graph")
        graph_title.setStyleSheet("font-weight: bold; color: #4F46E5;")
        graph_vbox.addWidget(graph_title)
        
        self.graph_widget = PaperGraphWidget()
        graph_vbox.addWidget(self.graph_widget)

        splitter.addWidget(graph_frame)
        
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 5)
        main_layout.addWidget(splitter)

    def refresh(self) -> None:
        """Fetch statistics from DB and update charts & graph node states."""
        user_id = self.settings.get_active_user_id()
        project_id = self.settings.get_active_project_id()
        if not user_id or not project_id:
            return

        # 1. Load data into Paper Relationship Graph
        papers = self.db.get_papers(project_id)
        # Filter papers to only those that have summaries (for better keywords comparison)
        self.graph_widget.set_papers(papers)

        # 2. Load API usage logs
        metrics = self.db.get_api_usage_metrics(user_id)
        
        # Populate Daily Line Chart
        daily_data = metrics.get("daily_usage", [])
        self.queries_chart.set_data(daily_data, chart_type="line", x_key="day", y_key="count")

        # Populate Provider Bar Chart
        provider_data = metrics.get("provider_breakdown", [])
        self.provider_chart.set_data(provider_data, chart_type="bar", x_key="provider", y_key="count")
