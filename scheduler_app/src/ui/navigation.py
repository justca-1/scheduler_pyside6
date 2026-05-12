from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor, QBrush

class NavigationPanel(QTreeWidget):
    """
    A side panel that displays a hierarchical view of Grade Levels and Class Sections.
    Replaces the standard QListWidget sidebar.
    """
    
    # Signal to switch the main stack page (passes stack index)
    page_change_requested = Signal(int)
    
    # Signal to load a specific class/person schedule (passes database ID)
    class_id_selected = Signal(int)
    
    # Signal for when a section is selected
    section_selected = Signal(str)
    
    def __init__(self, engine):
        """
        Initialize the navigation panel.
        :param engine: Instance of ScheduleEngine to query data.
        """
        super().__init__()
        self.engine = engine
        
        # Map Grade Name -> Stack Index (Matches MainWindow order)
        self.grade_map = {
            "Grade 7": 1,
            "Grade 8": 2,
            "Grade 9": 3,
            "Grade 10": 4
        }
        
        self._setup_ui()
        self.refresh_navigation()

    def _setup_ui(self):
        """Configures the visual properties of the tree."""
        self.setHeaderLabel("Main Menu")
        self.setHeaderHidden(False)
        self.setIndentation(10)
        self.setRootIsDecorated(False)
        self.setAnimated(True)
        self.setFixedWidth(220)
        self.setExpandsOnDoubleClick(False) # Expand on single click, not double
        self.setFrameShape(QTreeWidget.Shape.NoFrame) # Removes the visual gap border
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus) # Removes the dotted focus border
        
        # Add a stylesheet to make the selected item and hover states look distinct
        self.setStyleSheet("""
            QTreeWidget::item {
                padding: 8px 5px;
                margin: 2px 10px;
                border-radius: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #3498DB;
                color: white;
            }
            QTreeWidget::item:hover:!selected {
                background-color: rgba(52, 152, 219, 0.2);
            }
        """)
        
        # Connect the click signal to our handler
        self.itemClicked.connect(self._on_item_clicked)

    def refresh_navigation(self, known_classes=None):
        """
        Queries the database and repopulates the tree.
        Call this method whenever a new class or person is added.
        """
        if known_classes is None:
            known_classes = set()
            
        # Save selected item before clearing
        selected_text = None
        selected_data = None
        if self.selectedItems():
            sel = self.selectedItems()[0]
            selected_text = sel.text(0)
            selected_data = sel.data(0, Qt.ItemDataRole.UserRole)

        self.clear()
        
        # --- 1. Staff Management (Fixed Node) ---
        staff_node = QTreeWidgetItem(self, ["👥 Staff Management"])
        staff_node.setData(0, Qt.ItemDataRole.UserRole, 0) 
        
        # --- 2. Conflict Report (Dedicated View) ---
        conflict_node = QTreeWidgetItem(self)
        conflict_node.setText(0, "⚠️ Conflict Report")
        conflict_node.setData(0, Qt.ItemDataRole.UserRole, 5) # Stack Index 5
        # Make it stand out with a soft red color
        conflict_node.setForeground(0, QBrush(QColor("#E74C3C")))

        # --- 3. Grade Level Parent Nodes ---
        self.grade_items = {}
        for grade, stack_idx in self.grade_map.items():
            parent = QTreeWidgetItem(self, [grade])
            # Store Stack Index for Page Switching
            parent.setData(0, Qt.ItemDataRole.UserRole, stack_idx)
            
            self.grade_items[grade] = parent
            
        # --- 5. Restore Selection ---
        if selected_text is not None:
            for i in range(self.topLevelItemCount()):
                top_item = self.topLevelItem(i)
                if top_item.text(0) == selected_text and top_item.data(0, Qt.ItemDataRole.UserRole) == selected_data:
                    self.setCurrentItem(top_item)
                    break

    def _on_item_clicked(self, item, column):
        """Handles item clicks. Distinguishes between Page Navigation and Schedule Loading."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if data is None:
            return

        if isinstance(data, str) and data.startswith("PERSON:"):
            person_id = int(data.replace("PERSON:", ""))
            self.class_id_selected.emit(person_id)
        elif isinstance(data, str) and data.startswith("SECTION:"):
            section_name = data.replace("SECTION:", "")
            self.section_selected.emit(section_name)
        elif isinstance(data, int):
            self.page_change_requested.emit(data)
