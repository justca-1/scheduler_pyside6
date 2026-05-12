"""
src/database.py - Handles the SQLite database creation and pathing.
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def get_db_path():
    """Returns the persistent path for the database in the user's Documents folder."""
    # Create a subfolder so we don't clutter their main Documents folder
    app_dir = Path.home() / "Documents" / "CCNHS_Scheduler"
    app_dir.mkdir(parents=True, exist_ok=True) 
    return str(app_dir / "school_scheduler.db")

def init_db(db_path=None):
    """Initializes the database schema using the centralized path logic."""
    if db_path is None:
        db_path = get_db_path()
        
    logging.info(f"DATABASE IS AT: {db_path}")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Execute external schema / migrations file
        schema_file = resource_path(os.path.join("migrations", "schema.sql"))
        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                cursor.executescript(f.read())
        except FileNotFoundError:
            logging.error(f"Could not find schema file at {schema_file}.")
                
        conn.commit()
    return db_path