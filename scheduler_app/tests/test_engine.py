import sqlite3
import pytest

from engine import ScheduleEngine, ScheduleSlot

def test_can_assign_success(engine):
    """Test that a completely free slot returns valid."""
    slot = ScheduleSlot(person_id=1, day="Monday", start_time="09:00", end_time="10:00", grade_level="Grade 1", room="Room 101")
    result = engine.can_assign(slot)
    assert result.is_valid is True

def test_can_assign_teacher_conflict(engine):
    # Manually add the FIRST class
    with sqlite3.connect(engine.db_path) as conn:
        conn.execute(
            "INSERT INTO Schedule (person_id, day, start_time, end_time, room) VALUES (?, ?, ?, ?, ?)",
            (1, "Monday", "08:00", "09:00", "Room 101")
        )
    
    # Now try to add a SECOND class that overlaps
    slot = ScheduleSlot(person_id=1, day="Monday", start_time="08:30", end_time="09:30", grade_level="Grade 2", room="Room 102")
    result = engine.can_assign(slot)
    
    assert result.is_valid is False
    assert result.conflict_type == "TEACHER"

def test_can_assign_room_conflict(engine):
    """Test that two different teachers cannot use the same room at the same time."""
    slot = ScheduleSlot(person_id=2, day="Monday", start_time="08:30", end_time="09:30", grade_level="Grade 2", room="Room 101")
    result = engine.can_assign(slot)
    assert result.is_valid is False
    assert result.conflict_type == "ROOM"

def test_can_assign_grade_conflict(engine):
    """Test that a single grade cannot have two classes at the same time."""
    slot = ScheduleSlot(person_id=2, day="Monday", start_time="08:30", end_time="09:30", grade_level="Grade 1", room="Room 102")
    result = engine.can_assign(slot)
    assert result.is_valid is False
    assert result.conflict_type == "GRADE"

def test_can_assign_batch_internal_conflict(engine):
    """Test that the batch processor catches internal conflicts before hitting the database."""
    slots = [
        ScheduleSlot(person_id=2, day="Tuesday", start_time="10:00", end_time="11:00", grade_level="Grade 3", room="Room 200"),
        ScheduleSlot(person_id=2, day="Tuesday", start_time="10:30", end_time="11:30", grade_level="Grade 4", room="Room 201")
    ]
    result = engine.can_assign_batch(slots)
    assert result.is_valid is False
    assert result.conflict_type == "TEACHER"

def test_can_assign_boundary_no_conflict(engine):
    """Test that back-to-back classes do not trigger a conflict."""
    with sqlite3.connect(engine.db_path) as conn:
        conn.execute(
            "INSERT INTO Schedule (person_id, day, start_time, end_time, room) VALUES (?, ?, ?, ?, ?)",
            (1, "Wednesday", "09:00", "10:00", "Room 101")
        )
    
    # Starts exactly when the previous slot ends
    slot_after = ScheduleSlot(person_id=1, day="Wednesday", start_time="10:00", end_time="11:00", grade_level="Grade 2", room="Room 102")
    assert engine.can_assign(slot_after).is_valid is True

    # Ends exactly when the next slot starts
    slot_before = ScheduleSlot(person_id=1, day="Wednesday", start_time="08:00", end_time="09:00", grade_level="Grade 2", room="Room 102")
    assert engine.can_assign(slot_before).is_valid is True

def test_partial_overlap_conflicts(engine):
    """Test various time overlap scenarios: partial, encapsulated, and engulfing."""
    with sqlite3.connect(engine.db_path) as conn:
        conn.execute(
            "INSERT INTO Schedule (person_id, day, start_time, end_time, room) VALUES (?, ?, ?, ?, ?)",
            (1, "Thursday", "09:00", "10:30", "Room 101")
        )
    
    # 1. Overlaps at the beginning (Starts before, ends during)
    slot1 = ScheduleSlot(person_id=1, day="Thursday", start_time="08:30", end_time="09:30", grade_level="Grade 2", room="Room 102")
    assert engine.can_assign(slot1).is_valid is False
    
    # 2. Overlaps at the end (Starts during, ends after)
    slot2 = ScheduleSlot(person_id=1, day="Thursday", start_time="10:00", end_time="11:00", grade_level="Grade 2", room="Room 102")
    assert engine.can_assign(slot2).is_valid is False
    
    # 3. Completely engulfed (Starts and ends during)
    slot3 = ScheduleSlot(person_id=1, day="Thursday", start_time="09:15", end_time="10:15", grade_level="Grade 2", room="Room 102")
    assert engine.can_assign(slot3).is_valid is False

    # 4. Completely engulfs the existing slot (Starts before, ends after)
    slot4 = ScheduleSlot(person_id=1, day="Thursday", start_time="08:00", end_time="11:00", grade_level="Grade 2", room="Room 102")
    assert engine.can_assign(slot4).is_valid is False

def test_get_conflict_details(engine):
    """Test that the engine returns accurate details for a conflicted time slot."""
    with sqlite3.connect(engine.db_path) as conn:
        conn.execute(
            "INSERT INTO Schedule (person_id, day, start_time, end_time, grade_level, subject, room) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "Friday", "13:00", "14:00", "Grade 7 - Rizal", "Math", "Room 301")
        )
    
    # Intentionally check a time block that overlaps by 30 mins
    conflicts = engine.get_conflict_details(1, "Friday", "13:30", "14:30")
    
    assert len(conflicts) == 1
    assert conflicts[0]['grade_level'] == "Grade 7 - Rizal"
    assert conflicts[0]['subject'] == "Math"
    assert conflicts[0]['room'] == "Room 301"
