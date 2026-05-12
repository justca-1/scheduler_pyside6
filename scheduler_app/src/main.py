import sys
import os
import logging
from pathlib import Path

# This line ensures Python can find the 'src' folder regardless of where you run it from
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QDialog
from database import init_db
from engine import DepEdValidator
from ui.main_window import MainWindow
from login_manager import init_auth_db, LoginDialog

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def main():
    # Set up logging to write to a file in the user's Documents folder
    log_dir = Path.home() / "Documents" / "CCNHS_Scheduler"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(log_dir / "scheduler.log"),
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    app = QApplication(sys.argv)
    app.setStyle("Fusion") # Consistent look across all PCs
    
    # Load QSS
    qss_file = resource_path(os.path.join("ui", "style.qss"))
    try:
        with open(qss_file, "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Warning: style.qss not found.")
    
    # Initialize DB and Engine
    db_path = init_db()
    engine = DepEdValidator(db_path)
    
    # Initialize Auth and show Login Dialog
    init_auth_db(db_path)
    login_dialog = LoginDialog(db_path)
    
    # Launch UI only if login is successful
    if login_dialog.exec() == QDialog.DialogCode.Accepted:
        window = MainWindow(engine)
        window.setup_session(getattr(login_dialog, 'logged_in_user', {}))
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()