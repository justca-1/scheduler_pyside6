"""
dialogs.py - Contains popup windows for user input.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QMessageBox, QCheckBox, QPushButton, 
    QLabel, QHBoxLayout, QComboBox, QTimeEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QCompleter
)
from PySide6.QtCore import QTime, Qt
from PySide6.QtGui import QColor, QBrush


class AddPersonDialog(QDialog):
    """A standard popup to capture a new person's name and role."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Person")
        self.setFixedWidth(300)
        
        # Layout
        self.layout = QVBoxLayout(self)
        
        # Input Fields
        self.layout.addWidget(QLabel("Full Name:"))
        self.name_input = QLineEdit()
        self.layout.addWidget(self.name_input)
        
        self.layout.addWidget(QLabel("Role (Optional):"))
        self.role_input = QLineEdit()
        self.layout.addWidget(self.role_input)
        
        # Buttons
        self.btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept) # Closes dialog and returns 'True'
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.btn_layout.addWidget(self.save_btn)
        self.btn_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(self.btn_layout)

    def get_data(self) -> dict:
        """Returns the collected input as a dictionary."""
        return {
            "name": self.name_input.text().strip().title(),
            "role": self.role_input.text().strip()
        }
    

class AddClassDialog(QDialog):
    """Popup to create a new class section (e.g. Grade 7 - Rizal)."""
    def __init__(self, default_grade=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Class")
        self.setFixedWidth(300)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Grade Level:"))
        self.grade_combo = QComboBox()
        self.grade_combo.addItems(["Grade 7", "Grade 8", "Grade 9", "Grade 10"])
        
        if default_grade:
            self.grade_combo.setCurrentText(default_grade)
            
        layout.addWidget(self.grade_combo)
        
        layout.addWidget(QLabel("Section Name:"))
        self.section_input = QLineEdit()
        self.section_input.setPlaceholderText("e.g. Rizal, Emerald, A")
        layout.addWidget(self.section_input)
        
        self.btn_save = QPushButton("Add Class")
        self.btn_save.clicked.connect(self.accept)
        layout.addWidget(self.btn_save)

    def get_data(self) -> dict:
        return {
            "grade": self.grade_combo.currentText(),
            "section": self.section_input.text().strip()
        }

class AddScheduleDialog(QDialog):
    def __init__(self, engine, persons: list, available_classes: list = None, edit_info: dict = None, parent=None):
        super().__init__(parent)
        self.engine = engine # Store engine for conflict checking
        self.edit_info = edit_info
        self.setWindowTitle("Add Busy Time (Multi-Day)" if not edit_info else "Edit Schedule Block")
        layout = QVBoxLayout(self)

        # 1. MULTI-DAY SELECTION
        layout.addWidget(QLabel("Select Days:"))
        days_layout = QHBoxLayout()
        self.day_boxes = {}
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            cb = QCheckBox(day)
            self.day_boxes[day] = cb
            cb.toggled.connect(self.check_conflicts) # Real-time check
            days_layout.addWidget(cb)
        layout.addLayout(days_layout)

        # 2. PERSON SELECTION
        layout.addWidget(QLabel("Select Person (Type to Search):"))
        self.person_selector = QComboBox()
        self.person_selector.setEditable(True)
        self.person_selector.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        for p in persons:
            self.person_selector.addItem(p['full_name'], p['person_id'])
            
        self.person_selector.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.person_selector.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.person_selector.currentIndexChanged.connect(self.check_conflicts)
        
        layout.addWidget(self.person_selector)

        layout.addWidget(QLabel("Select Grade Level:"))
        self.grade_selector = QComboBox()
        if available_classes:
            self.grade_selector.addItems(sorted(available_classes))
        else:
            self.grade_selector.addItems(["Grade 7", "Grade 8", "Grade 9", "Grade 10"])
        layout.addWidget(self.grade_selector)

        # NEW: Subject Input
        layout.addWidget(QLabel("Subject:"))
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("e.g. Math, Science (Optional)")
        layout.addWidget(self.subject_input)

        # NEW: Room Input
        layout.addWidget(QLabel("Room:"))
        self.room_input = QLineEdit()
        self.room_input.setPlaceholderText("e.g. Room 101, Lab A (Optional)")
        layout.addWidget(self.room_input)

        # 3. TIME SELECTION
        time_layout = QHBoxLayout()
        # ... (Keep your Start/End QTimeEdit code here) ...
        self.start_time = QTimeEdit(); self.start_time.setTime(QTime(9, 0))
        self.end_time = QTimeEdit(); self.end_time.setTime(QTime(10, 0))
        
        self.start_time.timeChanged.connect(self.check_conflicts)
        self.end_time.timeChanged.connect(self.check_conflicts)
        
        time_layout.addWidget(self.start_time); time_layout.addWidget(self.end_time)
        layout.addLayout(time_layout)
        
        # Conflict Feedback Label
        self.conflict_lbl = QLabel("")
        self.conflict_lbl.setStyleSheet("color: #E74C3C; font-size: 11px;")
        self.conflict_lbl.setWordWrap(True)
        layout.addWidget(self.conflict_lbl)

        self.btn_save = QPushButton("Save to Schedule")
        self.btn_save.clicked.connect(self.accept)
        layout.addWidget(self.btn_save)
        
        if self.edit_info:
            self.btn_save.setText("Update Schedule")
            
            day = self.edit_info.get('day')
            if day in self.day_boxes:
                self.day_boxes[day].setChecked(True)
                
            person_id = self.edit_info.get('person_id')
            idx = self.person_selector.findData(person_id)
            if idx >= 0:
                self.person_selector.setCurrentIndex(idx)
                
            grade = self.edit_info.get('grade_level')
            self.grade_selector.setCurrentText(grade)
            self.subject_input.setText(self.edit_info.get('subject', ''))
            self.room_input.setText(self.edit_info.get('room', ''))
            
            start = self.edit_info.get('start_time', '09:00')
            end = self.edit_info.get('end_time', '10:00')
            self.start_time.setTime(QTime.fromString(start, "HH:mm"))
            self.end_time.setTime(QTime.fromString(end, "HH:mm"))
            
        # Trigger initial validation to set default states (e.g., Grey-Out strategy)
        self.check_conflicts()

    def check_conflicts(self):
        """Real-time validation against the database."""
        # 1. Base Validation (Grey-Out Strategy)
        start_time_val = self.start_time.time()
        end_time_val = self.end_time.time()
        
        # Reset visual styles initially
        self.person_selector.setStyleSheet("")
        self.start_time.setStyleSheet("")
        self.end_time.setStyleSheet("")
        self.person_selector.setToolTip("")
        self.start_time.setToolTip("")
        self.end_time.setToolTip("")

        has_days = any(cb.isChecked() for cb in self.day_boxes.values())
        if not has_days:
            self.conflict_lbl.setText("Please select at least one day.")
            self.btn_save.setEnabled(False)
            return
            
        if end_time_val <= start_time_val:
            self.conflict_lbl.setText("End time must be after start time.")
            self.btn_save.setEnabled(False)
            return
            
        person_id = self.person_selector.currentData()
        if not person_id: 
            self.conflict_lbl.setText("Please select a person.")
            self.btn_save.setEnabled(False)
            return

        # 2. Database Conflict Detection
        start = start_time_val.toString("HH:mm")
        end = end_time_val.toString("HH:mm")
        
        conflicting_days = []
        tooltip_lines = []
        
        person_name = self.person_selector.currentText()
        
        # Check each selected day
        for day, cb in self.day_boxes.items():
            if cb.isChecked():
                # Query Engine for detailed conflicts
                conflicts = self.engine.get_conflict_details(person_id, day, start, end)
                if conflicts:
                    if self.edit_info:
                        conflicts = [c for c in conflicts if not (
                            c.get('grade_level') == self.edit_info.get('grade_level') and
                            c.get('start_time') == self.edit_info.get('start_time') and
                            c.get('end_time') == self.edit_info.get('end_time') and
                            c.get('day') == self.edit_info.get('day') and
                            c.get('person_id') == self.edit_info.get('person_id')
                        )]
                        
                    if conflicts:
                        conflicting_days.append(day)
                        for c in conflicts:
                            grade = c.get('grade_level', 'Unknown Class')
                            subject = c.get('subject') or 'No Subject'
                            c_start = c.get('start_time')
                            c_end = c.get('end_time')
                            room = c.get('room')
                            room_text = f" in {room}" if room else ""
                            
                            # Detailed "End Game" Conflict Message
                            tooltip_lines.append(f"⚠️ Conflict Detected: Teacher {person_name} is already{room_text} teaching {subject} ({grade}) from {c_start} to {c_end} on {day}.")

        # Visual Feedback
        if conflicting_days:
            is_dark = getattr(self.parent(), 'is_dark_mode', False)
            border_color = "#FF8A80" if is_dark else "#E74C3C"
            bg_color = "rgba(255, 138, 128, 0.1)" if is_dark else "rgba(231, 76, 60, 0.1)"
            style = f"border: 1px solid {border_color}; background-color: {bg_color};"
            
            # Show detailed error directly on the UI
            msg = "\n".join(tooltip_lines)
            self.conflict_lbl.setText(msg)
            self.conflict_lbl.setStyleSheet(f"color: {border_color}; font-size: 11px;")
            self.btn_save.setEnabled(False) # Prevent saving
            
            self.person_selector.setToolTip(msg)
            self.start_time.setToolTip(msg)
            self.end_time.setToolTip(msg)
            
            self.person_selector.setStyleSheet(style)
            self.start_time.setStyleSheet(style)
            self.end_time.setStyleSheet(style)
        else:
            self.conflict_lbl.setText("")
            self.btn_save.setEnabled(True)

    def get_data(self) -> dict:
        selected_days = [day for day, cb in self.day_boxes.items() if cb.isChecked()]
        
        if self.person_selector.currentIndex() == -1:
            QMessageBox.warning(self, "Validation", "Please select a valid person from the list.")
            return None

        if not selected_days:
            QMessageBox.warning(self, "Validation", "Please select at least one day.")
            return None
        if self.end_time.time() <= self.start_time.time():
            QMessageBox.warning(self, "Validation", "End time must be after start time.")
            return None

        return {
            "days": selected_days, # This is now a LIST
            "person_id": self.person_selector.currentData(),
            "grade_level": self.grade_selector.currentText(),
            "subject": self.subject_input.text().strip(),
            "room": self.room_input.text().strip(),
            "start": self.start_time.time().toString("HH:mm"),
            "end": self.end_time.time().toString("HH:mm")
        }

class PersonScheduleDialog(QDialog):
    """Displays a read-only weekly schedule for a specific person."""
    def __init__(self, engine, person_id, name, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle(f"Schedule: {name}")
        self.resize(900, 600)
        layout = QVBoxLayout(self)
        
        # Grid Setup
        try:
            from .main_window import FlexibleGridWidget
        except ImportError:
            from ui.main_window import FlexibleGridWidget
            
        self.grid = FlexibleGridWidget()
        self.grid.block_clicked.connect(self.handle_block_click)
        layout.addWidget(self.grid)
        
        # Load Data
        self.load_data(engine, person_id)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
    def handle_block_click(self, info):
        if not info: return
        
        msg = f"Class: {info.get('grade_level')}\n"
        msg += f"Subject: {info.get('subject')}\n"
        msg += f"Teacher: {info.get('full_name')}\n"
        msg += f"Time: {info.get('day')} {info.get('start_time')} - {info.get('end_time')}\n\n"
        msg += "What would you like to do with this schedule block?"
        
        box = QMessageBox(self)
        box.setWindowTitle("Manage Schedule")
        box.setText(msg)
        
        edit_btn = box.addButton("Edit", QMessageBox.ButtonRole.ActionRole)
        delete_btn = box.addButton("Delete", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        box.exec()
        
        if box.clickedButton() == delete_btn:
            success = self.engine.delete_specific_schedule(
                info.get('person_id'), info.get('day'), 
                info.get('start_time'), info.get('end_time'), 
                info.get('grade_level')
            )
            if success:
                self.load_data(self.engine, info.get('person_id'))
                if self.parent() and hasattr(self.parent(), 'refresh_all'):
                    self.parent().refresh_all()
        elif box.clickedButton() == edit_btn:
            p_list = self.engine.get_all_persons()
            all_options = []
            if self.parent() and hasattr(self.parent(), 'known_classes'):
                all_options = list(self.parent().known_classes)
                
            d = AddScheduleDialog(self.engine, p_list, available_classes=all_options, edit_info=info, parent=self)
            if d.exec():
                res = d.get_data()
                if res:
                    self.engine.delete_specific_schedule(
                        info.get('person_id'), info.get('day'), 
                        info.get('start_time'), info.get('end_time'), 
                        info.get('grade_level')
                    )
                    try:
                        from engine import ScheduleSlot
                    except ImportError:
                        from scheduler_app.src.engine import ScheduleSlot
                        
                    slots_to_add = []
                    for day_name in res['days']:
                        slots_to_add.append(ScheduleSlot(
                            person_id=res['person_id'],
                            day=day_name,
                            start_time=res['start'],
                            end_time=res['end'],
                            grade_level=res['grade_level'],
                            subject=res['subject'],
                            room=res['room']
                        ))
                    if self.engine.add_schedule_batch(slots_to_add):
                        self.load_data(self.engine, info.get('person_id'))
                        if self.parent() and hasattr(self.parent(), 'refresh_all'):
                            self.parent().refresh_all()

    def load_data(self, engine, person_id):
        from datetime import datetime
        
        schedules = engine.get_schedules_by_person(person_id)
        self.grid.clear_blocks()
        
        for info in schedules:
            day = info['day']
            start = info['start_time']
            end = info['end_time']
            subject = info.get('subject', '')
            room = info.get('room', '')
            grade_level = info.get('grade_level', '')
            
            try:
                t1 = datetime.strptime(start, "%H:%M")
                t2 = datetime.strptime(end, "%H:%M")
                duration_mins = int((t2 - t1).total_seconds() / 60)
            except Exception:
                continue
                
            display_text = grade_level if grade_level else "Unknown Class"
            if subject:
                display_text += f"\n{subject}"
            display_text += f"\n{duration_mins} mins"
            if room:
                display_text += f"\n[{room}]"
                
            val = sum(map(ord, grade_level))
            hue = (val * 137) % 360
            is_dark = getattr(self.parent(), 'is_dark_mode', False)
            
            bg_color = QColor.fromHsl(hue, 120 if is_dark else 100, 80 if is_dark else 230).name()
            text_color = "#FFFFFF" if is_dark else "#121212"
            
            tooltip = f"Class: {grade_level}\nSubject: {subject}\nRoom: {room}\nTime: {start} - {end}"
            
            self.grid.add_class(
                day_str=day,
                start_time=start,
                duration_mins=duration_mins,
                display_text=display_text,
                bg_color=bg_color,
                text_color=text_color,
                tooltip=tooltip,
                schedule_info=info
            )