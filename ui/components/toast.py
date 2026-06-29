import logging
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation

logger = logging.getLogger("app")

class ToastNotification(QWidget):
    def __init__(self, message: str, parent: QWidget, duration: int = 3000, success: bool = True):
        """
        Create an animated non-blocking notification banner.
        
        Args:
            message: Text to display.
            parent: Parent QWidget (usually the QMainWindow to align coordinates).
            duration: Visibility length in ms.
            success: True for green success popup, False for red error popup.
        """
        super().__init__(parent)
        self.parent_widget = parent
        self.duration = duration
        
        # Set window flags to float overlay
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        
        self.label = QLabel(message)
        self.label.setWordWrap(True)
        
        # Premium Slate theme palette colors
        bg_color = "#10B981" if success else "#EF4444" # Emerald vs Rose
        self.label.setStyleSheet(f"""
            background-color: {bg_color};
            color: #FFFFFF;
            border-radius: 8px;
            padding: 12px 20px;
            font-size: 13px;
            font-weight: 600;
        """)
        
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        self.adjustSize()
        self.reposition()
        
        # Opacity animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        
        # Auto fadeout timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)
        
        self.show()
        self.anim.start()
        self.timer.start(self.duration)
        
        # Connect parent resize event to update position
        if hasattr(self.parent_widget, "resized"):
            # If parent window registers a resized signal, we update positions
            pass

    def reposition(self) -> None:
        """Position at the bottom-right corner of the parent frame."""
        if self.parent_widget:
            p_width = self.parent_widget.width()
            p_height = self.parent_widget.height()
            x = p_width - self.width() - 25
            y = p_height - self.height() - 25
            self.move(x, y)

    def fade_out(self) -> None:
        """Fade out and close widget."""
        self.anim.setDirection(QPropertyAnimation.Backward)
        self.anim.finished.connect(self.close)
        self.anim.start()
