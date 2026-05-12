import sqlite3
import pytest

from scheduler_app.src.engine import ScheduleEngine, ScheduleSlot

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
