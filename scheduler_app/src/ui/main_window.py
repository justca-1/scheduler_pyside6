from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QSplitter, QLineEdit, QTabWidget, QListWidget, QListWidgetItem, QStackedWidget, QAbstractItemView,
    QGraphicsBlurEffect, QInputDialog, QMenu, QComboBox, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtGui import QColor, QBrush, QFont, QAction, QIcon
from PySide6.QtCore import Qt, Signal, QSize
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from login_manager import ChangePasswordDialog

try:
    from .dialogs import AddPersonDialog, AddScheduleDialog, PersonScheduleDialog, AddClassDialog
    from .navigation import NavigationPanel
except ImportError:
    from dialogs import AddPersonDialog, AddScheduleDialog, PersonScheduleDialog, AddClassDialog
    from navigation import NavigationPanel

class MainWindow(QMainWindow):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.setWindowTitle("Offline Scheduling System - Dashboard")
        self.resize(1200, 850)
        self.undo_stack = [] # Stores lists of backup data
        self.current_section_filter = None # Tracks active section filter
        
        # Pre-populate known classes with CCNHS sections
        self.known_classes = set([
            "Grade 7 - Rizal", "Grade 7 - Mabini", "Grade 7 - Bonifacio",
            "Grade 8 - Luna", "Grade 8 - Jacinto", "Grade 8 - Silang",
            "Grade 9 - Aquino", "Grade 9 - Del Pilar",
            "Grade 10 - Dagohoy", "Grade 10 - Lapu-Lapu"
        ])

        # Central Container
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Sidebar Container
        self.sidebar_container = QWidget()
        self.sidebar_layout = QVBoxLayout(self.sidebar_container)
        self.sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.sidebar = NavigationPanel(self.engine)
        self.sidebar.page_change_requested.connect(self.change_page)
        self.sidebar.class_id_selected.connect(self.load_schedule)
        self.sidebar.section_selected.connect(self.on_sidebar_section_selected)
        self.sidebar_layout.addWidget(self.sidebar)
        
        self.main_layout.addWidget(self.sidebar_container, 0) # 0 stretch = stay fixed size

        # Right Content Area (Top bar + Main Stack)
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)

        # Top Bar for Theme Button
        self.top_bar = QHBoxLayout()
        self.top_bar.setContentsMargins(0, 10, 10, 0) # Add padding just for the button
        self.top_bar.addStretch() # Pushes the button to the right
        
        self.change_pwd_btn = QPushButton(" Change Password")
        self.change_pwd_btn.setFixedSize(140, 36)
        self.change_pwd_btn.setToolTip("Update Admin Credentials")
        self.change_pwd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.change_pwd_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB; 
                color: white; 
                font-weight: bold; 
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #2980B9; }
        """)
        self.change_pwd_btn.clicked.connect(self.open_change_password_dialog)
        self.change_pwd_btn.hide() # Hidden by default, shown after auth
        self.top_bar.addWidget(self.change_pwd_btn)

        self.theme_btn = QPushButton(" Dark Mode")
        self.theme_btn.setFixedSize(120, 36) # Larger size to accommodate text and icon
        self.theme_btn.setToolTip("Toggle Dark/Light Mode")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setStyleSheet("""
            QPushButton {
                background-color: #2C3E50; 
                color: white; 
                font-weight: bold; 
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #1A252F; }
        """)
        
        # Load initial moon icon from an 'icons' folder next to this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.theme_btn.setIcon(QIcon(os.path.join(base_dir, "icons", "moon.png"))) # Change to .svg if using SVGs
        self.theme_btn.setIconSize(QSize(20, 20)) # Scales the icon cleanly
        
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.top_bar.addWidget(self.theme_btn)
        self.right_layout.addLayout(self.top_bar)

        # Main Content Area
        self.main_stack = QStackedWidget()
        self.right_layout.addWidget(self.main_stack)
        
        self.main_layout.addWidget(self.right_container, 1) # 1 stretch = take up all remaining space

        # Initialize Sections
        self.init_person_management_ui()
        self.init_schedule_grid_ui()
        self.init_conflict_report_ui() # NEW: dedicated report area

        # Add the Status Bar at the very bottom
        self.statusBar().showMessage(f"Database Loaded: {self.engine.db_path}")

        self.is_dark_mode = False

        # Initial Data Load
        self.refresh_all()
        
        # Select first item by default
        self.change_page(0)

    def setup_session(self, user_data):
        """Configures UI based on the authenticated user."""
        self.current_user = user_data
        
        # Explicitly trigger visibility update after authentication
        self.change_pwd_btn.show()

    def change_page(self, index):
        # Clear filter if navigating directly to a main page via Category click
        self.current_section_filter = None
        
        # Reset all combos to "All Sections" without immediately triggering a refresh
        for view_data in self.grade_views.values():
            if 'stack' in view_data:
                view_data['stack'].setCurrentIndex(0)
            if 'delete_btn' in view_data:
                view_data['delete_btn'].setEnabled(False)
                
        self.main_stack.setCurrentIndex(index)
        # Force grid refresh in case we were just viewing a filtered section
        self.refresh_all()
        
    def on_sidebar_section_selected(self, section_name):
        """Handles when a specific section is clicked in the sidebar."""
        for grade, view_data in self.grade_views.items():
            if section_name.startswith(grade):
                # Switch to this grade's page directly to avoid clearing the filter
                stack_idx = self.sidebar.grade_map.get(grade)
                if stack_idx is not None:
                    self.main_stack.setCurrentIndex(stack_idx)
                    
                # Apply the filter and switch to the Timetable (Index 1)
                self.current_section_filter = section_name
                
                if 'stack' in view_data:
                    view_data['stack'].setCurrentIndex(1)
                if 'delete_btn' in view_data:
                    view_data['delete_btn'].setEnabled(True)
                
                self.refresh_all()
                break

    def on_section_list_item_clicked(self, item, grade_name):
        section_data = item.data(Qt.ItemDataRole.UserRole)
        self.on_sidebar_section_selected(section_data)

    def show_message(self, text, duration=3000):
        """Helper to show temporary messages (like 'Saved!') on the status bar."""
        self.statusBar().showMessage(text, duration)

    def toggle_theme(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.theme_btn.setIcon(QIcon(os.path.join(base_dir, "icons", "sun.svg")))
            self.theme_btn.setText(" Light Mode")
            self.theme_btn.setToolTip("Toggle Light Mode")
            self.apply_theme("dark_style.qss")
        else:
            self.theme_btn.setIcon(QIcon(os.path.join(base_dir, "icons", "moon.svg")))
            self.theme_btn.setText(" Dark Mode")
            self.theme_btn.setToolTip("Toggle Dark Mode")
            self.apply_theme("light_style.qss")
        self.update_theme_colors()  # Instantly update existing item colors

    def open_change_password_dialog(self):
        username = getattr(self, 'current_user', {}).get('username', 'admin')
        dialog = ChangePasswordDialog(self.engine.db_path, username, self)
        self._exec_with_blur(dialog)

    def apply_theme(self, stylesheet_name):
        import os
        import logging
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, stylesheet_name)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    from PySide6.QtWidgets import QApplication
                    QApplication.instance().setStyleSheet(f.read())
            else:
                logging.error(f"Stylesheet {stylesheet_name} not found at {path}!")
        except Exception as e:
            logging.error(f"Could not load theme {stylesheet_name}: {e}")

    def update_theme_colors(self):
        """Updates the colors of existing UI elements without doing a full data refresh."""
        is_dark = getattr(self, 'is_dark_mode', False)
        
        # 1. Update Conflict Report Table
        conflict_text_color = QColor("#FF8A80" if is_dark else "#C0392B")
        for r in range(self.conflict_table.rowCount()):
            item = self.conflict_table.item(r, 3)
            if item and "Double Booked:" in item.text():
                item.setForeground(QBrush(conflict_text_color))
                
        # 2. Update Grade Views (Schedule Grids)
        conflict_bg_color = QColor("#FF8A80" if is_dark else "#FF7043")
        text_color = QColor("#FFFFFF") if is_dark else QColor("#2c3e50")
        
        for view_data in self.grade_views.values():
            grid = view_data['grid']
            for r in range(grid.rowCount()):
                for c in range(grid.columnCount()):
                    item = grid.item(r, c)
                    if item:
                        text = item.text()
                        if "⚠️ CONFLICT" in text:
                            item.setBackground(QBrush(conflict_bg_color))
                            item.setForeground(QBrush(QColor("white")))
                        else:
                            # Extract subject from tooltip to determine original color
                            tooltip = item.toolTip()
                            subject = ""
                            if tooltip and tooltip.startswith("Subject: "):
                                subject = tooltip.split("\n")[0].replace("Subject: ", "")
                            
                            bg_color = self.get_subject_color(subject)
                            item.setBackground(QBrush(bg_color))
                            item.setForeground(QBrush(text_color))

    def init_person_management_ui(self):
        self.staff_tab = QWidget()
        self.staff_tab.setObjectName("Card")
        # Setting layout margins creates the 'float' effect over the cream background
        layout = QVBoxLayout(self.staff_tab)
        layout.setContentsMargins(0, 20, 20, 20) # 0 left margin to connect to side panel
        layout.setSpacing(15)

        # --- STATUS CARDS (Calculated Widgets) ---
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)

        def create_stat_card(title, color="#2ECC71"):
            card = QWidget()
            card.setObjectName("Card")
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(15, 15, 15, 15)
            
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("color: gray; font-size: 12px; font-weight: bold;")
            
            v_lbl = QLabel("0")
            v_lbl.setFont(QFont("Arial", 20, QFont.Weight.Bold))
            v_lbl.setStyleSheet(f"color: {color};")
            
            c_layout.addWidget(t_lbl)
            c_layout.addWidget(v_lbl)
            stats_layout.addWidget(card)
            return v_lbl

        self.stat_staff = create_stat_card("TOTAL STAFF")
        self.stat_teacher_conflicts = create_stat_card("TEACHER CONFLICTS", "#E74C3C")
        self.stat_class_conflicts = create_stat_card("CLASS CONFLICTS", "#E74C3C")
        self.stat_schedules = create_stat_card("ACTIVE SCHEDULES")

        layout.addLayout(stats_layout)

        section_label = QLabel("Registered Persons & Management")
        section_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(section_label)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search by name or role...")
        self.search_bar.setFixedWidth(500)
        self.search_bar.textChanged.connect(self.filter_people_table)
        layout.addWidget(self.search_bar)

        # Action Buttons (Horizontal)
        action_layout = QHBoxLayout()
        self.add_person_btn = QPushButton("Add New Person")
        self.add_person_btn.clicked.connect(self.open_add_person_dialog)
        
        self.add_schedule_btn = QPushButton("Assign Busy Time")
        self.add_schedule_btn.clicked.connect(self.open_add_schedule_dialog)
        
        action_layout.addWidget(self.add_person_btn)
        action_layout.addWidget(self.add_schedule_btn)
        action_layout.addStretch()
        layout.addLayout(action_layout)

        header_layout = QHBoxLayout()
        
        self.people_table = QTableWidget()
        self.people_table.setColumnCount(2)
        self.people_table.setHorizontalHeaderLabels(["ID", "Full Name"])
        self.people_table.setFixedHeight(180) 
        self.people_table.setFrameShape(QTableWidget.Shape.NoFrame) # Removes the border
        
        # Enable multi-row selection
        self.people_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.people_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        # Hide the vertical header (row numbers) as it is redundant and often tight
        self.people_table.verticalHeader().setVisible(False)
        
        header = self.people_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.people_table.setColumnWidth(0, 60)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.people_table.cellDoubleClicked.connect(self.on_person_double_clicked)
        
        # Context Menu
        self.people_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.people_table.customContextMenuRequested.connect(self.show_context_menu)
        
        header_layout.addWidget(self.people_table)

        # Button Sidebar
        btn_vbox = QVBoxLayout()
        
        # The Missing Link: The Delete Button
        self.delete_person_btn = QPushButton("Delete Selected")
        self.delete_person_btn.clicked.connect(self.delete_selected_person)
        
        btn_vbox.addWidget(self.delete_person_btn)
        
        self.undo_btn = QPushButton("Undo Delete")
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.undo_last_delete)
        btn_vbox.addWidget(self.undo_btn)
        
        btn_vbox.addStretch()
        
        header_layout.addLayout(btn_vbox)
        layout.addLayout(header_layout)

        # In init_person_management_ui, add the Print button:
        self.print_btn = QPushButton("Print to CSV (Excel)")
        self.print_btn.clicked.connect(self.export_to_csv)
        btn_vbox.addWidget(self.print_btn)

        self.clear_sched_btn = QPushButton("Clear All Schedules")
        self.clear_sched_btn.setStyleSheet("color: orange;")
        self.clear_sched_btn.clicked.connect(self.clear_schedules)
        btn_vbox.addWidget(self.clear_sched_btn)

        # Add to Stack and Sidebar
        self.main_stack.addWidget(self.staff_tab)

    def clear_schedules(self):
        confirm = QMessageBox.warning(
            self, "Clear All Schedules", 
            "Are you sure you want to delete ALL schedule entries?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            # We need a simple method in the engine for this
            if self.engine.clear_only_schedules():
                self.refresh_all()
                self.show_message("All schedules cleared.")

    def export_to_csv(self):
        """Exports the current grid exactly as seen to a CSV file."""
        import csv
        from PySide6.QtWidgets import QFileDialog

        # Get the currently visible grid from the tabs
        current_grid = self.main_stack.currentWidget()
        
        # Handle the Grade View container case (if it's a widget with a grid inside)
        if isinstance(current_grid, QWidget) and not isinstance(current_grid, QTableWidget):
            current_grid = current_grid.findChild(QTableWidget)

        if not current_grid or not isinstance(current_grid, QTableWidget):
            self.show_message("No schedule grid available to export.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Export Schedule", "", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    # Write Headers
                    headers = ["Time"] + ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                    writer.writerow(headers)

                    # Write Rows
                    for r in range(current_grid.rowCount()):
                        row_data = [current_grid.verticalHeaderItem(r).text()]
                        for c in range(current_grid.columnCount()):
                            item = current_grid.item(r, c)
                            row_data.append(item.text().replace("\n", " | ") if item else "")
                        writer.writerow(row_data)
                self.show_message("Export successful!")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Could not save file: {e}")

    def init_schedule_grid_ui(self):
        """Bottom section for the Weekly Matrix."""
        self.grade_views = {} # Stores { 'Grade 7': {'combo': ..., 'grid': ...}, ... }
        
        self.time_slots = [f"{h:02d}:{m:02d}" for h in range(6, 19) for m in (0, 30)]
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        
        # 1. All Grades (Grade 7-10) with Dropdowns
        for i in range(7, 11):
            grade_name = f"Grade {i}"
            
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 10, 10) # 0 left margin to connect grid to side panel
            
            # --- Top bar for filtering ---
            top_layout = QHBoxLayout()
            top_layout.setContentsMargins(20, 10, 0, 10)
            
            title_lbl = QLabel(f"{grade_name} Schedule")
            title_lbl.setFont(QFont("Arial", 14, QFont.Weight.Bold))
            
            add_class_btn = QPushButton("Add Class")
            add_class_btn.clicked.connect(lambda checked, g=grade_name: self.open_add_class_dialog(g))
            
            delete_class_btn = QPushButton("Delete Class")
            delete_class_btn.setStyleSheet("color: #E74C3C;") # Destructive action color (Red)
            delete_class_btn.setEnabled(False) # Disabled by default since "All Sections" is active
            delete_class_btn.clicked.connect(lambda checked, g=grade_name: self.delete_selected_class(g))
            
            filter_combo = QComboBox(container)
            filter_combo.setFixedWidth(200)
            filter_combo.addItem("All Sections", userData=None)
            filter_combo.currentIndexChanged.connect(lambda idx, g=grade_name: self.on_combo_filter_changed(g))
            filter_combo.hide()
            
            top_layout.addWidget(title_lbl)
            top_layout.addWidget(add_class_btn)
            top_layout.addWidget(delete_class_btn)
            top_layout.addStretch()
            
            layout.addLayout(top_layout)

            # --- Stacked Widget for this Grade ---
            grade_stack = QStackedWidget()
            layout.addWidget(grade_stack)
            
            # Page 0: Sections List
            sections_page = QWidget()
            sections_layout = QVBoxLayout(sections_page)
            sections_layout.setContentsMargins(20, 0, 20, 20)
            
            sections_label = QLabel("Select a section to view its timetable:")
            sections_label.setStyleSheet("color: gray; font-size: 14px;")
            sections_layout.addWidget(sections_label)
            
            sections_list = QListWidget()
            sections_list.setFrameShape(QListWidget.Shape.NoFrame)
            sections_list.itemClicked.connect(lambda item, g=grade_name: self.on_section_list_item_clicked(item, g))
            sections_layout.addWidget(sections_list)
            grade_stack.addWidget(sections_page)
            
            # Page 1: Timetable
            timetable_page = QWidget()
            timetable_layout = QVBoxLayout(timetable_page)
            timetable_layout.setContentsMargins(0, 0, 0, 0)
            
            grid = QTableWidget()
            self._setup_grid(grid, days, self.time_slots)
            timetable_layout.addWidget(grid)
            grade_stack.addWidget(timetable_page)
            
            self.main_stack.addWidget(container)
            
            self.grade_views[grade_name] = {
                'grid': grid, 
                'stack': grade_stack,
                'list': sections_list,
                'delete_btn': delete_class_btn
            }
            
    def init_conflict_report_ui(self):
        """Page Index 5: The dedicated Conflict Report."""
        self.conflict_page = QWidget()
        layout = QVBoxLayout(self.conflict_page)
        layout.setContentsMargins(0, 20, 20, 20) # 0 left margin to connect to side panel
        
        title = QLabel("⚠️ System Conflict Report")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #C0392B;")
        layout.addWidget(title)
        
        desc = QLabel("The following double-bookings were detected in the database:")
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        self.conflict_table = QTableWidget()
        self.conflict_table.setColumnCount(4)
        self.conflict_table.setHorizontalHeaderLabels(["Who / Class", "Day", "Time Slot", "Conflict Details"])
        self.conflict_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.conflict_table.verticalHeader().setVisible(False)
        self.conflict_table.setFrameShape(QTableWidget.Shape.NoFrame) # Removes the border
        
        layout.addWidget(self.conflict_table)
        
        self.main_stack.addWidget(self.conflict_page)

    def _setup_grid(self, grid, days, time_slots):
        """Helper to configure a schedule table widget."""
        grid.setColumnCount(len(days))
        grid.setHorizontalHeaderLabels(days)
        grid.setRowCount(len(time_slots))
        grid.setVerticalHeaderLabels(time_slots)
        grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        grid.verticalHeader().setDefaultSectionSize(65) # Increase this value to make rows taller
        grid.verticalHeader().setFixedWidth(70) # Increase this value to make the time column wider
        grid.setShowGrid(False) # Hide default grid lines for card-like look
        grid.setFrameShape(QTableWidget.Shape.NoFrame) # Snaps perfectly to the side panel

    # --- ACTION METHODS ---

    def delete_selected_person(self):
        """Removes the highlighted person(s) from the system."""
        selected_rows = sorted(set(index.row() for index in self.people_table.selectedIndexes()))
        
        if not selected_rows:
            QMessageBox.warning(self, "Selection Required", "Please select at least one person in the table.")
            return

        persons_to_delete = []
        for row in selected_rows:
            id_item = self.people_table.item(row, 0)
            name_item = self.people_table.item(row, 1)
            if id_item and name_item:
                p_id = int(id_item.text())
                p_name = name_item.text().replace("⚠️ ", "")
                persons_to_delete.append((p_id, p_name))

        msg = f"Delete {persons_to_delete[0][1]} and all their schedules?" if len(persons_to_delete) == 1 else f"Delete {len(persons_to_delete)} selected people and all their schedules?"

        confirm = QMessageBox.question(
            self, "Confirm Delete", 
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        # 1. Prepare Backup
        batch_backup = []
        for p_id, _ in persons_to_delete:
            data = self.engine.get_person_backup(p_id)
            if data:
                batch_backup.append(data)

        if confirm == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            for p_id, _ in persons_to_delete:
                if self.engine.delete_person(p_id):
                    deleted_count += 1
            
            if deleted_count > 0:
                # 2. Push to Undo Stack
                if batch_backup:
                    self.undo_stack.append(batch_backup)
                    self.update_undo_button()
                
                self.refresh_all()
                self.show_message(f"Deleted {deleted_count} people.")

    def show_context_menu(self, pos):
        """Displays a right-click menu for staff actions."""
        index = self.people_table.indexAt(pos)
        if not index.isValid():
            return

        menu = QMenu(self)
        
        # Rename Action
        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(lambda: self.handle_rename_context(index.row()))
        menu.addAction(rename_action)
        
        # View Schedule Action
        view_action = QAction("View Schedule", self)
        view_action.triggered.connect(lambda: self.on_person_double_clicked(index.row(), 0))
        menu.addAction(view_action)

        clear_sched_action = QAction("Clear This Teacher's Schedule", self)
        clear_sched_action.triggered.connect(lambda: self.clear_teacher_schedule(index.row()))
        menu.addAction(clear_sched_action)

        menu.exec(self.people_table.viewport().mapToGlobal(pos))

    def handle_rename_context(self, row):
        """Helper to trigger rename from context menu."""
        id_item = self.people_table.item(row, 0)
        name_item = self.people_table.item(row, 1)
        if id_item and name_item:
            p_id = int(id_item.text())
            name = name_item.text().replace("⚠️ ", "")
            self.open_rename_dialog(p_id, name)

    def clear_teacher_schedule(self, row):
        """Clears all schedules for the selected teacher."""
        id_item = self.people_table.item(row, 0)
        name_item = self.people_table.item(row, 1)
        if id_item and name_item:
            p_id = int(id_item.text())
            name = name_item.text().replace("⚠️ ", "")
            
            confirm = QMessageBox.warning(
                self, "Clear Schedule", 
                f"Are you sure you want to clear all schedules for {name}?\n\nThis action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.Yes:
                if self.engine.clear_person_schedule(p_id):
                    self.refresh_all()
                    self.show_message(f"Cleared schedules for {name}.")
                else:
                    QMessageBox.critical(self, "Error", "Failed to clear the schedule from the database.")

    def open_rename_dialog(self, person_id, current_name):
        """Opens a blurred popup to rename the person."""
        # Apply Blur
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(10)
        self.central_widget.setGraphicsEffect(blur)
        
        # Get New Name
        new_name, ok = QInputDialog.getText(
            self, "Rename Staff", 
            f"Rename '{current_name}' to:", 
            text=current_name
        )
        
        # Remove Blur
        self.central_widget.setGraphicsEffect(None)
        
        if ok and new_name:
            new_name = new_name.strip()
            if not new_name:
                QMessageBox.warning(self, "Invalid Name", "Name cannot be empty.")
                return
                
            if self.engine.update_person_name(person_id, new_name):
                self.show_message(f"Renamed to {new_name}")
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Update Failed", "Could not update name in database.")

    def _exec_with_blur(self, dialog):
        """Helper to execute a dialog with a background blur effect."""
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(10)
        self.central_widget.setGraphicsEffect(blur)
        res = dialog.exec()
        self.central_widget.setGraphicsEffect(None)
        return res

    def undo_last_delete(self):
        """Restores the last batch of deleted people."""
        if not self.undo_stack: return
        
        batch_backup = self.undo_stack.pop()
        restored_count = 0
        
        for data in batch_backup:
            if self.engine.restore_person_data(data):
                restored_count += 1
        
        self.refresh_all()
        self.update_undo_button()
        self.show_message(f"Restored {restored_count} people.")

    def update_undo_button(self):
        count = len(self.undo_stack)
        self.undo_btn.setEnabled(count > 0)
        self.undo_btn.setText(f"Undo Delete ({count})" if count > 0 else "Undo Delete")

    def load_schedule(self, person_id):
        """Loads the schedule dialog for a specific person ID."""
        # 1. Find Person Name
        persons = self.engine.get_all_persons()
        person = next((p for p in persons if p['person_id'] == person_id), None)
        
        if not person:
            return
            
        name = person['full_name']
        
        # 2. Check Overload & Popup
        stats = self.engine.validate_workload(person_id)
        if stats['overloaded']:
            msg = f"{name} is overloaded!\n"
            msg += f"Total Teaching: {int(stats['total'])} minutes\n\n"
            msg += "Breakdown of Overloaded Days:\n"
            for day in stats['overloaded']:
                day_total = int(stats['daily'][day])
                msg += f"--- {day} ({day_total} mins) ---\n"
            QMessageBox.warning(self, "Workload Alert", msg)
            
        # 3. Open Dialog
        dlg = PersonScheduleDialog(self.engine, person_id, name, self)
        self._exec_with_blur(dlg)

    def on_person_double_clicked(self, row, col):
        """Handles clicking a user: Checks overload and shows schedule."""
        id_item = self.people_table.item(row, 0)
        
        if not id_item:
            return
            
        p_id = int(id_item.text())
        self.load_schedule(p_id)

    def refresh_all(self):
        """
        Synchronizes the UI with the latest database state.
        Updates the person list and the weekly matrix.
        """
        # Block signals to prevent itemChanged from firing during population
        self.people_table.blockSignals(True)
        
        # --- 0. REFRESH NAVIGATION TREE ---
        self.sidebar.refresh_navigation(self.known_classes)
        
        # --- 1. REFRESH PERSON TABLE ---
        persons = self.engine.get_all_persons()
        
        # Sort persons alphabetically by their full name (case-insensitive)
        persons.sort(key=lambda p: p['full_name'].lower())
        
        self.people_table.setRowCount(len(persons))
        
        for i, p in enumerate(persons):
            # Column 0: ID
            id_item = QTableWidgetItem(str(p['person_id']))
            id_item.setFlags(id_item.flags() ^ Qt.ItemFlag.ItemIsEditable) # Non-editable
            self.people_table.setItem(i, 0, id_item)
            
            # Column 1: Full Name
            # --- NEW FEATURE: WORKLOAD VALIDATION ---
            stats = self.engine.validate_workload(p['person_id'])
            display_name = p['full_name']
            
            # Visual Cue for Overload
            if stats['overloaded']:
                display_name = f"⚠️ {p['full_name']}"
            
            name_item = QTableWidgetItem(display_name)
            
            # Tooltip details
            tip = f"Total Teaching: {int(stats['total'])} mins"
            if stats['overloaded']:
                tip += f"\n⚠️ OVERLOADED on: {', '.join(stats['overloaded'])}"
                name_item.setForeground(QBrush(QColor("#C0392B"))) # Red text
                name_item.setFont(QFont("Arial", weight=QFont.Weight.Bold))
            
            name_item.setToolTip(tip)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.people_table.setItem(i, 1, name_item)
            
        self.people_table.blockSignals(False)

        # --- 2. REFRESH SCHEDULE GRID ---
        # Fix: Populate known_classes from DB to ensure persistence
        db_classes = self.engine.get_unique_grade_levels()
        self.known_classes.update(db_classes)

        # Get the detailed map: {(Day, Time): [info_dict1, info_dict2]}
        s_map = self.engine.get_weekly_schedule_map()
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        
        # 1. Update Known Classes & Distribute to Grades
        # We categorize classes into buckets: "Grade 7", "Grade 8", etc.
        grade_buckets = { grade: set() for grade in self.grade_views.keys() }
        
        all_classes = set(self.known_classes)
        for infos in s_map.values():
            for info in infos:
                if info.get('grade_level'):
                    all_classes.add(info['grade_level'])
                    self.known_classes.add(info['grade_level'])

        for c_name in all_classes:
            # Safely assign the class to the correct grade bucket based directly on UI keys
            for grade in self.grade_views.keys():
                if c_name.startswith(grade):
                    grade_buckets[grade].add(c_name)
                    break

        # --- Update Section Dropdowns ---
        for grade, view_data in self.grade_views.items():
            sec_list = view_data.get('list')
            stack = view_data.get('stack')
            delete_btn = view_data.get('delete_btn')
            if sec_list and stack:
                
                sec_list.blockSignals(True)
                sec_list.clear()
                
                sections = sorted(list(grade_buckets.get(grade, set())))
                for sec in sections:
                    if " - " in sec:
                        display_name = sec.split(" - ", 1)[1]
                    else:
                        display_name = sec.replace(grade, "").strip(" -")
                        if not display_name:
                            display_name = sec
                            
                    list_item = QListWidgetItem(display_name)
                    list_item.setData(Qt.ItemDataRole.UserRole, sec)
                    list_item.setFont(QFont("Arial", 12))
                    sec_list.addItem(list_item)
                
                if self.current_section_filter and self.current_section_filter.startswith(grade):
                    stack.setCurrentIndex(1)
                    if delete_btn: delete_btn.setEnabled(True)
                else:
                    stack.setCurrentIndex(0)
                    if delete_btn: delete_btn.setEnabled(False)

                sec_list.blockSignals(False)
        
        # 2. Update Grids for 7-10
        for grade in self.grade_views.keys():
            # Apply filter if the current filter belongs to this grade
            filter_to_apply = None
            if self.current_section_filter and self.current_section_filter.startswith(grade):
                filter_to_apply = self.current_section_filter
            self.refresh_grade_grid(grade, section_filter=filter_to_apply)
            
        # 3. Update Conflict Report Tab & Global Stats
        # Using the raw map gives us true database conflicts (ignoring visual overlaps from "All Sections")
        teacher_conflicts, class_conflicts = self.refresh_conflict_table(s_map)
        total_conflicts = teacher_conflicts + class_conflicts

        # Update the Status Bar with the conflict tally
        status_msg = f"Database: {self.engine.db_path} | ⚠️ Conflicts: {total_conflicts}"
        self.statusBar().showMessage(status_msg)

        # Update Status Cards
        self.stat_staff.setText(str(len(persons)))
        self.stat_teacher_conflicts.setText(str(teacher_conflicts))
        self.stat_class_conflicts.setText(str(class_conflicts))
        self.stat_schedules.setText(str(self.engine.get_total_schedule_count()))

    def get_subject_color(self, subject):
        """Generates a consistent pastel color for a subject string."""
        if not subject:
            return QColor("#2D2D2D") if getattr(self, 'is_dark_mode', False) else QColor("#FFFDF5")
        
        # Deterministic hash so "Math" is always the same color
        val = sum(map(ord, subject))
        hue = (val * 137) % 360 
        
        if getattr(self, 'is_dark_mode', False):
            return QColor.fromHsl(hue, 120, 80)
        else:
            return QColor.fromHsl(hue, 100, 230)

    @staticmethod
    def calculate_duration(start_index: int, end_index: int, slot_duration: int = 30) -> int:
        """
        Calculates the duration in minutes based on grid row indices.
        
        Args:
            start_index (int): The grid row index where the class starts.
            end_index (int): The grid row index where the class ends.
            slot_duration (int): The duration of a single slot in minutes (default is 30).
            
        Returns:
            int: The total duration in minutes.
        """
        duration_minutes = (end_index - start_index) * slot_duration
        return duration_minutes

    def refresh_conflict_table(self, s_map):
        """Populates the conflict report table and returns conflict counts."""
        self.conflict_table.setRowCount(0)
        
        row_idx = 0
        teacher_conflicts = 0
        class_conflicts = 0
        
        for (day, time_slot), infos in s_map.items():
            
            # 1. Check for Class Double Bookings (Same Grade Level & Section)
            grade_groups = {}
            for info in infos:
                g = info.get('grade_level', 'Unknown')
                if g not in grade_groups: grade_groups[g] = []
                grade_groups[g].append(info)
            
            for g, group in grade_groups.items():
                if len(group) > 1:
                    class_conflicts += 1
                    self.conflict_table.insertRow(row_idx)
                    self.conflict_table.setItem(row_idx, 0, QTableWidgetItem(f"Class: {g}"))
                    self.conflict_table.setItem(row_idx, 1, QTableWidgetItem(str(day)))
                    self.conflict_table.setItem(row_idx, 2, QTableWidgetItem(str(time_slot)))
                    names = ", ".join([x['name'] for x in group])
                    msg = f"Double Booked: {names}"
                    item = QTableWidgetItem(msg)
                    is_dark = getattr(self, 'is_dark_mode', False)
                    item.setForeground(QBrush(QColor("#FF8A80" if is_dark else "#C0392B")))
                    self.conflict_table.setItem(row_idx, 3, item)
                    row_idx += 1
                    
            # 2. Check for Teacher Double Bookings (Same Teacher Name)
            teacher_groups = {}
            for info in infos:
                t = info.get('name', 'Unknown Teacher')
                if t not in teacher_groups: teacher_groups[t] = []
                teacher_groups[t].append(info)
                
            for t, group in teacher_groups.items():
                if len(group) > 1:
                    teacher_conflicts += 1
                    self.conflict_table.insertRow(row_idx)
                    self.conflict_table.setItem(row_idx, 0, QTableWidgetItem(f"Teacher: {t}"))
                    self.conflict_table.setItem(row_idx, 1, QTableWidgetItem(str(day)))
                    self.conflict_table.setItem(row_idx, 2, QTableWidgetItem(str(time_slot)))
                    
                    classes = ", ".join([x.get('grade_level', 'Unknown') for x in group])
                    msg = f"Double Booked: {classes}"
                    item = QTableWidgetItem(msg)
                    is_dark = getattr(self, 'is_dark_mode', False)
                    item.setForeground(QBrush(QColor("#FF8A80" if is_dark else "#C0392B")))
                    self.conflict_table.setItem(row_idx, 3, item)
                    row_idx += 1

        return teacher_conflicts, class_conflicts

    def refresh_grade_grid(self, grade_key, section_filter=None):
        """Populates the grid for a specific grade view, optionally filtered by section."""
        from datetime import datetime
        view_data = self.grade_views.get(grade_key)
        if not view_data: return 0
        
        grid = view_data['grid']
        
        # Clear content AND spans (merges)
        grid.clearContents()
        grid.clearSpans()
        
        s_map = self.engine.get_weekly_schedule_map()
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        
        local_conflicts = 0

        # Process Column by Column (Day by Day) to allow vertical merging
        for col, d_val in enumerate(days):
            row = 0
            while row < len(self.time_slots):
                t_val = self.time_slots[row]
                
                all_infos = s_map.get((d_val, t_val), [])
                
                if section_filter:
                    busy_infos = [info for info in all_infos if section_filter == info.get('grade_level', '')]
                else:
                    busy_infos = [info for info in all_infos if grade_key in info.get('grade_level', '')]
                
                if not busy_infos:
                    row += 1
                    continue

                info = busy_infos[0]
                subject = info.get('subject', '')
                room = info.get('room', '')
                name = info['name']
                is_conflict = len(busy_infos) > 1
                
                # --- 1. Calculate Merge Span ---
                # Look ahead to see if the next slots are the exact same class
                span_height = 1
                if not is_conflict:
                    for next_r in range(row + 1, len(self.time_slots)):
                        next_t = self.time_slots[next_r]
                        next_infos = s_map.get((d_val, next_t), [])
                        if section_filter:
                            next_busy = [i for i in next_infos if section_filter == i.get('grade_level', '')]
                        else:
                            next_busy = [i for i in next_infos if grade_key in i.get('grade_level', '')]
                            
                        # Stop if empty, conflict, or different subject/teacher
                        if len(next_busy) == 1 and \
                           next_busy[0]['name'] == name and \
                           next_busy[0].get('subject', '') == subject:
                            span_height += 1
                        else:
                            break

                # --- 2. Determine Content ---
                if is_conflict:
                    display_text = "⚠️ CONFLICT\n" + "\n".join([f"{i['name']} ({i.get('range', '')})" for i in busy_infos])
                else:
                    duration_mins = self.calculate_duration(row, row + span_height)

                    if duration_mins > 0:
                        time_range = f"{duration_mins} mins"
                    else:
                        time_range = info.get('range', '')

                    display_text = subject if subject else name
                    if subject and name:
                        display_text += f"\n({name})"
                    if time_range:
                        display_text += f"\n{time_range}"
                    if room:
                        display_text += f"\n[{room}]"

                item = QTableWidgetItem(display_text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                
                # --- 3. Styling & Color Coding ---
                if is_conflict:
                    is_dark = getattr(self, 'is_dark_mode', False)
                    conflict_bg_color = "#FF8A80" if is_dark else "#FF7043"
                    item.setBackground(QBrush(QColor(conflict_bg_color)))
                    item.setForeground(QBrush(QColor("white")))
                    item.setToolTip("⚠️ Multiple people scheduled")
                    local_conflicts += 1
                else:
                    # Dynamic Color based on Subject
                    bg_color = self.get_subject_color(subject)
                    item.setBackground(QBrush(bg_color))
                    text_color = QColor("#FFFFFF") if getattr(self, 'is_dark_mode', False) else QColor("#2c3e50")
                    item.setForeground(QBrush(text_color)) # Dark text
                    item.setFont(QFont("Arial", weight=QFont.Weight.Bold))
                    original_time = info.get('range', '')
                    item.setToolTip(f"Subject: {subject}\nTeacher: {name}\nRoom: {room}\nTime: {original_time}")
                
                grid.setItem(row, col, item)

                # --- 4. Apply Merge Span ---
                if span_height > 1:
                    grid.setSpan(row, col, span_height, 1)
                
                # Skip the rows we just handled
                row += span_height
        
        return local_conflicts

    def open_add_person_dialog(self):
        d = AddPersonDialog(self)
        if self._exec_with_blur(d):
            data = d.get_data()
            if self.engine.add_person(data['name'], data['role']):
                self.refresh_all()
            else:
                QMessageBox.warning(self, "Error", f"Could not add '{data['name']}'.\nThis name already exists.")

    def open_add_class_dialog(self, default_grade=None):
        """Adds a new class to the dropdown list."""
        d = AddClassDialog(default_grade=default_grade, parent=self)
        if self._exec_with_blur(d):
            data = d.get_data()
            grade = data['grade']
            section = data['section']
            
            if not section:
                QMessageBox.warning(self, "Input Error", "Section name cannot be empty.")
                return

            # Construct the full class name (e.g., "Grade 7 - Rizal")
            full_class_name = f"{grade} - {section}"
            
            if full_class_name not in self.known_classes:
                self.known_classes.add(full_class_name)
                self.refresh_all()
                self.show_message(f"Class '{full_class_name}' added.")
            else:
                self.show_message(f"Class '{full_class_name}' already exists.")

    def delete_selected_class(self, grade_name):
        """Deletes the currently selected class section from the dropdown."""
        section_data = self.current_section_filter
        
        if not section_data or not section_data.startswith(grade_name):
            QMessageBox.warning(self, "Select Class", "Please select a specific section to delete.")
            return
            
        confirm = QMessageBox.warning(
            self, "Confirm Delete", 
            f"Are you sure you want to delete the class '{section_data}'?\n\nThis will also remove all scheduled times for this class. This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                import sqlite3
                with sqlite3.connect(self.engine.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM Schedule WHERE grade_level = ?", (section_data,))
                    conn.commit()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Database error: {e}")
                return
                
            if section_data in self.known_classes:
                self.known_classes.remove(section_data)
                
            if self.current_section_filter == section_data:
                self.current_section_filter = None
                
            self.refresh_all()
            self.show_message(f"Class '{section_data}' deleted.")

    def open_add_schedule_dialog(self):
        p_list = self.engine.get_all_persons()
        if not p_list: 
            QMessageBox.warning(self, "Error", "Add a person first!")
            return
        
        # Pass 'self.engine' so dialog can perform real-time checking
        # Pass available classes to the dialog
        all_options = list(self.known_classes)
        d = AddScheduleDialog(self.engine, p_list, available_classes=all_options, parent=self)
        
        if self._exec_with_blur(d):
            res = d.get_data()
            if res is None: 
                return

            from engine import ScheduleSlot
            slots_to_add = []
            for day_name in res['days']:
                slot = ScheduleSlot(
                    person_id=res['person_id'],
                    day=day_name,
                    start_time=res['start'],
                    end_time=res['end'],
                    grade_level=res['grade_level'],
                    subject=res['subject'],
                    room=res['room']
                )
                slots_to_add.append(slot)
            
            if self.engine.add_schedule_batch(slots_to_add):
                self.show_message(f"Successfully added {len(slots_to_add)} days.")
                
                # Bridge the Model-View gap visually by navigating to the updated section
                target_section = res.get('grade_level')
                if target_section:
                    self.on_sidebar_section_selected(target_section)
                    
                self.refresh_all()

    def filter_people_table(self, text):
        """Hides rows in the people table that don't match the search text."""
        for i in range(self.people_table.rowCount()):
            name_item = self.people_table.item(i, 1) # Column 1 is 'Full Name'
            if name_item:
                # Show the row if the text matches (case-insensitive)
                is_visible = text.lower() in name_item.text().lower()
                self.people_table.setRowHidden(i, not is_visible)
                