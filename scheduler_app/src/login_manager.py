import sqlite3
import hashlib
import os
import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QCursor

# --- DATABASE & AUTHENTICATION LOGIC ---

def hash_password(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
    """Securely hashes a password using PBKDF2."""
    if salt is None:
        # Generate a new random salt for new passwords
        salt = os.urandom(16)
    
    # 100,000 iterations of SHA-256 is a strong standard
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return pwd_hash, salt

def init_auth_db(db_path: str):
    """Creates the Admins table and a default user if empty."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS Admins (
                            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE,
                            password_hash BLOB,
                            salt BLOB
                          )''')
        
        # Check if we need to create a default admin
        cursor.execute("SELECT COUNT(*) FROM Admins")
        if cursor.fetchone()[0] == 0:
            default_hash, default_salt = hash_password("admin")
            cursor.execute(
                "INSERT INTO Admins (username, password_hash, salt) VALUES (?, ?, ?)",
                ("admin", default_hash, default_salt)
            )
        conn.commit()

def verify_login(db_path: str, username: str, password: str) -> bool:
    """Verifies a username and password against the database."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash, salt FROM Admins WHERE username = ?", (username,))
            row = cursor.fetchone()
            
            if row is None:
                return False # Username not found
                
            stored_hash, stored_salt = row
            # Hash the input password with the stored salt
            input_hash, _ = hash_password(password, stored_salt)
            
            # Compare the hashes
            return hmac_compare(stored_hash, input_hash)
    except sqlite3.Error as e:
        logging.error(f"Database error during login: {e}")
        return False

def hmac_compare(a: bytes, b: bytes) -> bool:
    """Safely compares two hashes to prevent timing attacks."""
    import hmac
    return hmac.compare_digest(a, b)

def change_password(db_path: str, username: str, new_password: str) -> bool:
    """Updates the password for a given user."""
    try:
        new_hash, new_salt = hash_password(new_password)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE Admins SET password_hash = ?, salt = ? WHERE username = ?", (new_hash, new_salt, username))
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error as e:
        logging.error(f"Database error during password change: {e}")
        return False


# --- UI LOGIC ---

class LoginDialog(QDialog):
    """A standalone login screen matching the app's color palette."""
    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self.db_path = db_path
        
        self.setWindowTitle("System Access")
        self.setFixedSize(350, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Use the app's established light mode aesthetic
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
            QLabel {
                font-family: Arial;
                color: #2C3E50;
            }
            QLineEdit {
                padding: 10px;
                border: 1px solid #BDC3C7;
                border-radius: 5px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #3498DB;
            }
            QPushButton#loginBtn {
                background-color: #2ECC71;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 10px;
                border-radius: 5px;
                border: none;
            }
            QPushButton#loginBtn:hover {
                background-color: #27AE60;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        title = QLabel("Admin Login")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password) # Masks the characters
        layout.addWidget(self.password_input)
        
        self.login_btn = QPushButton("Secure Login")
        self.login_btn.setObjectName("loginBtn")
        self.login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_btn.clicked.connect(self.attempt_login)
        layout.addWidget(self.login_btn)
        
    def attempt_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password.")
            return
            
        if verify_login(self.db_path, username, password):
            self.logged_in_user = {"username": username}
            self.accept() # Unlocks the app
        else:
            QMessageBox.critical(self, "Access Denied", "Invalid username or password.")
            self.password_input.clear()
            self.password_input.setFocus()

class ChangePasswordDialog(QDialog):
    """A standalone dialog to update the admin password."""
    def __init__(self, db_path: str, username: str = "admin", parent=None):
        super().__init__(parent)
        self.db_path = db_path
        self.username = username
        
        self.setWindowTitle("Change Admin Password")
        self.setFixedSize(350, 360)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.setup_ui()
        
    def setup_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #F8F9FA; }
            QLabel { font-family: Arial; color: #2C3E50; }
            QLineEdit { padding: 10px; border: 1px solid #BDC3C7; border-radius: 5px; font-size: 14px; background-color: white; }
            QLineEdit:focus { border: 2px solid #3498DB; }
            QPushButton#updateBtn { background-color: #3498DB; color: white; font-weight: bold; font-size: 14px; padding: 10px; border-radius: 5px; border: none; }
            QPushButton#updateBtn:hover { background-color: #2980B9; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        title = QLabel("Update Credentials")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        self.old_pwd_input = QLineEdit()
        self.old_pwd_input.setPlaceholderText("Current Password")
        self.old_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.old_pwd_input)
        
        self.new_pwd_input = QLineEdit()
        self.new_pwd_input.setPlaceholderText("New Password")
        self.new_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.new_pwd_input)
        
        self.confirm_pwd_input = QLineEdit()
        self.confirm_pwd_input.setPlaceholderText("Confirm New Password")
        self.confirm_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.confirm_pwd_input)
        
        self.update_btn = QPushButton("Update Password")
        self.update_btn.setObjectName("updateBtn")
        self.update_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.update_btn.clicked.connect(self.attempt_change)
        layout.addWidget(self.update_btn)
        
    def attempt_change(self):
        old_pwd = self.old_pwd_input.text().strip()
        new_pwd = self.new_pwd_input.text().strip()
        confirm_pwd = self.confirm_pwd_input.text().strip()
        
        if not old_pwd or not new_pwd or not confirm_pwd:
            QMessageBox.warning(self, "Error", "All fields are required.")
            return
            
        if new_pwd != confirm_pwd:
            QMessageBox.warning(self, "Error", "New passwords do not match.")
            self.new_pwd_input.clear()
            self.confirm_pwd_input.clear()
            self.new_pwd_input.setFocus()
            return
            
        # --- Password Complexity Check ---
        if len(new_pwd) < 8 or not any(c.isupper() for c in new_pwd) or not any(c.isdigit() for c in new_pwd):
            QMessageBox.warning(
                self, 
                "Weak Password", 
                "Password must be at least 8 characters long, contain at least 1 uppercase letter, and 1 number."
            )
            self.new_pwd_input.clear()
            self.confirm_pwd_input.clear()
            self.new_pwd_input.setFocus()
            return

        if not verify_login(self.db_path, self.username, old_pwd):
            QMessageBox.critical(self, "Access Denied", "Incorrect current password.")
            self.old_pwd_input.clear()
            self.old_pwd_input.setFocus()
            return
            
        if change_password(self.db_path, self.username, new_pwd):
            QMessageBox.information(self, "Success", "Your password has been successfully updated!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "A database error occurred while updating the password.")
