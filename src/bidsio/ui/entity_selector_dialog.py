"""
Entity Selector Dialog.

This dialog allows users to select which entity values to include in an export.
"""

from PySide6.QtWidgets import QDialog, QListWidgetItem
from PySide6.QtCore import Qt, Slot

from bidsio.infrastructure.logging_config import get_logger
from bidsio.ui.forms.entity_selector_dialog_ui import Ui_EntitySelectorDialog


logger = get_logger(__name__)


class EntitySelectorDialog(QDialog):
    """
    Dialog for selecting entity values.
    
    Displays a searchable list of entity values with checkboxes.
    All items are checked by default.
    """
    
    def __init__(self, entity_name: str, entity_values: list[str], initial_selection: list[str] | None = None, parent=None):
        """
        Initialize the entity selector dialog.
        
        Args:
            entity_name: Display name of the entity (e.g., "Subjects", "Tasks").
            entity_values: List of all available entity values.
            initial_selection: List of initially selected values (defaults to all).
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self._entity_name = entity_name
        self._entity_values = sorted(entity_values)
        self._initial_selection = initial_selection if initial_selection is not None else self._entity_values.copy()
        
        self._setup_ui()
        self._connect_signals()
        self._populate_list()
        
        logger.debug(f"EntitySelectorDialog initialized for {entity_name} with {len(entity_values)} values")
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.ui = Ui_EntitySelectorDialog()
        self.ui.setupUi(self)
        
        # Update title
        self.setWindowTitle(f"Select {self._entity_name}")
        self.ui.titleLabel.setText(f"Select {self._entity_name.lower()} to include in export:")
    
    def _connect_signals(self):
        """Connect UI signals to slots."""
        self.ui.selectAllButton.clicked.connect(self._select_all)
        self.ui.deselectAllButton.clicked.connect(self._deselect_all)
        self.ui.searchLineEdit.textChanged.connect(self._filter_list)
        self.ui.entityListWidget.itemChanged.connect(self._update_selection_count)
    
    def _populate_list(self):
        """Populate the list widget with entity values."""
        self.ui.entityListWidget.clear()
        
        for value in self._entity_values:
            item = QListWidgetItem(value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            
            # Check if this value should be initially selected
            if value in self._initial_selection:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            
            self.ui.entityListWidget.addItem(item)
        
        self._update_selection_count()
    
    @Slot()
    def _select_all(self):
        """Select all visible items in the list."""
        for i in range(self.ui.entityListWidget.count()):
            item = self.ui.entityListWidget.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked)
    
    @Slot()
    def _deselect_all(self):
        """Deselect all visible items in the list."""
        for i in range(self.ui.entityListWidget.count()):
            item = self.ui.entityListWidget.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Unchecked)
    
    @Slot(str)
    def _filter_list(self, search_text: str):
        """
        Filter the list based on search text.
        
        Args:
            search_text: The search query.
        """
        search_lower = search_text.lower()
        
        for i in range(self.ui.entityListWidget.count()):
            item = self.ui.entityListWidget.item(i)
            text = item.text().lower()
            
            # Show item if it matches the search
            item.setHidden(search_lower not in text)
        
        self._update_selection_count()
    
    @Slot()
    def _update_selection_count(self):
        """Update the selection count label."""
        selected_count = 0
        total_count = 0
        
        for i in range(self.ui.entityListWidget.count()):
            item = self.ui.entityListWidget.item(i)
            if not item.isHidden():
                total_count += 1
                if item.checkState() == Qt.CheckState.Checked:
                    selected_count += 1
        
        self.ui.selectionCountLabel.setText(f"{selected_count} of {total_count} items selected")
    
    def get_selected_values(self) -> list[str]:
        """
        Get the list of selected entity values.
        
        Returns:
            List of selected values.
        """
        selected = []
        
        for i in range(self.ui.entityListWidget.count()):
            item = self.ui.entityListWidget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        
        return selected
