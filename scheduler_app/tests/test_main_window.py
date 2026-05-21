import sys
import os

class DummyMeta(type):
    def __getattr__(cls, name):
        return Dummy
    def __or__(cls, other):
        return Dummy
    def __and__(cls, other):
        return Dummy
    def __xor__(cls, other):
        return Dummy
    def __invert__(cls):
        return Dummy

class Dummy(metaclass=DummyMeta):
    def __init__(self, *args, **kwargs):
        pass
    def __call__(self, *args, **kwargs):
        return Dummy()
    def __getattr__(self, name):
        return Dummy()
    def __or__(self, other):
        return self
    def __and__(self, other):
        return self
    def __xor__(self, other):
        return self
    def __invert__(self):
        return self

class MockModule:
    def __getattr__(self, name):
        return Dummy

# Robust PySide6 Mocking to avoid AttributeError on inherited classes
sys.modules['PySide6'] = MockModule()
sys.modules['PySide6.QtWidgets'] = MockModule()
sys.modules['PySide6.QtGui'] = MockModule()
sys.modules['PySide6.QtCore'] = MockModule()

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