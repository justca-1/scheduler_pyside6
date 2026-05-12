import sqlite3
import logging
from typing import List, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class ScheduleSlot:
    """Data Class defining the structure of a schedule entry for type safety."""
    person_id: int
    day: str
    start_time: str
    end_time: str
    grade_level: str
    subject: str = ""
    room: str = ""

    def __post_init__(self):
        """Enforces strict zero-padded HH:MM 24-hour format on initialization."""
        try:
            self.start_time = datetime.strptime(self.start_time.strip(), "%H:%M").strftime("%H:%M")
            self.end_time = datetime.strptime(self.end_time.strip(), "%H:%M").strftime("%H:%M")
        except ValueError:
            raise ValueError(f"Time must be in 24-hour HH:MM format. Got start='{self.start_time}', end='{self.end_time}'")

@dataclass
class ValidationResult:
    """Result object to provide context for assignment validation."""
    is_valid: bool
    error_message: str = ""
    conflict_type: str = ""

class ScheduleEngine:
    """
    The central logic engine for the scheduling system.
    Handles all SQLite interactions and conflict detection math.
    """

    def __init__(self, db_path: str):
        """Initializes the engine with the path to the local SQLite file."""
        self.db_path = db_path

    def _get_connection(self):
        """Helper to create a connection and enforce SQLite foreign keys."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    # --- PERSON MANAGEMENT ---

    def add_person(self, name: str, role: str = "") -> bool:
        """Adds a new person to the database."""
        if not name:
            return False
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check for duplicates (case-insensitive)
                cursor.execute("SELECT 1 FROM Person WHERE full_name = ? COLLATE NOCASE", (name,))
                if cursor.fetchone():
                    return False

                cursor.execute("INSERT INTO Person (full_name, role) VALUES (?, ?)", (name, role))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Database Error (add_person): {e}")
            return False

    def update_person_name(self, person_id: int, new_name: str) -> bool:
        """Updates the full name of a person."""
        if not new_name:
            return False
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE Person SET full_name = ? WHERE person_id = ?", (new_name, person_id))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Update Error (update_person_name): {e}")
            return False

    def get_all_persons(self) -> List[Dict]:
        """Fetches all registered persons as a list of dictionaries."""
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT person_id, full_name, role FROM Person")
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    def get_unique_grade_levels(self) -> List[str]:
        """Fetches all unique grade levels/sections currently in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT grade_level FROM Schedule WHERE grade_level IS NOT NULL AND grade_level != ''")
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error:
            return []

    # --- SCHEDULE MANAGEMENT ---

    def can_assign(self, slot: ScheduleSlot) -> ValidationResult:
        """
        Checks if the requested schedule slot is free from conflicts.
        Optimized to use a single SELECT query to reduce database hits.
        Returns a ValidationResult object.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                    SELECT person_id, room, grade_level
                    FROM Schedule
                    WHERE day = ? AND start_time < ? AND end_time > ?
                """
                cursor.execute(query, (slot.day, slot.end_time, slot.start_time))
                rows = cursor.fetchall()
                
                # Filter through the results in memory
                for row in rows:
                    if row['person_id'] == slot.person_id:
                        return ValidationResult(False, "Teacher is already booked at this time.", "TEACHER")
                    if slot.room and row['room'] == slot.room:
                        return ValidationResult(False, f"Room '{slot.room}' is already in use at this time.", "ROOM")
                    if slot.grade_level and row['grade_level'] == slot.grade_level:
                        return ValidationResult(False, f"Grade Level '{slot.grade_level}' already has a class at this time.", "GRADE")
                        
                return ValidationResult(True)
        except sqlite3.Error as e:
            logging.error(f"Conflict Check Error: {e}")
            return ValidationResult(False, f"Database error: {e}", "DATABASE")

    def can_assign_batch(self, slots: List[ScheduleSlot]) -> ValidationResult:
        """
        Batch validation to prevent N+1 query problems.
        Fetches existing schedules for the relevant days in ONE query,
        then checks all requested slots for conflicts entirely in memory.
        """
        if not slots:
            return ValidationResult(True)
            
        days = list(set(slot.day for slot in slots))
        # Dynamically create the (?, ?, ?) string depending on how many days we are checking
        placeholders = ', '.join('?' for _ in days)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = f"SELECT person_id, day, start_time, end_time, grade_level, room FROM Schedule WHERE day IN ({placeholders})"
                cursor.execute(query, days)
                existing_schedules = [dict(row) for row in cursor.fetchall()]
                
                # 1. Check against existing database schedules
                for slot in slots:
                    for existing in existing_schedules:
                        if slot.day == existing['day'] and slot.start_time < existing['end_time'] and slot.end_time > existing['start_time']:
                            if slot.person_id == existing['person_id']:
                                return ValidationResult(False, f"Teacher is already booked on {slot.day} at {slot.start_time}-{slot.end_time}.", "TEACHER")
                            if slot.room and slot.room == existing['room']:
                                return ValidationResult(False, f"Room '{slot.room}' is already in use on {slot.day} at {slot.start_time}-{slot.end_time}.", "ROOM")
                            if slot.grade_level and slot.grade_level == existing['grade_level']:
                                return ValidationResult(False, f"Grade Level '{slot.grade_level}' already has a class on {slot.day} at {slot.start_time}-{slot.end_time}.", "GRADE")
                                
                # 2. Check for internal overlaps within the new batch itself
                for i, slot1 in enumerate(slots):
                    for slot2 in slots[i+1:]:
                        if slot1.day == slot2.day and slot1.start_time < slot2.end_time and slot1.end_time > slot2.start_time:
                            if slot1.person_id == slot2.person_id:
                                return ValidationResult(False, "Conflict in new batch: Teacher has overlapping times.", "TEACHER")
                            if slot1.room and slot1.room == slot2.room:
                                return ValidationResult(False, f"Conflict in new batch: Room '{slot1.room}' overlaps.", "ROOM")
                            if slot1.grade_level and slot1.grade_level == slot2.grade_level:
                                return ValidationResult(False, f"Conflict in new batch: Grade '{slot1.grade_level}' overlaps.", "GRADE")
                                
                return ValidationResult(True)
        except sqlite3.Error as e:
            logging.error(f"Batch Conflict Check Error: {e}")
            return ValidationResult(False, f"Database error: {e}", "DATABASE")

    def get_conflict_details(self, person_id: int, day: str, start: str, end: str) -> List[Dict]:
        """
        Returns details of any existing schedules that overlap with the requested time slot.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = "SELECT * FROM Schedule WHERE person_id = ? AND day = ? AND start_time < ? AND end_time > ?"
                cursor.execute(query, (person_id, day, end, start))
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logging.error(f"Conflict Fetch Error: {e}")
            return []

    def add_schedule(self, slot: ScheduleSlot) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO Schedule (person_id, day, start_time, end_time, grade_level, subject, room) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (slot.person_id, slot.day, slot.start_time, slot.end_time, slot.grade_level, slot.subject, slot.room)
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            logging.error(f"Database Error (add_schedule): {e}")
            return False

    def add_schedule_batch(self, slots: List[ScheduleSlot]) -> bool:
        """
        Saves a batch of schedules in a single transaction.
        Significantly faster than calling add_schedule inside a for loop.
        """
        if not slots:
            return True
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            data = [(s.person_id, s.day, s.start_time, s.end_time, s.grade_level, s.subject, s.room) for s in slots]
            
            # executemany compiles the query once and applies it to the whole array
            cursor.executemany(
                "INSERT INTO Schedule (person_id, day, start_time, end_time, grade_level, subject, room) VALUES (?, ?, ?, ?, ?, ?, ?)",
                data
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logging.error(f"Batch Database Error: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_weekly_schedule_map(self, person_id=None) -> dict:
        """
        Maps (Day, Time) to a list of info DICTIONARIES.
        Returns: {(Day, TimeStr): [{'name': '...', ...}, ...]}
        Refactored to use datetime objects and interval overlap logic.
        If person_id is provided, filters for that specific person.
        """
        schedule_map = {}
        
        query = """
        SELECT p.full_name, p.role, s.day, s.start_time, s.end_time, s.grade_level, s.subject, s.room 
        FROM Schedule s
        JOIN Person p ON s.person_id = p.person_id
        """
        
        params = ()
        if person_id:
            query += " WHERE s.person_id = ?"
            params = (person_id,)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()

            # 1. Define UI Grid Slots (Intervals)
            # We generate 30-min slots from 06:00 to 19:00
            ui_slots = []
            current_dt = datetime.strptime("06:00", "%H:%M")
            end_dt = datetime.strptime("19:00", "%H:%M")
            
            while current_dt < end_dt:
                slot_start = current_dt.time()
                next_dt = current_dt + timedelta(minutes=30)
                slot_end = next_dt.time()
                
                # Key used by UI (e.g., "06:00")
                key_str = slot_start.strftime("%H:%M")
                ui_slots.append({
                    "key": key_str,
                    "start": slot_start,
                    "end": slot_end
                })
                current_dt = next_dt

            for row in rows:
                # Normalize Time: Convert DB strings to datetime.time
                try:
                    sched_start = datetime.strptime(row['start_time'], "%H:%M").time()
                    sched_end = datetime.strptime(row['end_time'], "%H:%M").time()
                except (ValueError, TypeError):
                    continue # Skip invalid time formats

                # PACKAGE AS A DICTIONARY (This fixes your crash!)
                info = {
                    "name": row['full_name'],
                    "role": row['role'] if row['role'] else "No Role",
                    "subject": row['subject'] if row['subject'] else "",
                    "room": row['room'] if row['room'] else "",
                    "range": f"{row['start_time']} - {row['end_time']}",
                    "grade_level": row['grade_level']
                }
                
                day = row['day']

                # Interval Comparison: Check overlap with every UI slot
                # Overlap Rule: (StartA < EndB) and (StartB < EndA)
                for slot in ui_slots:
                    if slot['start'] < sched_end and sched_start < slot['end']:
                        key = (day, slot['key'])
                        if key not in schedule_map:
                            schedule_map[key] = []
                        # Store the dictionary, not just the name string
                        schedule_map[key].append(info)
            
            return schedule_map
        except sqlite3.Error as e:
            logging.error(f"Database error in get_weekly_schedule_map: {e}")
            return {}

    def validate_workload(self, person_id: int) -> dict:
        """
        Calculates load per day to enforce the 6-hour (360 min) teaching limit.
        Returns: {'daily': {day: mins}, 'total': int, 'overloaded': [days], 'details': {day: [slots]}}
        """
        stats = {"daily": {}, "total": 0, "overloaded": [], "details": {}}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT day, start_time, end_time FROM Schedule WHERE person_id = ?", (person_id,))
                rows = cursor.fetchall()

            for row in rows:
                day = row['day']
                fmt = "%H:%M"
                # Parse times
                t1 = datetime.strptime(row['start_time'], fmt)
                t2 = datetime.strptime(row['end_time'], fmt)
                
                # Calculate duration in minutes
                duration = (t2 - t1).total_seconds() / 60
                
                stats["daily"][day] = stats["daily"].get(day, 0) + duration
                stats["total"] += duration
                
                if day not in stats["details"]:
                    stats["details"][day] = []
                stats["details"][day].append(f"{row['start_time']} - {row['end_time']}")

            # Flag days exceeding 6 hours (360 minutes)
            stats["overloaded"] = [d for d, m in stats["daily"].items() if m > 360]
            return stats
        except sqlite3.Error as e:
            logging.error(f"Workload Calc Error: {e}")
            return stats

    def clear_all_data(self) -> bool:
        """Wipes the database - Use with caution!"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Schedule")
            cursor.execute("DELETE FROM Person")
            conn.commit()
            return True
        except sqlite3.Error:
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()
    
    def delete_person(self, person_id: int) -> bool:
        """Removes a person and all their associated schedules."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # 1. Remove their schedules first (to maintain integrity)
            cursor.execute("DELETE FROM Schedule WHERE person_id = ?", (person_id,))
            # 2. Remove the person
            cursor.execute("DELETE FROM Person WHERE person_id = ?", (person_id,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logging.error(f"Delete Error: {e}")
            return False
        finally:
            if conn:
                conn.close()
        

    def clear_only_schedules(self) -> bool:
        """Deletes all rows from the Schedule table but keeps the Person table."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Schedule")
            conn.commit()
            return True
        except sqlite3.Error:
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def clear_person_schedule(self, person_id: int) -> bool:
        """Deletes all rows from the Schedule table for a specific person."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Schedule WHERE person_id = ?", (person_id,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logging.error(f"Clear Person Schedule Error: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_total_schedule_count(self) -> int:
        """Returns the total number of busy blocks (rows) in the Schedule table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM Schedule")
                return cursor.fetchone()[0]
        except sqlite3.Error:
            return 0
            
    def get_person_backup(self, person_id: int) -> dict:
        """Retrieves person details and their schedules for backup before delete."""
        data = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get Person
                cursor.execute("SELECT * FROM Person WHERE person_id = ?", (person_id,))
                p_row = cursor.fetchone()
                if not p_row: return None
                data['person'] = dict(p_row)
                
                # Get Schedules
                cursor.execute("SELECT * FROM Schedule WHERE person_id = ?", (person_id,))
                data['schedules'] = [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logging.error(f"Backup Error: {e}")
            return None
        return data

    def restore_person_data(self, backup_data: dict) -> bool:
        """Restores a person and their schedules from backup."""
        conn = None
        try:
            p = backup_data['person']
            schedules = backup_data['schedules']
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Restore Person (Force ID to maintain consistency)
            cursor.execute(
                "INSERT INTO Person (person_id, full_name, role) VALUES (?, ?, ?)",
                (p['person_id'], p['full_name'], p['role'])
            )
            
            # Restore Schedules
            for s in schedules:
                cursor.execute(
                    "INSERT INTO Schedule (person_id, day, start_time, end_time, grade_level, subject, room) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (p['person_id'], s['day'], s['start_time'], s['end_time'], s['grade_level'], s['subject'], s.get('room', ''))
                )
            conn.commit()
            return True
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logging.error(f"Restore Error: {e}")
            return False
        finally:
            if conn:
                conn.close()

class DepEdValidator(ScheduleEngine):
    """
    Encapsulates specific Department of Education (DepEd) rules.
    Inherits from ScheduleEngine to separate Data Logic from Business Rules.
    """

    def calculate_weighted_load(self, person_id: int) -> float:
        """
        Calculates load points using subject weights and precise time math.
        """
        # Dictionary Mapping: Subject weights
        weights = {
            "Math": 50,
            "Science": 50,
            "English": 40,
            "Filipino": 40
        }

        total_points = 0.0

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                # UPDATED: Use 'subject' from Schedule instead of 'role' from Person
                query = """
                SELECT subject, start_time, end_time 
                FROM Schedule
                WHERE person_id = ?
                """
                cursor.execute(query, (person_id,))
                rows = cursor.fetchall()

            for row in rows:
                # Normalize Time
                fmt = "%H:%M"
                t1 = datetime.strptime(row['start_time'], fmt)
                t2 = datetime.strptime(row['end_time'], fmt)

                # The Breakdown: Reliable time math
                duration_minutes = (t2 - t1).total_seconds() / 60
                duration_hours = duration_minutes / 60

                # The Breakdown: Dictionary Mapping with fallback
                subject_name = row['subject'] if row['subject'] else ""
                weight = weights.get(subject_name, 40)

                total_points += duration_hours * weight

            return total_points

        except sqlite3.Error as e:
            logging.error(f"DepEd Validation Error: {e}")
            return 0.0