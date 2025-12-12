"""
Advanced Filter Builder Widget.

Provides an advanced interface with tree view for building complex filter expressions
with nested logical operations (AND/OR/NOT).
"""

from typing import Optional

from PySide6.QtWidgets import QWidget, QTreeWidgetItem, QMenu, QMessageBox
from PySide6.QtCore import Slot, Qt, QTimer
from PySide6.QtGui import QIcon, QKeySequence, QShortcut, QBrush, QColor

from bidsio.infrastructure.logging_config import get_logger
from bidsio.core.models import BIDSDataset
from bidsio.core.filters import (
    FilterCondition,
    LogicalOperation,
    SubjectIdFilter,
    ModalityFilter,
    ParticipantAttributeFilter,
    EntityFilter,
    ChannelAttributeFilter,
    ElectrodeAttributeFilter
)
from bidsio.ui.forms.advanced_filter_builder_widget_ui import Ui_AdvancedFilterBuilderWidget


logger = get_logger(__name__)


class AdvancedFilterBuilderWidget(QWidget):
    """
    Widget for building advanced filter expressions with tree structure.
    
    Provides a tree view for creating complex nested filter conditions
    with logical operations (AND/OR/NOT), visual editor panels, and
    cut/copy/paste operations.
    """
    
    def __init__(self, dataset: BIDSDataset, parent=None):
        """
        Initialize the advanced filter builder widget.
        
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
        
        # Clipboard for cut/copy/paste
        self._clipboard_item = None
        self._clipboard_is_cut = False
        self._cut_item_reference = None
        
        self._setup_ui()
        self._connect_signals()
        self._setup_keyboard_shortcuts()
        
        logger.debug("AdvancedFilterBuilderWidget initialized")
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.ui = Ui_AdvancedFilterBuilderWidget()
        self.ui.setupUi(self)
        
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
        self.ui.actionDelete.setShortcut(QKeySequence(Qt.Key.Key_Delete))
        self.ui.actionCut.setShortcut(QKeySequence(QKeySequence.StandardKey.Cut))
        self.ui.actionCopy.setShortcut(QKeySequence(QKeySequence.StandardKey.Copy))
        self.ui.actionPaste.setShortcut(QKeySequence(QKeySequence.StandardKey.Paste))
        self.ui.actionMoveUp.setShortcut(QKeySequence("Ctrl+Up"))
        self.ui.actionMoveDown.setShortcut(QKeySequence("Ctrl+Down"))
        
        # Initially disable actions that require selection
        self.ui.actionDelete.setEnabled(False)
        self.ui.actionMoveUp.setEnabled(False)
        self.ui.actionMoveDown.setEnabled(False)
        self.ui.actionCut.setEnabled(False)
        self.ui.actionCopy.setEnabled(False)
        self.ui.actionPaste.setEnabled(False)
        
        # Show empty editor page initially
        self.ui.editorStackedWidget.setCurrentWidget(self.ui.emptyEditorPage)
        
        # Populate dynamic dropdowns
        self._populate_dropdowns()
    
    def _populate_dropdowns(self):
        """Populate dropdowns in editor with dataset-specific values."""
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
        # Toolbar actions
        self.ui.actionAddCondition.triggered.connect(self._add_condition)
        self.ui.actionAddGroup.triggered.connect(self._add_group_menu)
        self.ui.actionDelete.triggered.connect(self._delete_item)
        self.ui.actionMoveUp.triggered.connect(self._move_up)
        self.ui.actionMoveDown.triggered.connect(self._move_down)
        self.ui.actionCut.triggered.connect(self._cut_item)
        self.ui.actionCopy.triggered.connect(self._copy_item)
        self.ui.actionPaste.triggered.connect(self._paste_item)
        
        # Tree widget
        self.ui.filterTreeWidget.itemSelectionChanged.connect(self._tree_selection_changed)
        self.ui.filterTreeWidget.customContextMenuRequested.connect(self._show_context_menu)
        
        # Editor widgets - immediate updates
        self.ui.logicalOperatorComboBox.currentTextChanged.connect(self._editor_logical_changed)
        self.ui.conditionTypeComboBox.currentIndexChanged.connect(self._editor_condition_type_changed)
        
        # Condition detail editors
        self.ui.subjectIdLineEdit.textChanged.connect(self._editor_details_changed)
        self.ui.modalityComboBox.currentTextChanged.connect(self._editor_details_changed)
        self.ui.entityNameComboBox.currentTextChanged.connect(self._editor_details_changed)
        self.ui.entityOperatorComboBox.currentTextChanged.connect(self._editor_details_changed)
        self.ui.entityValueLineEdit.textChanged.connect(self._editor_details_changed)
        self.ui.participantAttributeNameComboBox.currentTextChanged.connect(self._editor_details_changed)
        self.ui.participantAttributeOperatorComboBox.currentTextChanged.connect(self._editor_details_changed)
        self.ui.participantAttributeValueLineEdit.textChanged.connect(self._editor_details_changed)
        self.ui.channelAttributeNameComboBox.currentTextChanged.connect(self._editor_details_changed)
        self.ui.channelAttributeOperatorComboBox.currentTextChanged.connect(self._editor_details_changed)
        self.ui.channelAttributeValueLineEdit.textChanged.connect(self._editor_details_changed)
        self.ui.electrodeAttributeNameComboBox.currentTextChanged.connect(self._editor_details_changed)
        self.ui.electrodeAttributeOperatorComboBox.currentTextChanged.connect(self._editor_details_changed)
        self.ui.electrodeAttributeValueLineEdit.textChanged.connect(self._editor_details_changed)
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for common operations."""
        # Ctrl+D for duplicate
        duplicate_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        duplicate_shortcut.activated.connect(self._handle_duplicate_shortcut)
    
    def _handle_duplicate_shortcut(self):
        """Handle Ctrl+D shortcut."""
        if self.ui.filterTreeWidget.hasFocus():
            selected_items = self.ui.filterTreeWidget.selectedItems()
            if selected_items:
                # Copy then paste = duplicate
                self._copy_item()
                self._paste_item()
    
    def _get_participant_attributes(self) -> list[str]:
        """Get list of available participant attributes from participants.tsv."""
        attributes = set()
        for subject in self._dataset.subjects:
            attributes.update(subject.metadata.keys())
        return sorted(attributes)
    
    def _get_channel_attributes(self) -> list[str]:
        """Get list of available channel attributes from _channels.tsv files."""
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
        """Get list of available electrode attributes from _electrodes.tsv files."""
        attributes = set()
        for subject in self._dataset.subjects:
            if subject.ieeg_data and subject.ieeg_data.electrodes:
                # electrodes is a dict[Path, list[dict]]
                for electrode_list in subject.ieeg_data.electrodes.values():
                    if len(electrode_list) > 0:
                        attributes.update(electrode_list[0].keys())
                        break  # Only need first electrode to get attribute names
        return sorted(attributes)
    
    # ==================== Tree Management ====================
    
    def _tree_selection_changed(self):
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
                index = self.ui.filterTreeWidget.indexOfTopLevelItem(item)
                self.ui.actionMoveUp.setEnabled(index > 0)
                self.ui.actionMoveDown.setEnabled(index < self.ui.filterTreeWidget.topLevelItemCount() - 1)
            
            # Show appropriate editor
            self._show_editor_for_item(item)
        else:
            # No selection
            self.ui.actionMoveUp.setEnabled(False)
            self.ui.actionMoveDown.setEnabled(False)
            self.ui.editorStackedWidget.setCurrentWidget(self.ui.emptyEditorPage)
    
    def _show_editor_for_item(self, item: QTreeWidgetItem):
        """Show appropriate editor panel for selected tree item."""
        condition = item.data(0, Qt.ItemDataRole.UserRole)
        
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
            
            # Set condition type and populate fields
            if isinstance(condition, SubjectIdFilter):
                self.ui.conditionTypeComboBox.setCurrentIndex(0)
                self.ui.conditionDetailsStackedWidget.setCurrentIndex(0)
                self.ui.subjectIdLineEdit.setText(condition.subject_id)
                
            elif isinstance(condition, ModalityFilter):
                self.ui.conditionTypeComboBox.setCurrentIndex(1)
                self.ui.conditionDetailsStackedWidget.setCurrentIndex(1)
                self.ui.modalityComboBox.setCurrentText(condition.modality)
                    
            elif isinstance(condition, EntityFilter):
                self.ui.conditionTypeComboBox.setCurrentIndex(2)
                self.ui.conditionDetailsStackedWidget.setCurrentIndex(2)
                self.ui.entityNameComboBox.setCurrentText(condition.entity_code)
                self.ui.entityOperatorComboBox.setCurrentText(condition.operator)
                self.ui.entityValueLineEdit.setText(str(condition.value))
                
            elif isinstance(condition, ParticipantAttributeFilter):
                self.ui.conditionTypeComboBox.setCurrentIndex(3)
                self.ui.conditionDetailsStackedWidget.setCurrentIndex(3)
                self.ui.participantAttributeNameComboBox.setCurrentText(condition.attribute_name)
                self.ui.participantAttributeOperatorComboBox.setCurrentText(condition.operator)
                self.ui.participantAttributeValueLineEdit.setText(str(condition.value))
                
            elif isinstance(condition, ChannelAttributeFilter):
                self.ui.conditionTypeComboBox.setCurrentIndex(4)
                self.ui.conditionDetailsStackedWidget.setCurrentIndex(4)
                self.ui.channelAttributeNameComboBox.setCurrentText(condition.attribute_name)
                self.ui.channelAttributeOperatorComboBox.setCurrentText(condition.operator)
                self.ui.channelAttributeValueLineEdit.setText(str(condition.value))
                
            elif isinstance(condition, ElectrodeAttributeFilter):
                self.ui.conditionTypeComboBox.setCurrentIndex(5)
                self.ui.conditionDetailsStackedWidget.setCurrentIndex(5)
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
    
    # ==================== Tree Operations ====================
    
    @Slot()
    def _add_condition(self):
        """Add a new condition to the tree."""
        # Show menu with condition types
        menu = QMenu(self)
        menu.addAction(QIcon(":/icons/id_icon.svg"), "Subject ID", lambda: self._create_and_add_item('subject_id'))
        menu.addAction(QIcon(":/icons/folder_icon.svg"), "Modality", lambda: self._create_and_add_item('modality'))
        menu.addAction(QIcon(":/icons/label_icon.svg"), "Entity", lambda: self._create_and_add_item('entity'))
        menu.addAction(QIcon(":/icons/participant_attribute_icon.svg"), "Participant Attribute", lambda: self._create_and_add_item('participant_attribute'))
        menu.addAction(QIcon(":/icons/channel_attribute_icon.svg"), "Channel Attribute", lambda: self._create_and_add_item('channel_attribute'))
        menu.addAction(QIcon(":/icons/electrode_attribute_icon.svg"), "Electrode Attribute", lambda: self._create_and_add_item('electrode_attribute'))
        
        # Show menu at button position
        menu.exec(self.ui.treeToolBar.mapToGlobal(self.ui.treeToolBar.actionGeometry(self.ui.actionAddCondition).bottomLeft()))
    
    @Slot()
    def _add_group_menu(self):
        """Show menu to add a logical group (AND/OR/NOT)."""
        menu = QMenu(self)
        menu.addAction(QIcon(":/icons/and_icon.svg"), "AND Group", lambda: self._create_and_add_item('AND'))
        menu.addAction(QIcon(":/icons/or_icon.svg"), "OR Group", lambda: self._create_and_add_item('OR'))
        menu.addAction(QIcon(":/icons/not_icon.svg"), "NOT Group", lambda: self._create_and_add_item('NOT'))
        
        # Show menu at button position
        menu.exec(self.ui.treeToolBar.mapToGlobal(self.ui.treeToolBar.actionGeometry(self.ui.actionAddGroup).bottomLeft()))
    
    def _create_and_add_item(self, item_type: str):
        """Create and add a new item to the tree."""
        # Check if tree is empty - create default AND node for conditions
        if self.ui.filterTreeWidget.topLevelItemCount() == 0:
            # If adding a condition (not a logical operation), create AND node first
            if item_type not in ['AND', 'OR', 'NOT']:
                and_condition = LogicalOperation(operator='AND', conditions=[])
                and_item = self._create_tree_item(and_condition)
                self.ui.filterTreeWidget.addTopLevelItem(and_item)
                and_item.setExpanded(True)
        
        # Get parent item (selected item or None for root)
        selected_items = self.ui.filterTreeWidget.selectedItems()
        parent_item = None
        
        if selected_items:
            potential_parent = selected_items[0]
            parent_condition = potential_parent.data(0, Qt.ItemDataRole.UserRole)
            
            # If selected item is a logical operation, add as child
            if isinstance(parent_condition, LogicalOperation):
                parent_item = potential_parent
            # If selected item is a condition, add as sibling
            elif potential_parent.parent():
                parent_item = potential_parent.parent()
            # If selected is top-level condition, add to first top-level logical operation
            else:
                if self.ui.filterTreeWidget.topLevelItemCount() > 0:
                    first_item = self.ui.filterTreeWidget.topLevelItem(0)
                    if first_item and isinstance(first_item.data(0, Qt.ItemDataRole.UserRole), LogicalOperation):
                        parent_item = first_item
        else:
            # No selection - for conditions, add to the root node if it exists
            if self.ui.filterTreeWidget.topLevelItemCount() > 0:
                first_item = self.ui.filterTreeWidget.topLevelItem(0)
                if first_item and isinstance(first_item.data(0, Qt.ItemDataRole.UserRole), LogicalOperation):
                    parent_item = first_item
        
        # Create the condition object
        condition = self._create_condition(item_type)
        
        # Create tree item
        tree_item = self._create_tree_item(condition)
        
        # Add to tree
        if parent_item:
            parent_item.addChild(tree_item)
            parent_item.setExpanded(True)
        else:
            self.ui.filterTreeWidget.addTopLevelItem(tree_item)
        
        # Select the new item
        self.ui.filterTreeWidget.setCurrentItem(tree_item)
        
        logger.debug(f"Added {item_type} to tree")
    
    def _create_condition(self, item_type: str):
        """Create a new condition object based on type."""
        if item_type == 'AND':
            return LogicalOperation(operator='AND', conditions=[])
        elif item_type == 'OR':
            return LogicalOperation(operator='OR', conditions=[])
        elif item_type == 'NOT':
            return LogicalOperation(operator='NOT', conditions=[])
        elif item_type == 'subject_id':
            return SubjectIdFilter(subject_id='')
        elif item_type == 'modality':
            modality = self._available_modalities[0] if self._available_modalities else ''
            return ModalityFilter(modality=modality)
        elif item_type == 'entity':
            entity_code = sorted(self._available_entities.keys())[0] if self._available_entities else ''
            return EntityFilter(entity_code=entity_code, operator='equals', value='')
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
    
    def _create_tree_item(self, condition) -> QTreeWidgetItem:
        """Create a tree widget item for a condition."""
        item = QTreeWidgetItem()
        
        # Store condition object
        item.setData(0, Qt.ItemDataRole.UserRole, condition)
        
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
            text, icon = self._get_condition_display(condition)
            item.setText(0, text)
            item.setIcon(0, QIcon(icon))
        
        return item
    
    def _get_condition_display(self, condition: FilterCondition) -> tuple[str, str]:
        """Get display text and icon path for a condition."""
        if isinstance(condition, SubjectIdFilter):
            if condition.subject_id:
                text = f"Subject ID = {condition.subject_id}"
            else:
                text = "Subject ID = <empty>"
            return text, ":/icons/id_icon.svg"
        
        elif isinstance(condition, ModalityFilter):
            text = f"Modality = {condition.modality}"
            return text, ":/icons/folder_icon.svg"
        
        elif isinstance(condition, EntityFilter):
            text = f"{condition.entity_code} {condition.operator} {condition.value}"
            return text, ":/icons/label_icon.svg"
        
        elif isinstance(condition, ParticipantAttributeFilter):
            text = f"Subject.{condition.attribute_name} {condition.operator} {condition.value}"
            return text, ":/icons/participant_attribute_icon.svg"
        
        elif isinstance(condition, ChannelAttributeFilter):
            text = f"Channel.{condition.attribute_name} {condition.operator} {condition.value}"
            return text, ":/icons/channel_attribute_icon.svg"
        
        elif isinstance(condition, ElectrodeAttributeFilter):
            text = f"Electrode.{condition.attribute_name} {condition.operator} {condition.value}"
            return text, ":/icons/electrode_attribute_icon.svg"
        
        else:
            return "Unknown condition", ":/icons/help_icon.svg"
    
    @Slot()
    def _delete_item(self):
        """Delete selected tree item."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        
        # Confirm deletion if item has children
        if item.childCount() > 0:
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"This item has {item.childCount()} child item(s). Delete anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Remove from tree
        parent = item.parent()
        if parent:
            parent.removeChild(item)
        else:
            index = self.ui.filterTreeWidget.indexOfTopLevelItem(item)
            self.ui.filterTreeWidget.takeTopLevelItem(index)
        
        logger.debug("Deleted tree item")
    
    @Slot()
    def _move_up(self):
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
    
    @Slot()
    def _move_down(self):
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
    
    @Slot()
    def _cut_item(self):
        """Cut selected item to clipboard."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        
        # Store in clipboard
        self._clipboard_item = self._clone_tree_item(item)
        self._clipboard_is_cut = True
        self._cut_item_reference = item  # Store reference to the actual item
        
        # Visual feedback - gray out the item
        font = item.font(0)
        font.setItalic(True)
        item.setFont(0, font)
        item.setForeground(0, QBrush(QColor(Qt.GlobalColor.gray)))
        
        # Enable paste
        self.ui.actionPaste.setEnabled(True)
        
        logger.debug("Cut item to clipboard")
    
    @Slot()
    def _copy_item(self):
        """Copy selected item to clipboard."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        
        # Store in clipboard
        self._clipboard_item = self._clone_tree_item(item)
        self._clipboard_is_cut = False
        
        # Enable paste
        self.ui.actionPaste.setEnabled(True)
        
        logger.debug("Copied item to clipboard")
    
    @Slot()
    def _paste_item(self):
        """Paste item from clipboard."""
        if not self._clipboard_item:
            return
        
        selected_items = self.ui.filterTreeWidget.selectedItems()
        parent_item = None
        insert_index = None
        
        if selected_items:
            target_item = selected_items[0]
            target_condition = target_item.data(0, Qt.ItemDataRole.UserRole)
            
            # Prevent pasting an item into itself or its descendants
            if self._clipboard_is_cut and self._cut_item_reference and self._is_ancestor_or_self(self._cut_item_reference, target_item):
                QMessageBox.warning(
                    self,
                    "Invalid Operation",
                    "Cannot paste an item into itself or its descendants."
                )
                return
            
            # If target is a logical operation, paste as child
            if isinstance(target_condition, LogicalOperation):
                parent_item = target_item
                insert_index = None  # Append
            else:
                # Paste as sibling
                parent_item = target_item.parent()
                if parent_item:
                    insert_index = parent_item.indexOfChild(target_item) + 1
                else:
                    insert_index = self.ui.filterTreeWidget.indexOfTopLevelItem(target_item) + 1
        
        # Clone the clipboard item (in case we paste multiple times)
        pasted_item = self._clone_tree_item(self._clipboard_item)
        
        # Add to tree
        if parent_item:
            if insert_index is not None and insert_index < parent_item.childCount():
                parent_item.insertChild(insert_index, pasted_item)
            else:
                parent_item.addChild(pasted_item)
            parent_item.setExpanded(True)
        else:
            if insert_index is not None:
                self.ui.filterTreeWidget.insertTopLevelItem(insert_index, pasted_item)
            else:
                self.ui.filterTreeWidget.addTopLevelItem(pasted_item)
        
        # If it was cut, remove the original
        if self._clipboard_is_cut and self._cut_item_reference is not None:
            # Restore appearance first
            font = self._cut_item_reference.font(0)
            font.setItalic(False)
            self._cut_item_reference.setFont(0, font)
            self._cut_item_reference.setForeground(0, QBrush())
            
            # Remove the cut item
            parent = self._cut_item_reference.parent()
            if parent:
                parent.removeChild(self._cut_item_reference)
            else:
                index = self.ui.filterTreeWidget.indexOfTopLevelItem(self._cut_item_reference)
                self.ui.filterTreeWidget.takeTopLevelItem(index)
            
            # Clear cut state
            self._clipboard_item = None
            self._clipboard_is_cut = False
            self._cut_item_reference = None
            self.ui.actionPaste.setEnabled(False)
        
        # Select the pasted item
        self.ui.filterTreeWidget.setCurrentItem(pasted_item)
        
        logger.debug("Pasted item from clipboard")
    
    def _is_ancestor_or_self(self, ancestor: QTreeWidgetItem, item: QTreeWidgetItem) -> bool:
        """Check if ancestor is the same as item or an ancestor of item."""
        if ancestor == item:
            return True
        
        # Walk up the tree from item to see if we find ancestor
        current = item.parent()
        while current is not None:
            if current == ancestor:
                return True
            current = current.parent()
        
        return False
    
    def _clone_tree_item(self, item: QTreeWidgetItem) -> QTreeWidgetItem:
        """Deep clone a tree item with all children."""
        # Get the condition and deep copy it
        condition = item.data(0, Qt.ItemDataRole.UserRole)
        cloned_condition = self._deep_copy_condition(condition)
        
        # Create new tree item
        new_item = self._create_tree_item(cloned_condition)
        
        # Clone children recursively
        for i in range(item.childCount()):
            child_item = item.child(i)
            new_item.addChild(self._clone_tree_item(child_item))
        
        return new_item
    
    def _deep_copy_condition(self, condition):
        """Deep copy a condition object."""
        if isinstance(condition, LogicalOperation):
            return LogicalOperation(
                operator=condition.operator,
                conditions=[self._deep_copy_condition(c) for c in condition.conditions]
            )
        elif isinstance(condition, SubjectIdFilter):
            return SubjectIdFilter(subject_id=condition.subject_id)
        elif isinstance(condition, ModalityFilter):
            return ModalityFilter(modality=condition.modality)
        elif isinstance(condition, EntityFilter):
            return EntityFilter(
                entity_code=condition.entity_code,
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
            logger.warning(f"Unknown condition type for deep copy: {type(condition)}")
            return condition
    
    def _show_context_menu(self, position):
        """Show context menu for tree widget."""
        item = self.ui.filterTreeWidget.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        
        # Add submenu for adding items
        add_condition_menu = menu.addMenu(QIcon(":/icons/add_icon.svg"), "Add Condition")
        add_condition_menu.addAction(QIcon(":/icons/id_icon.svg"), "Subject ID", lambda: self._create_and_add_item('subject_id'))
        add_condition_menu.addAction(QIcon(":/icons/folder_icon.svg"), "Modality", lambda: self._create_and_add_item('modality'))
        add_condition_menu.addAction(QIcon(":/icons/label_icon.svg"), "Entity", lambda: self._create_and_add_item('entity'))
        add_condition_menu.addAction(QIcon(":/icons/participant_attribute_icon.svg"), "Participant Attribute", lambda: self._create_and_add_item('participant_attribute'))
        add_condition_menu.addAction(QIcon(":/icons/channel_attribute_icon.svg"), "Channel Attribute", lambda: self._create_and_add_item('channel_attribute'))
        add_condition_menu.addAction(QIcon(":/icons/electrode_attribute_icon.svg"), "Electrode Attribute", lambda: self._create_and_add_item('electrode_attribute'))
        
        add_group_menu = menu.addMenu(QIcon(":/icons/and_icon.svg"), "Add Group")
        add_group_menu.addAction(QIcon(":/icons/and_icon.svg"), "AND Group", lambda: self._create_and_add_item('AND'))
        add_group_menu.addAction(QIcon(":/icons/or_icon.svg"), "OR Group", lambda: self._create_and_add_item('OR'))
        add_group_menu.addAction(QIcon(":/icons/not_icon.svg"), "NOT Group", lambda: self._create_and_add_item('NOT'))
        
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
    
    # ==================== Editor Updates ====================
    
    @Slot()
    def _editor_logical_changed(self):
        """Handle logical operator change in editor."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        condition = item.data(0, Qt.ItemDataRole.UserRole)
        
        if isinstance(condition, LogicalOperation):
            # Update operator
            new_operator = self.ui.logicalOperatorComboBox.currentText()
            condition.operator = new_operator
            
            # Update tree display
            item.setText(0, new_operator)
            if new_operator == 'AND':
                item.setIcon(0, QIcon(":/icons/and_icon.svg"))
            elif new_operator == 'OR':
                item.setIcon(0, QIcon(":/icons/or_icon.svg"))
            elif new_operator == 'NOT':
                item.setIcon(0, QIcon(":/icons/not_icon.svg"))
    
    @Slot()
    def _editor_condition_type_changed(self, index):
        """Handle condition type change in editor."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        old_condition = item.data(0, Qt.ItemDataRole.UserRole)
        
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
        new_condition = self._create_condition(item_type)
        
        # Update tree item
        item.setData(0, Qt.ItemDataRole.UserRole, new_condition)
        # Only update display if it's a FilterCondition (not LogicalOperation)
        if isinstance(new_condition, FilterCondition):
            text, icon_path = self._get_condition_display(new_condition)
            item.setText(0, text)
            item.setIcon(0, QIcon(icon_path))
        
        # Update editor details page
        self.ui.conditionDetailsStackedWidget.setCurrentIndex(index)
        
        # Populate editor with new condition defaults
        self._block_editor_signals(True)
        self._populate_editor_for_condition(new_condition, index)
        self._block_editor_signals(False)
    
    def _populate_editor_for_condition(self, condition, page_index: int):
        """Populate editor fields for a condition."""
        if page_index == 0:  # Subject ID
            self.ui.subjectIdLineEdit.setText('')
        elif page_index == 1:  # Modality
            if self._available_modalities:
                self.ui.modalityComboBox.setCurrentIndex(0)
        elif page_index == 2:  # Entity
            if self._available_entities:
                self.ui.entityNameComboBox.setCurrentIndex(0)
            self.ui.entityOperatorComboBox.setCurrentText('equals')
            self.ui.entityValueLineEdit.setText('')
        elif page_index == 3:  # Participant Attribute
            if self._participant_attributes:
                self.ui.participantAttributeNameComboBox.setCurrentIndex(0)
            self.ui.participantAttributeOperatorComboBox.setCurrentText('equals')
            self.ui.participantAttributeValueLineEdit.setText('')
        elif page_index == 4:  # Channel Attribute
            if self._channel_attributes:
                self.ui.channelAttributeNameComboBox.setCurrentIndex(0)
            self.ui.channelAttributeOperatorComboBox.setCurrentText('equals')
            self.ui.channelAttributeValueLineEdit.setText('')
        elif page_index == 5:  # Electrode Attribute
            if self._electrode_attributes:
                self.ui.electrodeAttributeNameComboBox.setCurrentIndex(0)
            self.ui.electrodeAttributeOperatorComboBox.setCurrentText('equals')
            self.ui.electrodeAttributeValueLineEdit.setText('')
    
    @Slot()
    def _editor_details_changed(self):
        """Handle any condition detail change in editor."""
        selected_items = self.ui.filterTreeWidget.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        condition = item.data(0, Qt.ItemDataRole.UserRole)
        
        # Update condition based on current editor state
        if isinstance(condition, SubjectIdFilter):
            condition.subject_id = self.ui.subjectIdLineEdit.text()
        
        elif isinstance(condition, ModalityFilter):
            condition.modality = self.ui.modalityComboBox.currentText()
        
        elif isinstance(condition, EntityFilter):
            condition.entity_code = self.ui.entityNameComboBox.currentText()
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
        text, icon_path = self._get_condition_display(condition)
        item.setText(0, text)
    
    # ==================== Public API ====================
    
    def get_filter_expression(self) -> Optional[LogicalOperation]:
        """Build LogicalOperation from tree structure."""
        # If tree is empty, return None
        if self.ui.filterTreeWidget.topLevelItemCount() == 0:
            return None
        
        # If single top-level item, convert it
        if self.ui.filterTreeWidget.topLevelItemCount() == 1:
            root_item = self.ui.filterTreeWidget.topLevelItem(0)
            if root_item is not None:
                return self._tree_item_to_filter(root_item)
            return None
        
        # Multiple top-level items - wrap in AND
        conditions = []
        for i in range(self.ui.filterTreeWidget.topLevelItemCount()):
            item = self.ui.filterTreeWidget.topLevelItem(i)
            if item is not None:
                condition = self._tree_item_to_filter(item)
                if condition:
                    conditions.append(condition)
        
        if conditions:
            return LogicalOperation(operator='AND', conditions=conditions)
        return None
    
    def _tree_item_to_filter(self, item: QTreeWidgetItem):
        """Convert a tree item and its children to a filter condition."""
        condition = item.data(0, Qt.ItemDataRole.UserRole)
        
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
    
    def set_filter_expression(self, filter_expr: Optional[LogicalOperation]):
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
        item = self._create_tree_item(condition)
        
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
    
    def reset_filters(self):
        """Reset all filters by clearing the tree."""
        self.ui.filterTreeWidget.clear()
    
    def validate(self) -> tuple[bool, str]:
        """
        Validate the filter tree.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # For now, advanced mode is always valid
        # Could add validation for empty NOT groups, etc.
        return True, ""
