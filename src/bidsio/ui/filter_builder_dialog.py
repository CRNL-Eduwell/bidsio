"""
Filter Builder Dialog.

This dialog allows users to build complex filter expressions for filtering subjects.
Currently implements Simple mode; Advanced mode with logical operations is planned.
"""

import json
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QListWidget, QMessageBox, QFileDialog,
    QInputDialog, QCheckBox, QListWidgetItem, QDialogButtonBox,
    QTreeWidgetItem, QMenu
)
from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QIcon, QKeySequence, QShortcut

from bidsio.infrastructure.logging_config import get_logger
from bidsio.infrastructure.paths import get_filter_presets_directory
from bidsio.core.models import (
    BIDSDataset,
    FilterCondition,
    LogicalOperation,
    SubjectIdFilter,
    ModalityFilter,
    ParticipantAttributeFilter,
    EntityFilter,
    ChannelAttributeFilter,
    ElectrodeAttributeFilter
)
from bidsio.ui.forms.filter_builder_dialog_ui import Ui_FilterBuilderDialog


logger = get_logger(__name__)


class FilterBuilderDialog(QDialog):
    """
    Dialog for building filter expressions.
    
    Currently implements Simple mode with basic filters.
    
    TODO: Implement Advanced mode with:
    - Tree view for nested logical operations (AND/OR/NOT)
    - Visual representation of filter logic
    - Drag and drop condition reordering
    - Condition editor panel with dynamic forms
    - Real-time syntax validation
    - Filter expression preview/summary
    """
    
    def __init__(self, dataset: BIDSDataset, previous_filter: Optional[LogicalOperation] = None, parent=None):
        """
        Initialize the filter builder dialog.
        
        Args:
            dataset: The BIDS dataset to build filters for.
            previous_filter: Previously applied filter to restore UI state.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self._dataset = dataset
        self._filter_expr: Optional[LogicalOperation] = previous_filter
        
        # Discover available filter options from dataset
        self._available_modalities = list(dataset.get_all_modalities())
        self._available_entities = dataset.get_all_entities()
        self._participant_attributes = self._get_participant_attributes()
        self._channel_attributes = self._get_channel_attributes()
        self._electrode_attributes = self._get_electrode_attributes()
        
        # Filter rows (list of row widgets)
        self._filter_rows = []
        
        self._setup_ui()
        self._connect_signals()
        self._setup_keyboard_shortcuts()
        
        # Restore previous filter state to UI
        if previous_filter:
            # Check if filter is complex (has OR/NOT or nesting)
            if self._is_complex_filter(previous_filter):
                # Start in Advanced mode
                self.ui.tabWidget.setCurrentIndex(1)
                self._build_tree_from_filter(previous_filter)
            else:
                # Start in Simple mode
                self.ui.tabWidget.setCurrentIndex(0)
                self._restore_filter_to_ui(previous_filter)
        
        logger.debug("FilterBuilderDialog initialized")
    
    def _is_complex_filter(self, filter_expr: LogicalOperation) -> bool:
        """Check if filter uses OR/NOT or has nested logical operations."""
        if not isinstance(filter_expr, LogicalOperation):
            return False
        
        # Check operator
        if filter_expr.operator in ['OR', 'NOT']:
            return True
        
        # Check children for nested logical operations
        for condition in filter_expr.conditions:
            if isinstance(condition, LogicalOperation):
                return True
        
        return False
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.ui = Ui_FilterBuilderDialog()
        self.ui.setupUi(self)
        
        # Enable advanced tab now
        self.ui.tabWidget.setTabEnabled(1, True)
        
        # Setup advanced mode UI
        self._setup_advanced_ui()
    
    def _connect_signals(self):
        """Connect UI signals to slots."""
        # Apply and Reset buttons
        apply_button = self.ui.buttonBox.button(self.ui.buttonBox.StandardButton.Apply)
        if apply_button:
            apply_button.clicked.connect(self._apply_filter)
        
        reset_button = self.ui.buttonBox.button(self.ui.buttonBox.StandardButton.Reset)
        if reset_button:
            reset_button.clicked.connect(self._reset_filters)
        
        # Preset buttons
        self.ui.savePresetButton.clicked.connect(self._save_preset)
        self.ui.loadPresetButton.clicked.connect(self._load_preset)
        
        # Add condition button
        self.ui.addConditionButton.clicked.connect(self._add_filter_row)
    
    def _add_filter_row(self, filter_type=None, subtype=None, operator=None, value=None):
        """
        Add a new filter condition row.
        
        Args:
            filter_type: Pre-select filter type (for restoring state)
            subtype: Pre-select subtype (entity code, attribute name, etc.)
            operator: Pre-select operator
            value: Pre-fill value
        """
        row_layout = QHBoxLayout()
        row_layout.setSpacing(6)
        
        # Type dropdown
        type_combo = QComboBox()
        type_combo.addItems([
            "Subject ID",
            "Modality",
            "Entity",
            "Subject Attribute",
            "Channel Attribute",
            "Electrode Attribute"
        ])
        if filter_type:
            type_combo.setCurrentText(filter_type)
        
        # Subtype dropdown (entity, attribute, etc.) - dynamic based on type
        subtype_combo = QComboBox()
        subtype_combo.setMinimumWidth(120)
        
        # Operator dropdown
        operator_combo = QComboBox()
        operator_combo.addItems(['equals', 'contains', 'greater_than', 'less_than'])
        if operator:
            operator_combo.setCurrentText(operator)
        
        # Value input
        value_input = QLineEdit()
        value_input.setPlaceholderText("Enter value...")
        if value:
            value_input.setText(str(value))
        
        # Delete button
        delete_button = QPushButton("Delete")
        delete_button.setMaximumWidth(80)
        
        # Add widgets to row
        row_layout.addWidget(type_combo, 1)
        row_layout.addWidget(subtype_combo, 1)
        row_layout.addWidget(operator_combo, 1)
        row_layout.addWidget(value_input, 2)
        row_layout.addWidget(delete_button, 0)
        
        # Store row info
        row_data = {
            'layout': row_layout,
            'type_combo': type_combo,
            'subtype_combo': subtype_combo,
            'operator_combo': operator_combo,
            'value_input': value_input,
            'delete_button': delete_button
        }
        self._filter_rows.append(row_data)
        
        # Connect signals
        type_combo.currentTextChanged.connect(lambda: self._update_row_subtypes(row_data))
        type_combo.currentTextChanged.connect(lambda: self._update_row_operators(row_data))
        delete_button.clicked.connect(lambda: self._delete_filter_row(row_data))
        
        # Add row to layout
        self.ui.filterRowsLayout.addLayout(row_layout)
        
        # Update subtypes and operators based on selected type
        self._update_row_subtypes(row_data)
        self._update_row_operators(row_data)
        
        # Restore subtype if provided
        if subtype and subtype_combo.count() > 0:
            index = subtype_combo.findText(subtype)
            if index >= 0:
                subtype_combo.setCurrentIndex(index)
    
    def _update_row_subtypes(self, row_data: dict):
        """Update the subtype dropdown based on selected filter type."""
        filter_type = row_data['type_combo'].currentText()
        subtype_combo = row_data['subtype_combo']
        operator_combo = row_data['operator_combo']
        
        # Clear existing items
        subtype_combo.clear()
        
        if filter_type == "Subject ID":
            subtype_combo.setEnabled(False)
            subtype_combo.addItem("(not applicable)")
            
        elif filter_type == "Modality":
            subtype_combo.setEnabled(False)
            subtype_combo.addItem("(not applicable)")
            
        elif filter_type == "Entity":
            subtype_combo.setEnabled(True)
            for entity_code in self._available_entities.keys():
                if entity_code not in ['sub', 'ses']:
                    from bidsio.core.entity_config import get_entity_full_name
                    subtype_combo.addItem(entity_code, entity_code)
            
        elif filter_type == "Subject Attribute":
            subtype_combo.setEnabled(True)
            for attr in self._participant_attributes:
                if attr != 'participant_id':
                    subtype_combo.addItem(attr)
            
        elif filter_type == "Channel Attribute":
            subtype_combo.setEnabled(True)
            for attr in self._channel_attributes:
                subtype_combo.addItem(attr)
            
        elif filter_type == "Electrode Attribute":
            subtype_combo.setEnabled(True)
            for attr in self._electrode_attributes:
                subtype_combo.addItem(attr)
    
    def _update_row_operators(self, row_data: dict):
        """Update the operator dropdown based on selected filter type."""
        filter_type = row_data['type_combo'].currentText()
        operator_combo = row_data['operator_combo']
        
        # Remember current selection if valid
        current_operator = operator_combo.currentText()
        
        # Clear existing items
        operator_combo.clear()
        
        # Set operators based on filter type
        if filter_type in ["Subject ID", "Modality"]:
            # These filters only support exact matching (list-based)
            operator_combo.addItem("equals")
            operator_combo.setEnabled(False)  # Disable since only one option
            
        elif filter_type == "Entity":
            # Entity filters support equals, not_equals, and contains
            operator_combo.addItems(['equals', 'not_equals', 'contains'])
            operator_combo.setEnabled(True)
            
            # Restore previous selection if it was valid
            if current_operator in ['equals', 'not_equals', 'contains']:
                operator_combo.setCurrentText(current_operator)
            
        elif filter_type in ["Subject Attribute", "Channel Attribute", "Electrode Attribute"]:
            # These support all operators
            operator_combo.addItems(['equals', 'not_equals', 'contains', 'greater_than', 'less_than'])
            operator_combo.setEnabled(True)
            
            # Restore previous selection if it was valid
            if current_operator in ['equals', 'not_equals', 'contains', 'greater_than', 'less_than']:
                operator_combo.setCurrentText(current_operator)
    
    def _delete_filter_row(self, row_data: dict):
        """Delete a filter row."""
        # Remove from layout
        layout = row_data['layout']
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Remove layout itself
        self.ui.filterRowsLayout.removeItem(layout)
        layout.deleteLater()
        
        # Remove from list
        self._filter_rows.remove(row_data)
    
    def _get_participant_attributes(self) -> list[str]:
        """
        Get list of available participant attributes from participants.tsv.
        
        Returns:
            List of attribute names (column headers).
        """
        attributes = set()
        for subject in self._dataset.subjects:
            attributes.update(subject.metadata.keys())
        return sorted(attributes)
    
    def _get_channel_attributes(self) -> list[str]:
        """
        Get list of available channel attributes from _channels.tsv files.
        
        Returns:
            List of attribute names (column headers).
        """
        attributes = set()
        for subject in self._dataset.subjects:
            if subject.ieeg_data and subject.ieeg_data.channels:
                attributes.update(subject.ieeg_data.get_all_channel_attributes())
        return sorted(attributes)
    
    def _get_electrode_attributes(self) -> list[str]:
        """
        Get list of available electrode attributes from _electrodes.tsv files.
        
        Returns:
            List of attribute names (column headers).
        """
        attributes = set()
        for subject in self._dataset.subjects:
            if subject.ieeg_data and subject.ieeg_data.electrodes:
                attributes.update(subject.ieeg_data.get_all_electrode_attributes())
        return sorted(attributes)
    
    def _restore_filter_to_ui(self, filter_expr: LogicalOperation):
        """
        Restore filter expression to UI state by creating filter rows.
        
        Args:
            filter_expr: The filter expression to restore.
        """
        if not isinstance(filter_expr, LogicalOperation):
            return
        
        # Create a row for each condition in the filter
        for condition in filter_expr.conditions:
            if isinstance(condition, SubjectIdFilter):
                # Create one row per subject ID
                for subject_id in condition.subject_ids:
                    self._add_filter_row("Subject ID", None, "equals", subject_id)
            
            elif isinstance(condition, ModalityFilter):
                # Create one row per modality
                for modality in condition.modalities:
                    self._add_filter_row("Modality", None, "equals", modality)
            
            elif isinstance(condition, EntityFilter):
                # Create one row for the entity filter
                self._add_filter_row("Entity", condition.entity_code, condition.operator, condition.value)
            
            elif isinstance(condition, ParticipantAttributeFilter):
                self._add_filter_row(
                    "Subject Attribute",
                    condition.attribute_name,
                    condition.operator,
                    condition.value
                )
            
            elif isinstance(condition, ChannelAttributeFilter):
                self._add_filter_row(
                    "Channel Attribute",
                    condition.attribute_name,
                    condition.operator,
                    condition.value
                )
            
            elif isinstance(condition, ElectrodeAttributeFilter):
                self._add_filter_row(
                    "Electrode Attribute",
                    condition.attribute_name,
                    condition.operator,
                    condition.value
                )
    
    def _validate_rows(self) -> tuple[bool, str]:
        """
        Validate that all rows are complete (except value can be empty).
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self._filter_rows:
            return False, "At least one filter condition is required to save a preset."
        
        incomplete_rows = []
        for i, row_data in enumerate(self._filter_rows):
            filter_type = row_data['type_combo'].currentText()
            subtype = row_data['subtype_combo'].currentText()
            
            # Check if subtype is needed and selected
            if filter_type in ["Entity", "Subject Attribute", "Channel Attribute", "Electrode Attribute"]:
                if not subtype or subtype == "(not applicable)" or not row_data['subtype_combo'].isEnabled():
                    incomplete_rows.append(i + 1)
        
        if incomplete_rows:
            rows_str = ", ".join(str(r) for r in incomplete_rows)
            return False, f"Row(s) {rows_str} are incomplete. Please select all required fields (type and subtype where applicable)."
        
        return True, ""
    
    def _build_filter_from_ui(self) -> Optional[LogicalOperation]:
        """
        Build filter expression from current UI state (all filter rows).
        
        Returns:
            LogicalOperation if any filters are set, None otherwise.
        """
        conditions = []
        
        # Process each filter row
        for row_data in self._filter_rows:
            filter_type = row_data['type_combo'].currentText()
            subtype = row_data['subtype_combo'].currentText()
            operator = row_data['operator_combo'].currentText()
            value_text = row_data['value_input'].text().strip()
            
            # Skip rows without a value (value is optional for save but required for apply)
            # We'll handle this in validation for save
            
            # Convert value to appropriate type
            value = value_text
            if value_text:
                try:
                    value = float(value_text)
                except ValueError:
                    value = value_text
            
            # Create condition based on type
            if filter_type == "Subject ID":
                if value_text:
                    conditions.append(SubjectIdFilter(subject_ids=[value_text]))
            
            elif filter_type == "Modality":
                if value_text:
                    conditions.append(ModalityFilter(modalities=[value_text]))
            
            elif filter_type == "Entity":
                if subtype and value_text:
                    conditions.append(EntityFilter(
                        entity_code=subtype,
                        operator=operator,
                        value=value_text
                    ))
            
            elif filter_type == "Subject Attribute":
                if subtype and subtype != "(not applicable)":
                    conditions.append(ParticipantAttributeFilter(
                        attribute_name=subtype,
                        operator=operator,
                        value=value if value_text else ""
                    ))
            
            elif filter_type == "Channel Attribute":
                if subtype and subtype != "(not applicable)":
                    conditions.append(ChannelAttributeFilter(
                        attribute_name=subtype,
                        operator=operator,
                        value=value if value_text else ""
                    ))
            
            elif filter_type == "Electrode Attribute":
                if subtype and subtype != "(not applicable)":
                    conditions.append(ElectrodeAttributeFilter(
                        attribute_name=subtype,
                        operator=operator,
                        value=value if value_text else ""
                    ))
        
        # Create logical operation (AND all conditions)
        if conditions:
            return LogicalOperation(operator='AND', conditions=conditions)
        else:
            return None
    
    @Slot()
    def _apply_filter(self):
        """Build filter expression from UI and accept dialog."""
        current_tab = self.ui.tabWidget.currentIndex()
        
        if current_tab == 0:  # Simple mode
            self._filter_expr = self._build_filter_from_ui()
        else:  # Advanced mode
            self._filter_expr = self._build_filter_from_tree()
        
        self.accept()
    
    @Slot()
    def _reset_filters(self):
        """Reset all filters by removing all rows."""
        reply = QMessageBox.question(
            self,
            "Reset Filters",
            "Are you sure you want to clear all filter conditions?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            current_tab = self.ui.tabWidget.currentIndex()
            
            if current_tab == 0:  # Simple mode
                # Remove all filter rows
                for row_data in self._filter_rows[:]:  # Copy list to avoid modification during iteration
                    self._delete_filter_row(row_data)
            else:  # Advanced mode
                # Clear tree
                self.ui.filterTreeWidget.clear()
                # Show empty editor
                self.ui.editorStackedWidget.setCurrentWidget(self.ui.emptyEditorPage)
            
            logger.debug("Filters reset")
    
    def _build_filter_from_tree(self) -> Optional[LogicalOperation]:
        """Build LogicalOperation from tree structure."""
        # If tree is empty, return None
        if self.ui.filterTreeWidget.topLevelItemCount() == 0:
            return None
        
        # If single top-level item, convert it
        if self.ui.filterTreeWidget.topLevelItemCount() == 1:
            root_item = self.ui.filterTreeWidget.topLevelItem(0)
            return self._tree_item_to_filter(root_item)
        
        # Multiple top-level items - wrap in AND
        conditions = []
        for i in range(self.ui.filterTreeWidget.topLevelItemCount()):
            item = self.ui.filterTreeWidget.topLevelItem(i)
            condition = self._tree_item_to_filter(item)
            if condition:
                conditions.append(condition)
        
        if conditions:
            return LogicalOperation(operator='AND', conditions=conditions)
        return None
    
    def _tree_item_to_filter(self, item: QTreeWidgetItem):
        """Convert a tree item and its children to a filter condition."""
        condition = item.data(0, Qt.UserRole)
        
        # If it's a logical operation, recursively convert children
        if isinstance(condition, LogicalOperation):
            child_conditions = []
            for i in range(item.childCount()):
                child_item = item.child(i)
                child_condition = self._tree_item_to_filter(child_item)
                if child_condition:
                    child_conditions.append(child_condition)
            
            # Create new logical operation with converted children
            return LogicalOperation(
                operator=condition.operator,
                conditions=child_conditions
            )
        else:
            # It's a filter condition - return as is
            return condition
    
    def _build_tree_from_filter(self, filter_expr: LogicalOperation):
        """Populate tree widget from LogicalOperation structure."""
        self.ui.filterTreeWidget.clear()
        
        if not filter_expr:
            return
        
        # Create tree structure
        root_item = self._filter_to_tree_item(filter_expr)
        self.ui.filterTreeWidget.addTopLevelItem(root_item)
        root_item.setExpanded(True)
        
        # Expand all children recursively
        self._expand_all_children(root_item)
    
    def _filter_to_tree_item(self, condition) -> QTreeWidgetItem:
        """Convert a filter condition to a tree item with children."""
        item = self._advanced_create_tree_item(condition)
        
        # If it's a logical operation, convert children
        if isinstance(condition, LogicalOperation):
            for child_condition in condition.conditions:
                child_item = self._filter_to_tree_item(child_condition)
                item.addChild(child_item)
        
        return item
    
    def _expand_all_children(self, item: QTreeWidgetItem):
        """Recursively expand all children of an item."""
        item.setExpanded(True)
        for i in range(item.childCount()):
            self._expand_all_children(item.child(i))
    
    @Slot()
    def _save_preset(self):
        """Save current filter expression as a preset."""
        current_tab = self.ui.tabWidget.currentIndex()
        
        # Build filter from current mode
        if current_tab == 0:  # Simple mode
            # Validate that all rows are complete
            is_valid, error_msg = self._validate_rows()
            if not is_valid:
                QMessageBox.warning(
                    self,
                    "Incomplete Filter",
                    error_msg
                )
                return
            
            filter_expr = self._build_filter_from_ui()
        else:  # Advanced mode
            # Validate tree is not empty
            if self.ui.filterTreeWidget.topLevelItemCount() == 0:
                QMessageBox.warning(
                    self,
                    "No Filter",
                    "The filter tree is empty. Cannot save an empty preset."
                )
                return
            
            filter_expr = self._build_filter_from_tree()
        
        if not filter_expr:
            QMessageBox.warning(
                self,
                "No Filter",
                "No filters are selected. Cannot save an empty preset."
            )
            return
        
        # Ask for preset name
        name, ok = QInputDialog.getText(
            self,
            "Save Preset",
            "Enter a name for this filter preset:"
        )
        
        if not ok or not name:
            return
        
        # Determine mode for metadata
        mode = "simple" if current_tab == 0 else "advanced"
        is_complex = self._is_complex_filter(filter_expr) if filter_expr else False
        
        # Save to file with version and mode metadata
        preset_path = get_filter_presets_directory() / f"{name}.json"
        
        try:
            preset_data = {
                "version": "1.0",
                "mode": "advanced" if is_complex else "simple",
                "filter": filter_expr.to_dict()
            }
            
            with open(preset_path, 'w', encoding='utf-8') as f:
                json.dump(preset_data, f, indent=2)
            
            QMessageBox.information(
                self,
                "Preset Saved",
                f"Filter preset '{name}' saved successfully."
            )
            logger.info(f"Filter preset saved: {preset_path}")
            
        except Exception as e:
            logger.error(f"Failed to save preset: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save preset:\n{str(e)}"
            )
    
    @Slot()
    def _load_preset(self):
        """Load a filter preset from file with preset management dialog."""
        presets_dir = get_filter_presets_directory()
        
        # Get list of preset files
        preset_files = list(presets_dir.glob("*.json"))
        
        if not preset_files:
            QMessageBox.information(
                self,
                "No Presets",
                "No saved filter presets found."
            )
            return
        
        # Create preset selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Load Filter Preset")
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(300)
        
        layout = QVBoxLayout(dialog)
        
        # Instructions
        label = QLabel("Select a preset to load:")
        layout.addWidget(label)
        
        # List widget for presets
        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        for preset_file in preset_files:
            item = QListWidgetItem(preset_file.stem)
            item.setData(Qt.ItemDataRole.UserRole, preset_file)
            list_widget.addItem(item)
        layout.addWidget(list_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda: self._delete_preset_item(list_widget))
        button_layout.addWidget(delete_button)
        button_layout.addStretch()
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        button_layout.addWidget(button_box)
        
        layout.addLayout(button_layout)
        
        # Show dialog
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        # Get selected preset
        selected_items = list_widget.selectedItems()
        if not selected_items:
            return
        
        selected_file = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        try:
            with open(selected_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle versioned and non-versioned formats
            if isinstance(data, dict) and 'version' in data:
                # New format with version
                preset_mode = data.get('mode', 'simple')
                filter_data = data.get('filter', {})
            else:
                # Old format - direct filter data
                filter_data = data
                preset_mode = 'simple'
            
            # Reconstruct filter expression
            filter_expr = LogicalOperation.from_dict(filter_data)
            
            # Check if preset is compatible with current mode
            current_tab = self.ui.tabWidget.currentIndex()
            is_complex = self._is_complex_filter(filter_expr)
            
            if current_tab == 0 and is_complex:  # Simple mode trying to load complex preset
                QMessageBox.warning(
                    self,
                    "Preset Too Complex",
                    "This preset uses advanced features (OR/NOT operations) "
                    "that cannot be loaded in Simple mode.\n\n"
                    "Please switch to Advanced mode to load this preset."
                )
                return
            
            # Ask whether to override or merge
            should_override = True
            current_mode_has_filters = (
                (current_tab == 0 and len(self._filter_rows) > 0) or
                (current_tab == 1 and self.ui.filterTreeWidget.topLevelItemCount() > 0)
            )
            
            if current_mode_has_filters:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Load Preset")
                msg_box.setText("There are existing filter conditions.")
                msg_box.setInformativeText("Do you want to override them or merge with the loaded preset?")
                
                override_button = msg_box.addButton("Override", QMessageBox.ButtonRole.YesRole)
                merge_button = msg_box.addButton("Merge", QMessageBox.ButtonRole.NoRole)
                cancel_button = msg_box.addButton(QMessageBox.StandardButton.Cancel)
                
                msg_box.setDefaultButton(override_button)
                msg_box.exec()
                
                clicked_button = msg_box.clickedButton()
                
                if clicked_button == cancel_button:
                    return
                elif clicked_button == override_button:
                    should_override = True
                else:
                    should_override = False
            
            # Load based on current mode
            if current_tab == 0:  # Simple mode
                if should_override:
                    # Clear existing rows
                    for row_data in self._filter_rows[:]:
                        self._delete_filter_row(row_data)
                
                # Restore to simple mode
                self._restore_filter_to_ui(filter_expr)
                
            else:  # Advanced mode
                if should_override:
                    # Clear tree
                    self.ui.filterTreeWidget.clear()
                    # Load preset as root
                    self._build_tree_from_filter(filter_expr)
                else:
                    # Merge - add preset as new top-level item
                    new_item = self._filter_to_tree_item(filter_expr)
                    self.ui.filterTreeWidget.addTopLevelItem(new_item)
                    new_item.setExpanded(True)
                    self._expand_all_children(new_item)
            
            action = "loaded" if should_override else "merged"
            logger.info(f"Filter preset {action} from: {selected_file}")
            
        except Exception as e:
            logger.error(f"Failed to load preset: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load preset:\n{str(e)}"
            )
    
    def _delete_preset_item(self, list_widget: QListWidget):
        """Delete the selected preset with confirmation."""
        selected_items = list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a preset to delete."
            )
            return
        
        item = selected_items[0]
        preset_name = item.text()
        preset_file = item.data(Qt.ItemDataRole.UserRole)
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the preset '{preset_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                preset_file.unlink()
                list_widget.takeItem(list_widget.row(item))
                logger.info(f"Deleted preset: {preset_file}")
                QMessageBox.information(
                    self,
                    "Preset Deleted",
                    f"Preset '{preset_name}' has been deleted."
                )
            except Exception as e:
                logger.error(f"Failed to delete preset: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to delete preset:\n{str(e)}"
                )
    
    def get_filter_expression(self) -> Optional[LogicalOperation]:
        """
        Get the built filter expression.
        
        Returns:
            LogicalOperation if filter was applied, None otherwise.
        """
        return self._filter_expr
    
    # ==================== Advanced Mode Implementation ====================
    
    def _setup_advanced_ui(self):
        """Setup the Advanced mode UI components."""
        # Import resources for icons
        import bidsio.ui.resources.resources_rc
        
        # Set icons for toolbar actions
        self.ui.actionAddCondition.setIcon(QIcon(":/icons/add_icon.svg"))
        self.ui.actionAddGroup.setIcon(QIcon(":/icons/and_icon.svg"))
        self.ui.actionDelete.setIcon(QIcon(":/icons/delete_icon.svg"))
        self.ui.actionMoveUp.setIcon(QIcon(":/icons/move_up_icon.svg"))
        self.ui.actionMoveDown.setIcon(QIcon(":/icons/move_down_icon.svg"))
        self.ui.actionCut.setIcon(QIcon(":/icons/cut_icon.svg"))
        self.ui.actionCopy.setIcon(QIcon(":/icons/copy_icon.svg"))
        self.ui.actionPaste.setIcon(QIcon(":/icons/paste_icon.svg"))
        
        # Set keyboard shortcuts for actions
        self.ui.actionDelete.setShortcut(QKeySequence(Qt.Key_Delete))
        self.ui.actionCut.setShortcut(QKeySequence.Cut)
        self.ui.actionCopy.setShortcut(QKeySequence.Copy)
        self.ui.actionPaste.setShortcut(QKeySequence.Paste)
        self.ui.actionMoveUp.setShortcut(QKeySequence("Ctrl+Up"))
        self.ui.actionMoveDown.setShortcut(QKeySequence("Ctrl+Down"))
        
        # Initially disable actions that require selection
        self.ui.actionDelete.setEnabled(False)
        self.ui.actionMoveUp.setEnabled(False)
        self.ui.actionMoveDown.setEnabled(False)
        self.ui.actionCut.setEnabled(False)
        self.ui.actionCopy.setEnabled(False)
        self.ui.actionPaste.setEnabled(False)
        
        # Clipboard for cut/copy/paste
        self._clipboard_item = None
        self._clipboard_is_cut = False
        
        # Show empty editor page initially
        self.ui.editorStackedWidget.setCurrentWidget(self.ui.emptyEditorPage)
        
        # Populate dynamic dropdowns
        self._populate_advanced_dropdowns()
    
    def _populate_advanced_dropdowns(self):
        """Populate dropdowns in advanced editor with dataset-specific values."""
        # Modality
        self.ui.modalityComboBox.clear()
        self.ui.modalityComboBox.addItems(self._available_modalities)
        
        # Entity names
        self.ui.entityNameComboBox.clear()
        self.ui.entityNameComboBox.addItems(sorted(self._available_entities.keys()))
        
        # Participant attributes
        self.ui.participantAttributeNameComboBox.clear()
        self.ui.participantAttributeNameComboBox.addItems(sorted(self._participant_attributes))
        
        # Channel attributes  
        self.ui.channelAttributeNameComboBox.clear()
        self.ui.channelAttributeNameComboBox.addItems(sorted(self._channel_attributes))
        
        # Electrode attributes
        self.ui.electrodeAttributeNameComboBox.clear()
        self.ui.electrodeAttributeNameComboBox.addItems(sorted(self._electrode_attributes))
    
    def _connect_signals(self):
        """Connect UI signals to slots."""
        # Apply and Reset buttons
        apply_button = self.ui.buttonBox.button(self.ui.buttonBox.StandardButton.Apply)
        if apply_button:
            apply_button.clicked.connect(self._apply_filter)
        
        reset_button = self.ui.buttonBox.button(self.ui.buttonBox.StandardButton.Reset)
        if reset_button:
            reset_button.clicked.connect(self._reset_filters)
        
        # Preset buttons
        self.ui.savePresetButton.clicked.connect(self._save_preset)
        self.ui.loadPresetButton.clicked.connect(self._load_preset)
        
        # Simple mode: Add condition button
        self.ui.addConditionButton.clicked.connect(self._add_filter_row)
        
        # Advanced mode: Toolbar actions
        self.ui.actionAddCondition.triggered.connect(self._advanced_add_condition)
        self.ui.actionAddGroup.triggered.connect(self._advanced_add_group_menu)
        self.ui.actionDelete.triggered.connect(self._advanced_delete_item)
        self.ui.actionMoveUp.triggered.connect(self._advanced_move_up)
        self.ui.actionMoveDown.triggered.connect(self._advanced_move_down)
        self.ui.actionCut.triggered.connect(self._advanced_cut_item)
        self.ui.actionCopy.triggered.connect(self._advanced_copy_item)
        self.ui.actionPaste.triggered.connect(self._advanced_paste_item)
        
        # Advanced mode: Tree widget
        self.ui.filterTreeWidget.itemSelectionChanged.connect(self._advanced_tree_selection_changed)
        self.ui.filterTreeWidget.customContextMenuRequested.connect(self._advanced_show_context_menu)
        
        # Advanced mode: Editor widgets - immediate updates
        self.ui.logicalOperatorComboBox.currentTextChanged.connect(self._advanced_editor_logical_changed)
        self.ui.conditionTypeComboBox.currentIndexChanged.connect(self._advanced_editor_condition_type_changed)
        
        # Condition detail editors - connect all to immediate update
        self.ui.subjectIdLineEdit.textChanged.connect(self._advanced_editor_details_changed)
        self.ui.modalityComboBox.currentTextChanged.connect(self._advanced_editor_details_changed)
        self.ui.entityNameComboBox.currentTextChanged.connect(self._advanced_editor_details_changed)
        self.ui.entityOperatorComboBox.currentTextChanged.connect(self._advanced_editor_details_changed)
        self.ui.entityValueLineEdit.textChanged.connect(self._advanced_editor_details_changed)
        self.ui.participantAttributeNameComboBox.currentTextChanged.connect(self._advanced_editor_details_changed)
        self.ui.participantAttributeOperatorComboBox.currentTextChanged.connect(self._advanced_editor_details_changed)
        self.ui.participantAttributeValueLineEdit.textChanged.connect(self._advanced_editor_details_changed)
        self.ui.channelAttributeNameComboBox.currentTextChanged.connect(self._advanced_editor_details_changed)
        self.ui.channelAttributeOperatorComboBox.currentTextChanged.connect(self._advanced_editor_details_changed)
        self.ui.channelAttributeValueLineEdit.textChanged.connect(self._advanced_editor_details_changed)
        self.ui.electrodeAttributeNameComboBox.currentTextChanged.connect(self._advanced_editor_details_changed)
        self.ui.electrodeAttributeOperatorComboBox.currentTextChanged.connect(self._advanced_editor_details_changed)
        self.ui.electrodeAttributeValueLineEdit.textChanged.connect(self._advanced_editor_details_changed)
        
        # Tab switching
        self.ui.tabWidget.currentChanged.connect(self._on_tab_changed)
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for common operations."""
        # Advanced mode shortcuts (only active when Advanced tab is visible)
        # Delete key
        delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self)
        delete_shortcut.activated.connect(self._handle_delete_shortcut)
        
        # Ctrl+X for cut
        cut_shortcut = QShortcut(QKeySequence.Cut, self)
        cut_shortcut.activated.connect(self._handle_cut_shortcut)
        
        # Ctrl+C for copy
        copy_shortcut = QShortcut(QKeySequence.Copy, self)
        copy_shortcut.activated.connect(self._handle_copy_shortcut)
        
        # Ctrl+V for paste
        paste_shortcut = QShortcut(QKeySequence.Paste, self)
        paste_shortcut.activated.connect(self._handle_paste_shortcut)
        
        # Ctrl+D for duplicate
        duplicate_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        duplicate_shortcut.activated.connect(self._handle_duplicate_shortcut)
        
        # Ctrl+Up/Down for moving
        move_up_shortcut = QShortcut(QKeySequence("Ctrl+Up"), self)
        move_up_shortcut.activated.connect(self._handle_move_up_shortcut)
        
        move_down_shortcut = QShortcut(QKeySequence("Ctrl+Down"), self)
        move_down_shortcut.activated.connect(self._handle_move_down_shortcut)
    
    def _handle_delete_shortcut(self):
        """Handle Delete key press."""
        if self.ui.tabWidget.currentIndex() == 1:  # Advanced mode
            if self.ui.filterTreeWidget.hasFocus() and self.ui.actionDelete.isEnabled():
                self._advanced_delete_item()
    
    def _handle_cut_shortcut(self):
        """Handle Ctrl+X shortcut."""
        if self.ui.tabWidget.currentIndex() == 1:  # Advanced mode
            if self.ui.filterTreeWidget.hasFocus() and self.ui.actionCut.isEnabled():
                self._advanced_cut_item()
    
    def _handle_copy_shortcut(self):
        """Handle Ctrl+C shortcut."""
        if self.ui.tabWidget.currentIndex() == 1:  # Advanced mode
            if self.ui.filterTreeWidget.hasFocus() and self.ui.actionCopy.isEnabled():
                self._advanced_copy_item()
    
    def _handle_paste_shortcut(self):
        """Handle Ctrl+V shortcut."""
        if self.ui.tabWidget.currentIndex() == 1:  # Advanced mode
            if self.ui.filterTreeWidget.hasFocus() and self.ui.actionPaste.isEnabled():
                self._advanced_paste_item()
    
    def _handle_duplicate_shortcut(self):
        """Handle Ctrl+D shortcut."""
        if self.ui.tabWidget.currentIndex() == 1:  # Advanced mode
            if self.ui.filterTreeWidget.hasFocus():
                selected_items = self.ui.filterTreeWidget.selectedItems()
                if selected_items:
                    # Copy then paste = duplicate
                    self._advanced_copy_item()
                    self._advanced_paste_item()
    
    def _handle_move_up_shortcut(self):
        """Handle Ctrl+Up shortcut."""
        if self.ui.tabWidget.currentIndex() == 1:  # Advanced mode
            if self.ui.filterTreeWidget.hasFocus() and self.ui.actionMoveUp.isEnabled():
                self._advanced_move_up()
    
    def _handle_move_down_shortcut(self):
        """Handle Ctrl+Down shortcut."""
        if self.ui.tabWidget.currentIndex() == 1:  # Advanced mode
            if self.ui.filterTreeWidget.hasFocus() and self.ui.actionMoveDown.isEnabled():
                self._advanced_move_down()
    
    # ==================== Advanced Mode: Tree Management ====================
    
    def _advanced_tree_selection_changed(self):
        """Handle tree selection changes."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        
        # Enable/disable actions based on selection
        has_selection = len(selected_items) > 0
        self.ui.actionDelete.setEnabled(has_selection)
        self.ui.actionCut.setEnabled(has_selection)
        self.ui.actionCopy.setEnabled(has_selection)
        
        # Enable paste if we have clipboard content
        self.ui.actionPaste.setEnabled(self._clipboard_item is not None)
        
        if has_selection:
            item = selected_items[0]
            parent = item.parent()
            
            # Enable move up/down if not first/last
            if parent:
                index = parent.indexOfChild(item)
                self.ui.actionMoveUp.setEnabled(index > 0)
                self.ui.actionMoveDown.setEnabled(index < parent.childCount() - 1)
            else:
                # Root level items
                index = self.ui.filterTreeWidget.indexOfTopLevelItem(item)
                self.ui.actionMoveUp.setEnabled(index > 0)
                self.ui.actionMoveDown.setEnabled(index < self.ui.filterTreeWidget.topLevelItemCount() - 1)
            
            # Show appropriate editor
            self._advanced_show_editor_for_item(item)
        else:
            # No selection
            self.ui.actionMoveUp.setEnabled(False)
            self.ui.actionMoveDown.setEnabled(False)
            self.ui.editorStackedWidget.setCurrentWidget(self.ui.emptyEditorPage)
    
    def _advanced_show_editor_for_item(self, item: QTreeWidgetItem):
        """Show appropriate editor panel for selected tree item."""
        condition = item.data(0, Qt.UserRole)
        
        if isinstance(condition, LogicalOperation):
            # Show logical operator editor
            self.ui.editorStackedWidget.setCurrentWidget(self.ui.logicalEditorPage)
            
            # Block signals to prevent immediate update during restore
            self.ui.logicalOperatorComboBox.blockSignals(True)
            self.ui.logicalOperatorComboBox.setCurrentText(condition.operator)
            self.ui.logicalOperatorComboBox.blockSignals(False)
            
        elif isinstance(condition, FilterCondition):
            # Show condition editor
            self.ui.editorStackedWidget.setCurrentWidget(self.ui.conditionEditorPage)
            
            # Block all signals during restore
            self._block_editor_signals(True)
            
            # Set condition type
            if isinstance(condition, SubjectIdFilter):
                self.ui.conditionTypeComboBox.setCurrentText("Subject ID")
                self.ui.conditionDetailsStackedWidget.setCurrentWidget(self.ui.subjectIdDetailsPage)
                self.ui.subjectIdLineEdit.setText(', '.join(condition.subject_ids))
                
            elif isinstance(condition, ModalityFilter):
                self.ui.conditionTypeComboBox.setCurrentText("Modality")
                self.ui.conditionDetailsStackedWidget.setCurrentWidget(self.ui.modalityDetailsPage)
                if condition.modalities:
                    self.ui.modalityComboBox.setCurrentText(condition.modalities[0])
                    
            elif isinstance(condition, EntityFilter):
                self.ui.conditionTypeComboBox.setCurrentText("Entity")
                self.ui.conditionDetailsStackedWidget.setCurrentWidget(self.ui.entityDetailsPage)
                self.ui.entityNameComboBox.setCurrentText(condition.entity_name)
                self.ui.entityOperatorComboBox.setCurrentText(condition.operator)
                self.ui.entityValueLineEdit.setText(condition.value)
                
            elif isinstance(condition, ParticipantAttributeFilter):
                self.ui.conditionTypeComboBox.setCurrentText("Participant Attribute")
                self.ui.conditionDetailsStackedWidget.setCurrentWidget(self.ui.participantAttributeDetailsPage)
                self.ui.participantAttributeNameComboBox.setCurrentText(condition.attribute_name)
                self.ui.participantAttributeOperatorComboBox.setCurrentText(condition.operator)
                self.ui.participantAttributeValueLineEdit.setText(str(condition.value))
                
            elif isinstance(condition, ChannelAttributeFilter):
                self.ui.conditionTypeComboBox.setCurrentText("Channel Attribute")
                self.ui.conditionDetailsStackedWidget.setCurrentWidget(self.ui.channelAttributeDetailsPage)
                self.ui.channelAttributeNameComboBox.setCurrentText(condition.attribute_name)
                self.ui.channelAttributeOperatorComboBox.setCurrentText(condition.operator)
                self.ui.channelAttributeValueLineEdit.setText(str(condition.value))
                
            elif isinstance(condition, ElectrodeAttributeFilter):
                self.ui.conditionTypeComboBox.setCurrentText("Electrode Attribute")
                self.ui.conditionDetailsStackedWidget.setCurrentWidget(self.ui.electrodeAttributeDetailsPage)
                self.ui.electrodeAttributeNameComboBox.setCurrentText(condition.attribute_name)
                self.ui.electrodeAttributeOperatorComboBox.setCurrentText(condition.operator)
                self.ui.electrodeAttributeValueLineEdit.setText(str(condition.value))
            
            # Unblock signals
            self._block_editor_signals(False)
        else:
            # Unknown type - show empty
            self.ui.editorStackedWidget.setCurrentWidget(self.ui.emptyEditorPage)
    
    def _block_editor_signals(self, block: bool):
        """Block or unblock all editor widget signals."""
        self.ui.conditionTypeComboBox.blockSignals(block)
        self.ui.subjectIdLineEdit.blockSignals(block)
        self.ui.modalityComboBox.blockSignals(block)
        self.ui.entityNameComboBox.blockSignals(block)
        self.ui.entityOperatorComboBox.blockSignals(block)
        self.ui.entityValueLineEdit.blockSignals(block)
        self.ui.participantAttributeNameComboBox.blockSignals(block)
        self.ui.participantAttributeOperatorComboBox.blockSignals(block)
        self.ui.participantAttributeValueLineEdit.blockSignals(block)
        self.ui.channelAttributeNameComboBox.blockSignals(block)
        self.ui.channelAttributeOperatorComboBox.blockSignals(block)
        self.ui.channelAttributeValueLineEdit.blockSignals(block)
        self.ui.electrodeAttributeNameComboBox.blockSignals(block)
        self.ui.electrodeAttributeOperatorComboBox.blockSignals(block)
        self.ui.electrodeAttributeValueLineEdit.blockSignals(block)
    
    # ==================== Advanced Mode: Tree Operations ====================
    
    def _advanced_add_condition(self):
        """Add a new condition to the tree."""
        # Show menu with condition types
        menu = QMenu(self)
        menu.addAction(QIcon(":/icons/id_icon.svg"), "Subject ID", lambda: self._advanced_create_and_add_item('subject_id'))
        menu.addAction(QIcon(":/icons/folder_icon.svg"), "Modality", lambda: self._advanced_create_and_add_item('modality'))
        menu.addAction(QIcon(":/icons/label_icon.svg"), "Entity", lambda: self._advanced_create_and_add_item('entity'))
        menu.addAction(QIcon(":/icons/participant_attribute_icon.svg"), "Participant Attribute", lambda: self._advanced_create_and_add_item('participant_attribute'))
        menu.addAction(QIcon(":/icons/channel_attribute_icon.svg"), "Channel Attribute", lambda: self._advanced_create_and_add_item('channel_attribute'))
        menu.addAction(QIcon(":/icons/electrode_attribute_icon.svg"), "Electrode Attribute", lambda: self._advanced_create_and_add_item('electrode_attribute'))
        
        # Show menu at button position
        menu.exec(self.ui.treeToolBar.mapToGlobal(self.ui.treeToolBar.actionGeometry(self.ui.actionAddCondition).bottomLeft()))
    
    def _advanced_add_group_menu(self):
        """Show menu to add a logical group (AND/OR/NOT)."""
        menu = QMenu(self)
        menu.addAction(QIcon(":/icons/and_icon.svg"), "AND Group", lambda: self._advanced_create_and_add_item('AND'))
        menu.addAction(QIcon(":/icons/or_icon.svg"), "OR Group", lambda: self._advanced_create_and_add_item('OR'))
        menu.addAction(QIcon(":/icons/not_icon.svg"), "NOT Group", lambda: self._advanced_create_and_add_item('NOT'))
        
        # Show menu at button position
        menu.exec(self.ui.treeToolBar.mapToGlobal(self.ui.treeToolBar.actionGeometry(self.ui.actionAddGroup).bottomLeft()))
    
    def _advanced_create_and_add_item(self, item_type: str):
        """Create and add a new item to the tree."""
        # Get parent item (selected item or None for root)
        selected_items = self.ui.filterTreeWidget.selectedItems()
        parent_item = None
        
        if selected_items:
            potential_parent = selected_items[0]
            parent_condition = potential_parent.data(0, Qt.UserRole)
            
            # If selected item is a logical operation, add as child
            if isinstance(parent_condition, LogicalOperation):
                # Check if NOT and already has a child
                if parent_condition.operator == 'NOT' and potential_parent.childCount() > 0:
                    QMessageBox.warning(
                        self,
                        "Cannot Add Child",
                        "NOT operations can only have one child condition."
                    )
                    return
                parent_item = potential_parent
            # Otherwise add as sibling (same level)
        
        # Create the condition object
        condition = self._advanced_create_condition(item_type)
        
        # Create tree item
        tree_item = self._advanced_create_tree_item(condition)
        
        # Add to tree
        if parent_item:
            parent_item.addChild(tree_item)
            parent_item.setExpanded(True)
        else:
            self.ui.filterTreeWidget.addTopLevelItem(tree_item)
        
        # Select the new item
        self.ui.filterTreeWidget.setCurrentItem(tree_item)
        
        logger.debug(f"Added {item_type} to tree")
    
    def _advanced_create_condition(self, item_type: str):
        """Create a new condition object based on type."""
        if item_type == 'AND':
            return LogicalOperation(operator='AND', conditions=[])
        elif item_type == 'OR':
            return LogicalOperation(operator='OR', conditions=[])
        elif item_type == 'NOT':
            return LogicalOperation(operator='NOT', conditions=[])
        elif item_type == 'subject_id':
            return SubjectIdFilter(subject_ids=[])
        elif item_type == 'modality':
            modality = self._available_modalities[0] if self._available_modalities else ''
            return ModalityFilter(modalities=[modality] if modality else [])
        elif item_type == 'entity':
            entity_name = sorted(self._available_entities.keys())[0] if self._available_entities else ''
            return EntityFilter(entity_name=entity_name, operator='equals', value='')
        elif item_type == 'participant_attribute':
            attr_name = sorted(self._participant_attributes)[0] if self._participant_attributes else ''
            return ParticipantAttributeFilter(attribute_name=attr_name, operator='equals', value='')
        elif item_type == 'channel_attribute':
            attr_name = sorted(self._channel_attributes)[0] if self._channel_attributes else ''
            return ChannelAttributeFilter(attribute_name=attr_name, operator='equals', value='')
        elif item_type == 'electrode_attribute':
            attr_name = sorted(self._electrode_attributes)[0] if self._electrode_attributes else ''
            return ElectrodeAttributeFilter(attribute_name=attr_name, operator='equals', value='')
        else:
            raise ValueError(f"Unknown item type: {item_type}")
    
    def _advanced_create_tree_item(self, condition) -> QTreeWidgetItem:
        """Create a tree widget item for a condition."""
        item = QTreeWidgetItem()
        
        # Store condition object
        item.setData(0, Qt.UserRole, condition)
        
        # Set display text and icon
        if isinstance(condition, LogicalOperation):
            item.setText(0, condition.operator)
            if condition.operator == 'AND':
                item.setIcon(0, QIcon(":/icons/and_icon.svg"))
            elif condition.operator == 'OR':
                item.setIcon(0, QIcon(":/icons/or_icon.svg"))
            elif condition.operator == 'NOT':
                item.setIcon(0, QIcon(":/icons/not_icon.svg"))
        else:
            text, icon = self._advanced_get_condition_display(condition)
            item.setText(0, text)
            item.setIcon(0, QIcon(icon))
        
        return item
    
    def _advanced_get_condition_display(self, condition: FilterCondition) -> tuple[str, str]:
        """Get display text and icon path for a condition."""
        if isinstance(condition, SubjectIdFilter):
            if condition.subject_ids:
                text = f"Subject ID: {', '.join(condition.subject_ids)}"
            else:
                text = "Subject ID: (empty)"
            return text, ":/icons/id_icon.svg"
        
        elif isinstance(condition, ModalityFilter):
            if condition.modalities:
                text = f"Modality: {', '.join(condition.modalities)}"
            else:
                text = "Modality: (empty)"
            return text, ":/icons/folder_icon.svg"
        
        elif isinstance(condition, EntityFilter):
            if condition.entity_name and condition.value:
                text = f"Entity: {condition.entity_name} {condition.operator} {condition.value}"
            else:
                text = f"Entity: {condition.entity_name or '(empty)'}"
            return text, ":/icons/label_icon.svg"
        
        elif isinstance(condition, ParticipantAttributeFilter):
            if condition.attribute_name and condition.value:
                text = f"Participant: {condition.attribute_name} {condition.operator} {condition.value}"
            else:
                text = f"Participant: {condition.attribute_name or '(empty)'}"
            return text, ":/icons/participant_attribute_icon.svg"
        
        elif isinstance(condition, ChannelAttributeFilter):
            if condition.attribute_name and condition.value:
                text = f"Channel: {condition.attribute_name} {condition.operator} {condition.value}"
            else:
                text = f"Channel: {condition.attribute_name or '(empty)'}"
            return text, ":/icons/channel_attribute_icon.svg"
        
        elif isinstance(condition, ElectrodeAttributeFilter):
            if condition.attribute_name and condition.value:
                text = f"Electrode: {condition.attribute_name} {condition.operator} {condition.value}"
            else:
                text = f"Electrode: {condition.attribute_name or '(empty)'}"
            return text, ":/icons/electrode_attribute_icon.svg"
        
        else:
            return "Unknown Condition", ":/icons/help_icon.svg"
    
    def _advanced_delete_item(self):
        """Delete selected tree item."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        
        # Confirm deletion if item has children
        if item.childCount() > 0:
            reply = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"This item has {item.childCount()} child(ren). Delete anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # Remove from tree
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            index = self.ui.filterTreeWidget.indexOfTopLevelItem(item)
            self.ui.filterTreeWidget.takeTopLevelItem(index)
        
        logger.debug("Deleted tree item")
    
    def _advanced_move_up(self):
        """Move selected item up in its parent."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        parent = item.parent()
        
        if parent:
            index = parent.indexOfChild(item)
            if index > 0:
                parent.takeChild(index)
                parent.insertChild(index - 1, item)
                self.ui.filterTreeWidget.setCurrentItem(item)
        else:
            index = self.ui.filterTreeWidget.indexOfTopLevelItem(item)
            if index > 0:
                self.ui.filterTreeWidget.takeTopLevelItem(index)
                self.ui.filterTreeWidget.insertTopLevelItem(index - 1, item)
                self.ui.filterTreeWidget.setCurrentItem(item)
    
    def _advanced_move_down(self):
        """Move selected item down in its parent."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        parent = item.parent()
        
        if parent:
            index = parent.indexOfChild(item)
            if index < parent.childCount() - 1:
                parent.takeChild(index)
                parent.insertChild(index + 1, item)
                self.ui.filterTreeWidget.setCurrentItem(item)
        else:
            index = self.ui.filterTreeWidget.indexOfTopLevelItem(item)
            if index < self.ui.filterTreeWidget.topLevelItemCount() - 1:
                self.ui.filterTreeWidget.takeTopLevelItem(index)
                self.ui.filterTreeWidget.insertTopLevelItem(index + 1, item)
                self.ui.filterTreeWidget.setCurrentItem(item)
    
    def _advanced_cut_item(self):
        """Cut selected item to clipboard."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        
        # Store in clipboard
        self._clipboard_item = self._advanced_clone_tree_item(item)
        self._clipboard_is_cut = True
        
        # Visual feedback - gray out the item
        font = item.font(0)
        font.setItalic(True)
        item.setFont(0, font)
        item.setForeground(0, Qt.gray)
        
        # Enable paste
        self.ui.actionPaste.setEnabled(True)
        
        logger.debug("Cut item to clipboard")
    
    def _advanced_copy_item(self):
        """Copy selected item to clipboard."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        
        # Store in clipboard
        self._clipboard_item = self._advanced_clone_tree_item(item)
        self._clipboard_is_cut = False
        
        # Enable paste
        self.ui.actionPaste.setEnabled(True)
        
        logger.debug("Copied item to clipboard")
    
    def _advanced_paste_item(self):
        """Paste item from clipboard."""
        if not self._clipboard_item:
            return
        
        selected_items = self.ui.filterTreeWidget.selectedItems()
        parent_item = None
        
        if selected_items:
            potential_parent = selected_items[0]
            parent_condition = potential_parent.data(0, Qt.UserRole)
            
            # If selected item is a logical operation, paste as child
            if isinstance(parent_condition, LogicalOperation):
                # Check if NOT and already has a child
                if parent_condition.operator == 'NOT' and potential_parent.childCount() > 0:
                    QMessageBox.warning(
                        self,
                        "Cannot Paste",
                        "NOT operations can only have one child condition."
                    )
                    return
                parent_item = potential_parent
        
        # Clone the clipboard item (in case we paste multiple times)
        pasted_item = self._advanced_clone_tree_item(self._clipboard_item)
        
        # Add to tree
        if parent_item:
            parent_item.addChild(pasted_item)
            parent_item.setExpanded(True)
        else:
            self.ui.filterTreeWidget.addTopLevelItem(pasted_item)
        
        # If it was cut, remove the original
        if self._clipboard_is_cut:
            # Find and remove the original cut item
            self._advanced_remove_cut_item()
            self._clipboard_item = None
            self._clipboard_is_cut = False
            self.ui.actionPaste.setEnabled(False)
        
        # Select the pasted item
        self.ui.filterTreeWidget.setCurrentItem(pasted_item)
        
        logger.debug("Pasted item from clipboard")
    
    def _advanced_remove_cut_item(self):
        """Remove the cut item from tree (after paste)."""
        # Search for the item that has gray/italic styling
        for i in range(self.ui.filterTreeWidget.topLevelItemCount()):
            item = self.ui.filterTreeWidget.topLevelItem(i)
            if self._advanced_find_and_remove_cut_item(item):
                return
    
    def _advanced_find_and_remove_cut_item(self, item: QTreeWidgetItem) -> bool:
        """Recursively find and remove cut item."""
        # Check if this item is styled as cut
        if item.font(0).italic():
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                index = self.ui.filterTreeWidget.indexOfTopLevelItem(item)
                self.ui.filterTreeWidget.takeTopLevelItem(index)
            return True
        
        # Check children
        for i in range(item.childCount()):
            if self._advanced_find_and_remove_cut_item(item.child(i)):
                return True
        
        return False
    
    def _advanced_clone_tree_item(self, item: QTreeWidgetItem) -> QTreeWidgetItem:
        """Deep clone a tree item with all children."""
        # Get the condition and deep copy it
        condition = item.data(0, Qt.UserRole)
        cloned_condition = self._advanced_deep_copy_condition(condition)
        
        # Create new tree item
        new_item = self._advanced_create_tree_item(cloned_condition)
        
        # Clone children recursively
        for i in range(item.childCount()):
            child_clone = self._advanced_clone_tree_item(item.child(i))
            new_item.addChild(child_clone)
        
        return new_item
    
    def _advanced_deep_copy_condition(self, condition):
        """Deep copy a condition object."""
        if isinstance(condition, LogicalOperation):
            return LogicalOperation(
                operator=condition.operator,
                conditions=[self._advanced_deep_copy_condition(c) for c in condition.conditions]
            )
        elif isinstance(condition, SubjectIdFilter):
            return SubjectIdFilter(subject_ids=condition.subject_ids.copy())
        elif isinstance(condition, ModalityFilter):
            return ModalityFilter(modalities=condition.modalities.copy())
        elif isinstance(condition, EntityFilter):
            return EntityFilter(
                entity_name=condition.entity_name,
                operator=condition.operator,
                value=condition.value
            )
        elif isinstance(condition, ParticipantAttributeFilter):
            return ParticipantAttributeFilter(
                attribute_name=condition.attribute_name,
                operator=condition.operator,
                value=condition.value
            )
        elif isinstance(condition, ChannelAttributeFilter):
            return ChannelAttributeFilter(
                attribute_name=condition.attribute_name,
                operator=condition.operator,
                value=condition.value
            )
        elif isinstance(condition, ElectrodeAttributeFilter):
            return ElectrodeAttributeFilter(
                attribute_name=condition.attribute_name,
                operator=condition.operator,
                value=condition.value
            )
        else:
            # Fallback - should not happen
            return condition
    
    def _advanced_show_context_menu(self, position):
        """Show context menu for tree widget."""
        item = self.ui.filterTreeWidget.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        # Add submenu for adding items
        add_condition_menu = menu.addMenu(QIcon(":/icons/add_icon.svg"), "Add Condition")
        add_condition_menu.addAction(QIcon(":/icons/id_icon.svg"), "Subject ID", lambda: self._advanced_create_and_add_item('subject_id'))
        add_condition_menu.addAction(QIcon(":/icons/folder_icon.svg"), "Modality", lambda: self._advanced_create_and_add_item('modality'))
        add_condition_menu.addAction(QIcon(":/icons/label_icon.svg"), "Entity", lambda: self._advanced_create_and_add_item('entity'))
        add_condition_menu.addAction(QIcon(":/icons/participant_attribute_icon.svg"), "Participant Attribute", lambda: self._advanced_create_and_add_item('participant_attribute'))
        add_condition_menu.addAction(QIcon(":/icons/channel_attribute_icon.svg"), "Channel Attribute", lambda: self._advanced_create_and_add_item('channel_attribute'))
        add_condition_menu.addAction(QIcon(":/icons/electrode_attribute_icon.svg"), "Electrode Attribute", lambda: self._advanced_create_and_add_item('electrode_attribute'))
        
        add_group_menu = menu.addMenu(QIcon(":/icons/and_icon.svg"), "Add Group")
        add_group_menu.addAction(QIcon(":/icons/and_icon.svg"), "AND Group", lambda: self._advanced_create_and_add_item('AND'))
        add_group_menu.addAction(QIcon(":/icons/or_icon.svg"), "OR Group", lambda: self._advanced_create_and_add_item('OR'))
        add_group_menu.addAction(QIcon(":/icons/not_icon.svg"), "NOT Group", lambda: self._advanced_create_and_add_item('NOT'))
        
        menu.addSeparator()
        
        # Standard operations
        menu.addAction(self.ui.actionCut)
        menu.addAction(self.ui.actionCopy)
        menu.addAction(self.ui.actionPaste)
        
        menu.addSeparator()
        
        menu.addAction(self.ui.actionDelete)
        
        menu.addSeparator()
        
        menu.addAction(self.ui.actionMoveUp)
        menu.addAction(self.ui.actionMoveDown)
        
        # Show menu at cursor
        menu.exec(self.ui.filterTreeWidget.viewport().mapToGlobal(position))
    
    # ==================== Advanced Mode: Editor Updates ====================
    
    def _advanced_editor_logical_changed(self):
        """Handle logical operator change in editor."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        condition = item.data(0, Qt.UserRole)
        
        if isinstance(condition, LogicalOperation):
            new_operator = self.ui.logicalOperatorComboBox.currentText()
            
            # Check if changing to NOT and has more than 1 child
            if new_operator == 'NOT' and item.childCount() > 1:
                QMessageBox.warning(
                    self,
                    "Cannot Change to NOT",
                    "NOT operations can only have one child condition.\n"
                    "Please remove extra children first."
                )
                # Revert the combo box
                self.ui.logicalOperatorComboBox.blockSignals(True)
                self.ui.logicalOperatorComboBox.setCurrentText(condition.operator)
                self.ui.logicalOperatorComboBox.blockSignals(False)
                return
            
            # Update condition
            condition.operator = new_operator
            
            # Update tree display
            item.setText(0, new_operator)
            if new_operator == 'AND':
                item.setIcon(0, QIcon(":/icons/and_icon.svg"))
            elif new_operator == 'OR':
                item.setIcon(0, QIcon(":/icons/or_icon.svg"))
            elif new_operator == 'NOT':
                item.setIcon(0, QIcon(":/icons/not_icon.svg"))
    
    def _advanced_editor_condition_type_changed(self, index):
        """Handle condition type change in editor."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        old_condition = item.data(0, Qt.UserRole)
        
        # Only proceed if it's actually a condition (not logical operation)
        if not isinstance(old_condition, FilterCondition):
            return
        
        # Get the type name
        type_names = ["Subject ID", "Modality", "Entity", "Participant Attribute", "Channel Attribute", "Electrode Attribute"]
        type_map = {
            "Subject ID": "subject_id",
            "Modality": "modality",
            "Entity": "entity",
            "Participant Attribute": "participant_attribute",
            "Channel Attribute": "channel_attribute",
            "Electrode Attribute": "electrode_attribute"
        }
        
        if index < 0 or index >= len(type_names):
            return
        
        type_name = type_names[index]
        item_type = type_map[type_name]
        
        # Create new condition
        new_condition = self._advanced_create_condition(item_type)
        
        # Update tree item
        item.setData(0, Qt.UserRole, new_condition)
        text, icon_path = self._advanced_get_condition_display(new_condition)
        item.setText(0, text)
        item.setIcon(0, QIcon(icon_path))
        
        # Update editor details page
        self.ui.conditionDetailsStackedWidget.setCurrentIndex(index)
        
        # Populate editor with new condition defaults
        self._block_editor_signals(True)
        self._advanced_populate_editor_for_condition(new_condition, index)
        self._block_editor_signals(False)
    
    def _advanced_populate_editor_for_condition(self, condition: FilterCondition, page_index: int):
        """Populate editor fields for a condition."""
        if page_index == 0:  # Subject ID
            self.ui.subjectIdLineEdit.clear()
        elif page_index == 1:  # Modality
            if isinstance(condition, ModalityFilter) and condition.modalities:
                self.ui.modalityComboBox.setCurrentText(condition.modalities[0])
        elif page_index == 2:  # Entity
            if isinstance(condition, EntityFilter):
                self.ui.entityNameComboBox.setCurrentText(condition.entity_name)
                self.ui.entityOperatorComboBox.setCurrentText(condition.operator)
                self.ui.entityValueLineEdit.clear()
        elif page_index == 3:  # Participant Attribute
            if isinstance(condition, ParticipantAttributeFilter):
                self.ui.participantAttributeNameComboBox.setCurrentText(condition.attribute_name)
                self.ui.participantAttributeOperatorComboBox.setCurrentText(condition.operator)
                self.ui.participantAttributeValueLineEdit.clear()
        elif page_index == 4:  # Channel Attribute
            if isinstance(condition, ChannelAttributeFilter):
                self.ui.channelAttributeNameComboBox.setCurrentText(condition.attribute_name)
                self.ui.channelAttributeOperatorComboBox.setCurrentText(condition.operator)
                self.ui.channelAttributeValueLineEdit.clear()
        elif page_index == 5:  # Electrode Attribute
            if isinstance(condition, ElectrodeAttributeFilter):
                self.ui.electrodeAttributeNameComboBox.setCurrentText(condition.attribute_name)
                self.ui.electrodeAttributeOperatorComboBox.setCurrentText(condition.operator)
                self.ui.electrodeAttributeValueLineEdit.clear()
    
    def _advanced_editor_details_changed(self):
        """Handle any condition detail change in editor."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        condition = item.data(0, Qt.UserRole)
        
        # Update condition based on current editor state
        if isinstance(condition, SubjectIdFilter):
            text = self.ui.subjectIdLineEdit.text()
            condition.subject_ids = [s.strip() for s in text.split(',') if s.strip()]
        
        elif isinstance(condition, ModalityFilter):
            modality = self.ui.modalityComboBox.currentText()
            condition.modalities = [modality] if modality else []
        
        elif isinstance(condition, EntityFilter):
            condition.entity_name = self.ui.entityNameComboBox.currentText()
            condition.operator = self.ui.entityOperatorComboBox.currentText()
            condition.value = self.ui.entityValueLineEdit.text()
        
        elif isinstance(condition, ParticipantAttributeFilter):
            condition.attribute_name = self.ui.participantAttributeNameComboBox.currentText()
            condition.operator = self.ui.participantAttributeOperatorComboBox.currentText()
            condition.value = self.ui.participantAttributeValueLineEdit.text()
        
        elif isinstance(condition, ChannelAttributeFilter):
            condition.attribute_name = self.ui.channelAttributeNameComboBox.currentText()
            condition.operator = self.ui.channelAttributeOperatorComboBox.currentText()
            condition.value = self.ui.channelAttributeValueLineEdit.text()
        
        elif isinstance(condition, ElectrodeAttributeFilter):
            condition.attribute_name = self.ui.electrodeAttributeNameComboBox.currentText()
            condition.operator = self.ui.electrodeAttributeOperatorComboBox.currentText()
            condition.value = self.ui.electrodeAttributeValueLineEdit.text()
        
        # Update tree display
        text, icon_path = self._advanced_get_condition_display(condition)
        item.setText(0, text)
    
    def _on_tab_changed(self, index):
        """Handle tab switching between Simple and Advanced modes."""
        if index == 0:  # Switching to Simple mode
            # Check if Advanced filter can be converted to Simple
            if not self._can_convert_advanced_to_simple():
                QMessageBox.warning(
                    self,
                    "Cannot Switch to Simple Mode",
                    "Your filter uses OR or NOT operations, or nested groups, "
                    "which are not supported in Simple mode.\n\n"
                    "Please simplify your filter or continue using Advanced mode."
                )
                # Stay on Advanced tab
                self.ui.tabWidget.blockSignals(True)
                self.ui.tabWidget.setCurrentIndex(1)
                self.ui.tabWidget.blockSignals(False)
                return
            
            # Convert Advanced to Simple
            self._convert_advanced_to_simple()
        
        elif index == 1:  # Switching to Advanced mode
            # Convert Simple to Advanced if tree is empty
            if self.ui.filterTreeWidget.topLevelItemCount() == 0:
                self._convert_simple_to_advanced()
    
    def _can_convert_advanced_to_simple(self) -> bool:
        """Check if Advanced filter can be converted to Simple mode."""
        # Empty tree is OK
        if self.ui.filterTreeWidget.topLevelItemCount() == 0:
            return True
        
        # Must have exactly one root item
        if self.ui.filterTreeWidget.topLevelItemCount() != 1:
            return False
        
        root_item = self.ui.filterTreeWidget.topLevelItem(0)
        root_condition = root_item.data(0, Qt.UserRole)
        
        # Root must be an AND operation
        if not isinstance(root_condition, LogicalOperation) or root_condition.operator != 'AND':
            return False
        
        # All children must be conditions (no nested logical operations)
        for i in range(root_item.childCount()):
            child = root_item.child(i)
            child_condition = child.data(0, Qt.UserRole)
            if isinstance(child_condition, LogicalOperation):
                return False
        
        return True
    
    def _convert_advanced_to_simple(self):
        """Convert Advanced mode filter to Simple mode."""
        # Clear existing Simple mode rows
        for row_data in self._filter_rows:
            # Remove widgets from layout
            for widget in [row_data['type_combo'], row_data['subtype_combo'], 
                          row_data['operator_combo'], row_data['value_input'], 
                          row_data['delete_button']]:
                widget.deleteLater()
            # Remove layout
            self.ui.filterRowsLayout.removeItem(row_data['layout'])
        self._filter_rows.clear()
        
        # If tree is empty, nothing to convert
        if self.ui.filterTreeWidget.topLevelItemCount() == 0:
            return
        
        # Get root AND node
        root_item = self.ui.filterTreeWidget.topLevelItem(0)
        
        # Convert each child to a Simple mode row
        for i in range(root_item.childCount()):
            child = root_item.child(i)
            condition = child.data(0, Qt.UserRole)
            self._convert_condition_to_simple_row(condition)
    
    def _convert_condition_to_simple_row(self, condition: FilterCondition):
        """Convert a single condition to a Simple mode row."""
        if isinstance(condition, SubjectIdFilter):
            value = ', '.join(condition.subject_ids) if condition.subject_ids else ''
            self._add_filter_row(filter_type="Subject ID", value=value)
        
        elif isinstance(condition, ModalityFilter):
            value = ', '.join(condition.modalities) if condition.modalities else ''
            self._add_filter_row(filter_type="Modality", subtype=condition.modalities[0] if condition.modalities else None)
        
        elif isinstance(condition, EntityFilter):
            self._add_filter_row(
                filter_type="Entity",
                subtype=condition.entity_name,
                operator=condition.operator,
                value=condition.value
            )
        
        elif isinstance(condition, ParticipantAttributeFilter):
            self._add_filter_row(
                filter_type="Subject Attribute",
                subtype=condition.attribute_name,
                operator=condition.operator,
                value=str(condition.value)
            )
        
        elif isinstance(condition, ChannelAttributeFilter):
            self._add_filter_row(
                filter_type="Channel Attribute",
                subtype=condition.attribute_name,
                operator=condition.operator,
                value=str(condition.value)
            )
        
        elif isinstance(condition, ElectrodeAttributeFilter):
            self._add_filter_row(
                filter_type="Electrode Attribute",
                subtype=condition.attribute_name,
                operator=condition.operator,
                value=str(condition.value)
            )
    
    def _convert_simple_to_advanced(self):
        """Convert Simple mode filter rows to Advanced mode tree."""
        # Clear existing tree
        self.ui.filterTreeWidget.clear()
        
        # If no rows, nothing to convert
        if not self._filter_rows:
            return
        
        # Create root AND node
        root_condition = LogicalOperation(operator='AND', conditions=[])
        root_item = self._advanced_create_tree_item(root_condition)
        self.ui.filterTreeWidget.addTopLevelItem(root_item)
        
        # Convert each row to a condition
        for row_data in self._filter_rows:
            condition = self._build_condition_from_row(row_data)
            if condition:
                child_item = self._advanced_create_tree_item(condition)
                root_item.addChild(child_item)
        
        # Expand root
        root_item.setExpanded(True)
    
    def _build_condition_from_row(self, row_data: dict) -> Optional[FilterCondition]:
        """Build a condition from a Simple mode row."""
        filter_type = row_data['type_combo'].currentText()
        subtype = row_data['subtype_combo'].currentText()
        operator = row_data['operator_combo'].currentText()
        value = row_data['value_input'].text()
        
        if filter_type == "Subject ID":
            subject_ids = [s.strip() for s in value.split(',') if s.strip()]
            return SubjectIdFilter(subject_ids=subject_ids)
        
        elif filter_type == "Modality":
            return ModalityFilter(modalities=[subtype] if subtype else [])
        
        elif filter_type == "Entity":
            return EntityFilter(
                entity_name=subtype,
                operator=operator,
                value=value
            )
        
        elif filter_type == "Subject Attribute":
            return ParticipantAttributeFilter(
                attribute_name=subtype,
                operator=operator,
                value=value
            )
        
        elif filter_type == "Channel Attribute":
            return ChannelAttributeFilter(
                attribute_name=subtype,
                operator=operator,
                value=value
            )
        
        elif filter_type == "Electrode Attribute":
            return ElectrodeAttributeFilter(
                attribute_name=subtype,
                operator=operator,
                value=value
            )
        
        return None


# TODO: Create separate widget classes for each filter type for better modularity
# TODO: Implement filter preview showing affected subject count
# TODO: Add filter description/summary generation
# TODO: Implement filter validation before application
# TODO: Add keyboard shortcuts for common operations
# TODO: Support filter composition (combining multiple saved presets)
