import sys
import os
import pytest

# Ensure 'src' is in the python path so we can import our modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from ui.main_window import MainWindow

def test_calculate_duration_default_slot():
    """Test that the default 30-minute slot duration is used correctly."""
    # Span of 2 rows (e.g., Row 0 to Row 2) should be 60 minutes
    assert MainWindow.calculate_duration(0, 2) == 60

def test_calculate_duration_custom_slot():
    """Test that a custom slot duration calculates correctly."""
    # Span of 3 rows with 15-minute intervals should be 45 minutes
    assert MainWindow.calculate_duration(1, 4, slot_duration=15) == 45

def test_calculate_duration_zero_span():
    """Test that the same start and end index returns 0 minutes."""
    assert MainWindow.calculate_duration(3, 3) == 0