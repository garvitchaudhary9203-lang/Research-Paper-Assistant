# Premium CSS styles for Research Paper Assistant Pro

DARK_STYLE = """
/* Dark Theme Stylesheet */
QMainWindow {
    background-color: #0B0F19; /* Sleek Deep Slate */
}

QWidget {
    color: #F3F4F6;
    font-family: "Segoe UI", -apple-system, Roboto, sans-serif;
    font-size: 13px;
}

/* Sidebar Navigation */
#SidebarFrame {
    background-color: #111827; /* Rich Dark Charcoal */
    border-right: 1px solid #1F2937;
}

#SidebarTitle {
    color: #4F46E5; /* Vibrant Violet */
    font-size: 16px;
    font-weight: bold;
    padding: 15px 10px;
    border-bottom: 1px solid #1F2937;
}

#SidebarVersion {
    color: #6B7280;
    font-size: 10px;
    padding: 5px 10px;
}

QPushButton.SidebarBtn {
    background-color: transparent;
    color: #9CA3AF;
    text-align: left;
    padding: 12px 18px;
    border: none;
    border-left: 3px solid transparent;
    font-weight: 500;
}

QPushButton.SidebarBtn:hover {
    background-color: #1F2937;
    color: #F3F4F6;
}

QPushButton.SidebarBtn[active="true"] {
    background-color: #1F2937;
    color: #4F46E5;
    border-left: 3px solid #4F46E5;
}

/* Main Content Containers */
#ContentFrame {
    background-color: #0B0F19;
}

#PageTitle {
    font-size: 22px;
    font-weight: bold;
    color: #FFFFFF;
    margin-bottom: 20px;
}

/* Glassmorphism Cards */
QFrame.MetricCard {
    background-color: rgba(31, 41, 55, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 15px;
}

#CardTitle {
    font-size: 11px;
    font-weight: 600;
    color: #9CA3AF;
    text-transform: uppercase;
}

#CardValue {
    font-size: 24px;
    font-weight: bold;
    color: #FFFFFF;
    margin-top: 5px;
}

/* Buttons */
QPushButton.PrimaryBtn {
    background-color: #4F46E5;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton.PrimaryBtn:hover {
    background-color: #4338CA;
}

QPushButton.PrimaryBtn:pressed {
    background-color: #3730A3;
}

QPushButton.SecondaryBtn {
    background-color: #374151;
    color: #F3F4F6;
    border: 1px solid #4B5563;
    border-radius: 6px;
    padding: 8px 16px;
}

QPushButton.SecondaryBtn:hover {
    background-color: #4B5563;
}

QPushButton.WarningBtn {
    background-color: #DC2626;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
}

QPushButton.WarningBtn:hover {
    background-color: #B91C1C;
}

/* Inputs and Forms */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background-color: #1F2937;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 8px;
    color: #F3F4F6;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #4F46E5;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

/* Lists and Tables */
QListWidget, QTableWidget {
    background-color: #111827;
    border: 1px solid #1F2937;
    border-radius: 6px;
    padding: 5px;
    color: #F3F4F6;
    gridline-color: #1F2937;
}

QTableWidget::item {
    padding: 8px;
}

QHeaderView::section {
    background-color: #1F2937;
    color: #9CA3AF;
    padding: 8px;
    border: 1px solid #111827;
    font-weight: bold;
}

/* Dialogs */
QDialog {
    background-color: #111827;
    border: 1px solid #1F2937;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #111827;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #374151;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4B5563;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
"""

LIGHT_STYLE = """
/* Light Theme Stylesheet */
QMainWindow {
    background-color: #F9FAFB; /* Pure Light Gray */
}

QWidget {
    color: #1F2937;
    font-family: "Segoe UI", -apple-system, Roboto, sans-serif;
    font-size: 13px;
}

/* Sidebar Navigation */
#SidebarFrame {
    background-color: #FFFFFF;
    border-right: 1px solid #E5E7EB;
}

#SidebarTitle {
    color: #4F46E5;
    font-size: 16px;
    font-weight: bold;
    padding: 15px 10px;
    border-bottom: 1px solid #E5E7EB;
}

#SidebarVersion {
    color: #9CA3AF;
    font-size: 10px;
    padding: 5px 10px;
}

QPushButton.SidebarBtn {
    background-color: transparent;
    color: #4B5563;
    text-align: left;
    padding: 12px 18px;
    border: none;
    border-left: 3px solid transparent;
    font-weight: 500;
}

QPushButton.SidebarBtn:hover {
    background-color: #F3F4F6;
    color: #111827;
}

QPushButton.SidebarBtn[active="true"] {
    background-color: #F3F4F6;
    color: #4F46E5;
    border-left: 3px solid #4F46E5;
}

/* Main Content Containers */
#ContentFrame {
    background-color: #F9FAFB;
}

#PageTitle {
    font-size: 22px;
    font-weight: bold;
    color: #111827;
    margin-bottom: 20px;
}

/* Cards */
QFrame.MetricCard {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 15px;
}

#CardTitle {
    font-size: 11px;
    font-weight: 600;
    color: #6B7280;
    text-transform: uppercase;
}

#CardValue {
    font-size: 24px;
    font-weight: bold;
    color: #111827;
    margin-top: 5px;
}

/* Buttons */
QPushButton.PrimaryBtn {
    background-color: #4F46E5;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton.PrimaryBtn:hover {
    background-color: #4338CA;
}

QPushButton.SecondaryBtn {
    background-color: #FFFFFF;
    color: #374151;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 8px 16px;
}

QPushButton.SecondaryBtn:hover {
    background-color: #F3F4F6;
}

QPushButton.WarningBtn {
    background-color: #EF4444;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
}

QPushButton.WarningBtn:hover {
    background-color: #DC2626;
}

/* Inputs and Forms */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    padding: 8px;
    color: #111827;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #4F46E5;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

/* Lists and Tables */
QListWidget, QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 6px;
    padding: 5px;
    color: #111827;
    gridline-color: #E5E7EB;
}

QTableWidget::item {
    padding: 8px;
}

QHeaderView::section {
    background-color: #F3F4F6;
    color: #4B5563;
    padding: 8px;
    border: 1px solid #E5E7EB;
    font-weight: bold;
}

/* Dialogs */
QDialog {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #F3F4F6;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #D1D5DB;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #9CA3AF;
}
"""
