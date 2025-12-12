"""
Simple Filter Builder Widget.

Provides a simple interface for building filter expressions with rows of conditions
combined with AND logic. Ideal for straightforward filtering needs.
"""

from typing import Optional

from PySide6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QLineEdit, QPushButton
from PySide6.QtCore import Slot

from bidsio.infrastructure.logging_config import get_logger
from bidsio.core.models import BIDSDataset
from bidsio.core.filters import (
    LogicalOperation,
    SubjectIdFilter,
    ModalityFilter,
    EntityFilter,
    ParticipantAttributeFilter,
    ChannelAttributeFilter,
    ElectrodeAttributeFilter
)
from bidsio.ui.forms.simple_filter_builder_widget_ui import Ui_SimpleFilterBuilderWidget


logger = get_logger(__name__)


class SimpleFilterBuilderWidget(QWidget):
    """
    Widget for building simple filter expressions.
    
    Provides rows of filter conditions that are combined with AND logic.
    Each row specifies a filter type, optional subtype, operator, and value.
    """
    
    def __init__(self, dataset: BIDSDataset, parent=None):
        """
        Initialize the simple filter builder widget.
        
        Args:
            dataset: The BIDS dataset to build filters for.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self._dataset = dataset
        
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
        
        logger.debug("SimpleFilterBuilderWidget initialized")
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.ui = Ui_SimpleFilterBuilderWidget()
        self.ui.setupUi(self)
    
    def _connect_signals(self):
        """Connect UI signals to slots."""
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
                subtype_combo.addItem(entity_code)
            
        elif filter_type == "Subject Attribute":
            subtype_combo.setEnabled(True)
            for attr in self._participant_attributes:
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
                # channels is a dict[Path, list[dict]]
                for channel_list in subject.ieeg_data.channels.values():
                    if len(channel_list) > 0:
                        attributes.update(channel_list[0].keys())
                        break  # Only need first channel to get attribute names
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
                # electrodes is a dict[Path, list[dict]]
                for electrode_list in subject.ieeg_data.electrodes.values():
                    if len(electrode_list) > 0:
                        attributes.update(electrode_list[0].keys())
                        break  # Only need first electrode to get attribute names
        return sorted(attributes)
    
    def get_filter_expression(self, include_incomplete: bool = False) -> Optional[LogicalOperation]:
        """
        Build filter expression from current UI state (all filter rows).
        
        Args:
            include_incomplete: If True, include rows with empty values (for mode conversion).
        
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
            
            # Skip rows without a value (unless include_incomplete is True)
            if not value_text and not include_incomplete:
                continue
            
            # Convert value to appropriate type
            value = value_text
            if value_text:
                try:
                    value = int(value_text)
                except ValueError:
                    try:
                        value = float(value_text)
                    except ValueError:
                        value = value_text
            
            # Create condition based on type
            if filter_type == "Subject ID":
                condition = SubjectIdFilter(subject_id=value_text)
                conditions.append(condition)
            
            elif filter_type == "Modality":
                condition = ModalityFilter(modality=value_text)
                conditions.append(condition)
            
            elif filter_type == "Entity":
                condition = EntityFilter(
                    entity_code=subtype,
                    operator=operator,
                    value=str(value)
                )
                conditions.append(condition)
            
            elif filter_type == "Subject Attribute":
                condition = ParticipantAttributeFilter(
                    attribute_name=subtype,
                    operator=operator,
                    value=str(value)
                )
                conditions.append(condition)
            
            elif filter_type == "Channel Attribute":
                condition = ChannelAttributeFilter(
                    attribute_name=subtype,
                    operator=operator,
                    value=str(value)
                )
                conditions.append(condition)
            
            elif filter_type == "Electrode Attribute":
                condition = ElectrodeAttributeFilter(
                    attribute_name=subtype,
                    operator=operator,
                    value=str(value)
                )
                conditions.append(condition)
        
        # Create logical operation (AND all conditions)
        if conditions:
            return LogicalOperation(operator='AND', conditions=conditions)
        else:
            return None
    
    def set_filter_expression(self, filter_expr: Optional[LogicalOperation]):
        """
        Restore filter expression to UI state by creating filter rows.
        
        Args:
            filter_expr: The filter expression to restore.
        """
        # Clear existing rows
        self.reset_filters()
        
        if not isinstance(filter_expr, LogicalOperation):
            return
        
        # Only support AND operations for simple mode
        if filter_expr.operator != 'AND':
            return
        
        # Create a row for each condition in the filter
        for condition in filter_expr.conditions:
            if isinstance(condition, SubjectIdFilter):
                self._add_filter_row("Subject ID", None, "equals", condition.subject_id)
                
            elif isinstance(condition, ModalityFilter):
                self._add_filter_row("Modality", None, "equals", condition.modality)
                
            elif isinstance(condition, EntityFilter):
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
    
    def reset_filters(self):
        """Reset all filters by removing all rows."""
        # Remove all rows
        for row_data in self._filter_rows.copy():
            self._delete_filter_row(row_data)
        self._filter_rows.clear()
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate that all rows are complete.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self._filter_rows:
            return True, ""
        
        incomplete_rows = []
        for i, row_data in enumerate(self._filter_rows):
            filter_type = row_data['type_combo'].currentText()
            subtype = row_data['subtype_combo'].currentText()
            
            # Check if subtype is needed and selected
            if filter_type in ["Entity", "Subject Attribute", "Channel Attribute", "Electrode Attribute"]:
                if not subtype or subtype == "(not applicable)":
                    incomplete_rows.append(i + 1)
        
        if incomplete_rows:
            rows_str = ", ".join(str(r) for r in incomplete_rows)
            return False, f"Incomplete filters in row(s): {rows_str}"
        
        return True, ""
