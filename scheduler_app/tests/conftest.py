import sys
import os
import pytest
import sqlite3

# Ensure 'src' is in the python path so we can import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from engine import ScheduleEngine

@pytest.fixture
def temp_db_path(tmp_path):
    """Creates a unique temporary database file for each test instead of memory."""
    db_file = tmp_path / "test_school_scheduler.db"
    return str(db_file)

@pytest.fixture
def engine(temp_db_path):
    """Initialize the engine and create the necessary tables."""
    test_engine = ScheduleEngine(temp_db_path)
    
    with sqlite3.connect(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE Person (person_id INTEGER PRIMARY KEY, full_name TEXT, role TEXT)''')
        cursor.execute('''CREATE TABLE Schedule (
                          schedule_id INTEGER PRIMARY KEY AUTOINCREMENT, 
                          person_id INTEGER, 
                          day TEXT, 
                          start_time TEXT, 
                          end_time TEXT, 
                          grade_level TEXT, 
                          subject TEXT,
                          room TEXT)''')
                          
        # Seed the database with exactly one existing schedule:
        cursor.execute("INSERT INTO Person (person_id, full_name, role) VALUES (1, 'John Doe', 'Teacher')")
        cursor.execute("INSERT INTO Schedule (person_id, day, start_time, end_time, grade_level, subject, room) VALUES (1, 'Monday', '08:00', '09:00', 'Grade 1', 'Math', 'Room 101')")
        conn.commit()
        
    return test_engine