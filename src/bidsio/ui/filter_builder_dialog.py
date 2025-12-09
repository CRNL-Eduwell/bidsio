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
    QInputDialog, QCheckBox, QListWidgetItem, QDialogButtonBox
)
from PySide6.QtCore import Slot, Qt

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
        
        # Restore previous filter state to UI
        if previous_filter:
            self._restore_filter_to_ui(previous_filter)
        
        logger.debug("FilterBuilderDialog initialized")
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.ui = Ui_FilterBuilderDialog()
        self.ui.setupUi(self)
        
        # Disable advanced tab for now
        self.ui.tabWidget.setTabEnabled(1, False)
    
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
        delete_button.clicked.connect(lambda: self._delete_filter_row(row_data))
        
        # Add row to layout
        self.ui.filterRowsLayout.addLayout(row_layout)
        
        # Update subtypes based on selected type
        self._update_row_subtypes(row_data)
        
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
            operator_combo.setEnabled(True)
            
        elif filter_type == "Modality":
            subtype_combo.setEnabled(False)
            subtype_combo.addItem("(not applicable)")
            operator_combo.setEnabled(True)
            
        elif filter_type == "Entity":
            subtype_combo.setEnabled(True)
            for entity_code in self._available_entities.keys():
                if entity_code not in ['sub', 'ses']:
                    from bidsio.core.entity_config import get_entity_full_name
                    subtype_combo.addItem(entity_code, entity_code)
            operator_combo.setEnabled(True)
            
        elif filter_type == "Subject Attribute":
            subtype_combo.setEnabled(True)
            for attr in self._participant_attributes:
                if attr != 'participant_id':
                    subtype_combo.addItem(attr)
            operator_combo.setEnabled(True)
            
        elif filter_type == "Channel Attribute":
            subtype_combo.setEnabled(True)
            for attr in self._channel_attributes:
                subtype_combo.addItem(attr)
            operator_combo.setEnabled(True)
            
        elif filter_type == "Electrode Attribute":
            subtype_combo.setEnabled(True)
            for attr in self._electrode_attributes:
                subtype_combo.addItem(attr)
            operator_combo.setEnabled(True)
    
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
                # Create one row per entity value
                for value in condition.values:
                    self._add_filter_row("Entity", condition.entity_code, "equals", value)
            
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
                    conditions.append(EntityFilter(entity_code=subtype, values=[value_text]))
            
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
        self._filter_expr = self._build_filter_from_ui()
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
            # Remove all filter rows
            for row_data in self._filter_rows[:]:  # Copy list to avoid modification during iteration
                self._delete_filter_row(row_data)
            
            self.ui.statusLabel.setText("All filters cleared")
            logger.debug("Filters reset")
    
    @Slot()
    def _save_preset(self):
        """Save current filter expression as a preset."""
        # Validate that all rows are complete
        is_valid, error_msg = self._validate_rows()
        if not is_valid:
            QMessageBox.warning(
                self,
                "Incomplete Filter",
                error_msg
            )
            return
        
        # Build filter from current UI state (without closing dialog)
        filter_expr = self._build_filter_from_ui()
        
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
        
        # Save to file
        preset_path = get_filter_presets_directory() / f"{name}.json"
        
        try:
            with open(preset_path, 'w', encoding='utf-8') as f:
                json.dump(filter_expr.to_dict(), f, indent=2)
            
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
            
            # Reconstruct filter expression
            filter_expr = LogicalOperation.from_dict(data)
            
            # Check if there are existing conditions
            should_override = True
            if self._filter_rows:
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
                    # Override - clear existing rows first
                    for row_data in self._filter_rows[:]:
                        self._delete_filter_row(row_data)
                    should_override = True
                else:
                    # Merge - keep existing rows
                    should_override = False
            
            # Restore filter to UI (will add to existing if merging)
            self._restore_filter_to_ui(filter_expr)
            
            action = "loaded" if should_override else "merged"
            self.ui.statusLabel.setText(f"Preset '{selected_file.stem}' {action} successfully")
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


# TODO: Create separate widget classes for each filter type for better modularity
# TODO: Implement filter preview showing affected subject count
# TODO: Add filter description/summary generation
# TODO: Implement filter validation before application
# TODO: Add keyboard shortcuts for common operations
# TODO: Support filter composition (combining multiple saved presets)
