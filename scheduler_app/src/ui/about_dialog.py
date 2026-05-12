import os
import sys
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap

def get_base_path():
    """Get absolute path to resources, works for dev and for PyInstaller."""
    try:
        return sys._MEIPASS
    except Exception:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About CCNHS Scheduler")
        self.setFixedSize(400, 300)
        self.setModal(True) # Blocks input to the main window while open
        
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # App Title
        title_label = QLabel("CCNHS Scheduler")
        title_font = QFont("Arial", 16, QFont.Weight.Bold)
        title_label.setFont(title_font)
        
        # App Version
        version_label = QLabel("Version 1.0.0")
        
        # Credits
        credits_label = QLabel(
            "Designed and Developed for\nCity Comprehensive National High School.\n\n"
            "© 2026 CCNHS Scheduler Team."
        )
        credits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Close Button
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.accept)
        
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(credits_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)