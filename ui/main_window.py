import logging
from typing import Dict, Any, Optional
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel, QPushButton, QStackedWidget
from PySide6.QtCore import Qt

from ui.styles import DARK_STYLE, LIGHT_STYLE
from pages.dashboard_page import DashboardPage
from pages.upload_page import UploadPage
from pages.library_page import LibraryPage
from pages.chat_page import ChatPage
from pages.comparison_page import ComparisonPage
from pages.memory_page import MemoryPage
from pages.analytics_page import AnalyticsPage
from pages.settings_page import SettingsPage
from pages.about_page import AboutPage

logger = logging.getLogger("app")

class MainWindow(QMainWindow):
    def __init__(self, services: Dict[str, Any]):
        """
        Injects the registry of application services.
        
        Args:
            services: Dict containing instanced Service classes:
                      {'db': DatabaseService, 'settings': SettingsService, 'rag': RAGService,
                       'llm': LLMService, 'export': ExportService, 'plugins': PluginManager}
        """
        super().__init__()
        self.services = services
        self.db = services["db"]
        self.settings = services["settings"]
        
        self.setWindowTitle("Research Paper Assistant Pro")
        self.setMinimumSize(1100, 700)
        
        self._init_ui()
        self.apply_stylesheet()
        self.restore_view_state()

    def _init_ui(self) -> None:
        # Core main widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Sidebar Navigation Panel
        sidebar_frame = QFrame()
        sidebar_frame.setObjectName("SidebarFrame")
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # App branding header
        brand_label = QLabel("Research Pro")
        brand_label.setObjectName("SidebarTitle")
        brand_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(brand_label)

        # Active workspace stats labels
        self.workspace_lbl = QLabel("Profile: Loading...")
        self.workspace_lbl.setStyleSheet("color: #9CA3AF; padding: 10px 18px 2px 18px; font-size: 11px;")
        self.project_lbl = QLabel("Project: Loading...")
        self.project_lbl.setStyleSheet("color: #9CA3AF; padding: 2px 18px 10px 18px; font-size: 11px;")
        
        sidebar_layout.addWidget(self.workspace_lbl)
        sidebar_layout.addWidget(self.project_lbl)

        # Sidebar Buttons
        self.nav_buttons: Dict[str, QPushButton] = {}
        nav_items = [
            ("Dashboard", "📊 Dashboard"),
            ("Upload Papers", "📥 Upload Papers"),
            ("Research Library", "📚 Research Library"),
            ("Research Chat", "💬 Research Chat"),
            ("Paper Comparison", "⚖️ Paper Comparison"),
            ("Research Memory", "🧠 Research Memory"),
            ("Analytics", "📈 Analytics"),
            ("Settings", "⚙️ Settings"),
            ("About", "ℹ️ About")
        ]

        for page_name, label in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("SidebarBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda checked=False, name=page_name: self.navigate_to_page(name))
            
            sidebar_layout.addWidget(btn)
            self.nav_buttons[page_name] = btn

        sidebar_layout.addStretch()

        # Sidebar version stamp
        version_lbl = QLabel("v1.0.0 (Stable)")
        version_lbl.setObjectName("SidebarVersion")
        version_lbl.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(version_lbl)

        main_layout.addWidget(sidebar_frame, 2)

        # 2. Right Stacked Pages Widget
        self.pages_widget = QStackedWidget()
        self.pages_widget.setObjectName("ContentFrame")
        
        # Instantiate pages passing injected services (Dependency Injection)
        self.pages: Dict[str, QWidget] = {
            "Dashboard": DashboardPage(self.db, self.settings),
            "Upload Papers": UploadPage(self.db, self.settings, self.services["rag"], self.services["llm"]),
            "Research Library": LibraryPage(self.db, self.settings, self.services["rag"]),
            "Research Chat": ChatPage(self.db, self.settings, self.services["rag"], self.services["llm"], self.services["export"]),
            "Paper Comparison": ComparisonPage(self.db, self.settings, self.services["llm"], self.services["export"]),
            "Research Memory": MemoryPage(self.db, self.settings),
            "Analytics": AnalyticsPage(self.db, self.settings),
            "Settings": SettingsPage(self.db, self.settings, self.services["llm"]),
            "About": AboutPage()
        }

        # Set Object Names for child lookups
        self.pages["Research Library"].setObjectName("LibraryPage")
        self.pages["Paper Comparison"].setObjectName("ComparisonPage")

        for page_widget in self.pages.values():
            self.pages_widget.addWidget(page_widget)

        main_layout.addWidget(self.pages_widget, 8)

    def navigate_to_page(self, page_name: str) -> None:
        """Route central view to selected page index and update active sidebar button styling."""
        if page_name not in self.pages:
            return
            
        # Update sidebar button states
        for name, btn in self.nav_buttons.items():
            if name == page_name:
                btn.setProperty("active", "true")
            else:
                btn.setProperty("active", "false")
            # Style sheets evaluate dynamic properties on polish
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Show selected page
        page_widget = self.pages[page_name]
        self.pages_widget.setCurrentWidget(page_widget)
        
        # Trigger refresh on the targeted page
        if hasattr(page_widget, "refresh"):
            page_widget.refresh()

        # Update sidebar info headers
        self.refresh_active_headers()

    def refresh_active_headers(self) -> None:
        """Updates active user profile and project titles displayed in the sidebar."""
        user_id = self.settings.get_active_user_id()
        proj_id = self.settings.get_active_project_id()
        
        user = self.db.get_user(user_id) if user_id else None
        proj = self.db.get_project(proj_id) if proj_id else None
        
        u_name = user["username"] if user else "None"
        p_name = proj["name"] if proj else "None"
        
        self.workspace_lbl.setText(f"Profile: <b>{u_name}</b>")
        self.project_lbl.setText(f"Project: <b>{p_name}</b>")

    def refresh_active_page(self) -> None:
        """Refreshes whichever page is currently in view (used during switch events)."""
        current_widget = self.pages_widget.currentWidget()
        if current_widget and hasattr(current_widget, "refresh"):
            current_widget.refresh()
        self.refresh_active_headers()

    def apply_stylesheet(self) -> None:
        """Toggle styling based on current settings theme (Dark/Light)."""
        theme = self.settings.get_theme()
        if theme == "dark":
            self.setStyleSheet(DARK_STYLE)
        else:
            self.setStyleSheet(LIGHT_STYLE)

    def restore_view_state(self) -> None:
        """Restore previous page view and project layouts for recovery."""
        user_id = self.settings.get_active_user_id()
        
        # If no active user profile exists, create/auto-select default
        if not user_id:
            users = self.db.get_users()
            if users:
                user_id = users[0]["id"]
            else:
                user = self.db.create_user("Default Researcher")
                user_id = user["id"]
                # Default workspace project
                self.db.create_project(user_id, "Main Workspace", "Initial research workspace.")
            self.settings.set_active_user_id(user_id)

        # Restore last active page view
        last_page = self.settings.get_last_page()
        self.navigate_to_page(last_page if last_page in self.pages else "Dashboard")

    def closeEvent(self, event) -> None:
        """Write UI states to settings.json on closure for crash recovery."""
        current_widget = self.pages_widget.currentWidget()
        # Find page name
        page_name = "Dashboard"
        for name, widget in self.pages.items():
            if widget == current_widget:
                page_name = name
                break
        self.settings.set_last_page(page_name)
        
        # Close SQLite DB connection safely
        self.db.close()
        event.accept()
