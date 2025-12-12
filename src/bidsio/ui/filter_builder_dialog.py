"""
Filter Builder Dialog.

This dialog allows users to build complex filter expressions for filtering subjects.
Provides both Simple mode (AND-only rows) and Advanced mode (full logical expressions).
"""

import json
import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QDialog, QMessageBox, QInputDialog, QListWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialogButtonBox, QListWidgetItem
from PySide6.QtCore import Slot, Qt, QFile, QTextStream, QTimer

from bidsio.infrastructure.logging_config import get_logger
from bidsio.infrastructure.paths import get_filter_presets_directory
from bidsio.ui.text_viewer_dialog import TextViewerDialog
from bidsio.core.models import BIDSDataset
from bidsio.core.filters import LogicalOperation
from bidsio.ui.forms.filter_builder_dialog_ui import Ui_FilterBuilderDialog
from bidsio.ui.widgets.simple_filter_builder_widget import SimpleFilterBuilderWidget
from bidsio.ui.widgets.advanced_filter_builder_widget import AdvancedFilterBuilderWidget


logger = get_logger(__name__)


class FilterBuilderDialog(QDialog):
    """
    Dialog for building filter expressions.
    
    Provides two modes for creating filters:
    
    - **Simple Mode**: Quick filter creation with rows of conditions combined with AND logic.
      Ideal for straightforward filtering needs.
    
    - **Advanced Mode**: Full logical expression builder with tree view for nested operations
      (AND/OR/NOT), visual representation, cut/copy/paste, condition reordering, and 
      dynamic editor panels. Supports complex filter expressions.
    
    Both modes support saving and loading filter presets.
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
        
        self._setup_ui()
        self._setup_widgets()
        self._connect_signals()
        
        # Restore previous filter state to UI
        if previous_filter:
            # Check if filter is complex (has OR/NOT or nesting)
            if self._is_complex_filter(previous_filter):
                # Set to advanced mode
                self.ui.tabWidget.setCurrentIndex(1)
                self._advanced_widget.set_filter_expression(previous_filter)
            else:
                # Set to simple mode
                self.ui.tabWidget.setCurrentIndex(0)
                self._simple_widget.set_filter_expression(previous_filter)
        
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
    
    def _setup_widgets(self):
        """Setup the filter builder widgets."""
        # Replace placeholder widgets with our custom widgets initialized with dataset
        # Remove the placeholder widgets created by Qt Designer
        old_simple = self.ui.simpleFilterWidget
        old_advanced = self.ui.advancedFilterWidget
        
        # Create new widgets with dataset
        self._simple_widget = SimpleFilterBuilderWidget(self._dataset, self.ui.simpleTab)
        self._advanced_widget = AdvancedFilterBuilderWidget(self._dataset, self.ui.advancedTab)
        
        # Replace in layouts
        simple_layout = self.ui.simpleTab.layout()
        if simple_layout:
            simple_layout.replaceWidget(old_simple, self._simple_widget)
        
        advanced_layout = self.ui.advancedTab.layout()
        if advanced_layout:
            advanced_layout.replaceWidget(old_advanced, self._advanced_widget)
        
        # Delete old widgets
        old_simple.deleteLater()
        old_advanced.deleteLater()
        
        # Update UI references
        self.ui.simpleFilterWidget = self._simple_widget
        self.ui.advancedFilterWidget = self._advanced_widget
    
    def _connect_signals(self):
        """Connect UI signals to slots."""
        # Dialog buttons
        apply_button = self.ui.buttonBox.button(self.ui.buttonBox.StandardButton.Apply)
        if apply_button:
            apply_button.clicked.connect(self._apply_filter)
        
        reset_button = self.ui.buttonBox.button(self.ui.buttonBox.StandardButton.Reset)
        if reset_button:
            reset_button.clicked.connect(self._reset_filters)
        
        # Preset buttons
        self.ui.savePresetButton.clicked.connect(self._save_preset)
        self.ui.loadPresetButton.clicked.connect(self._load_preset)
        self.ui.helpButton.clicked.connect(self._show_help)
        
        # Tab switching
        self.ui.tabWidget.currentChanged.connect(self._on_tab_changed)
    
    @Slot()
    def _apply_filter(self):
        """Build filter expression from UI and accept dialog."""
        current_tab = self.ui.tabWidget.currentIndex()
        
        if current_tab == 0:  # Simple mode
            self._filter_expr = self._simple_widget.get_filter_expression()
        else:  # Advanced mode
            self._filter_expr = self._advanced_widget.get_filter_expression()
        
        self.accept()
    
    @Slot()
    def _reset_filters(self):
        """Reset all filters in the current mode."""
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
                self._simple_widget.reset_filters()
            else:  # Advanced mode
                self._advanced_widget.reset_filters()
    
    @Slot()
    def _save_preset(self):
        """Save current filter expression as a preset."""
        current_tab = self.ui.tabWidget.currentIndex()
        
        # Build filter from current mode
        if current_tab == 0:  # Simple mode
            # Validate first
            is_valid, error_msg = self._simple_widget.validate()
            if not is_valid:
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    error_msg
                )
                return
            
            filter_expr = self._simple_widget.get_filter_expression()
        else:  # Advanced mode
            # Validate first
            is_valid, error_msg = self._advanced_widget.validate()
            if not is_valid:
                QMessageBox.warning(
                    self,
                    "Validation Error",
                    error_msg
                )
                return
            
            filter_expr = self._advanced_widget.get_filter_expression()
        
        if not filter_expr:
            QMessageBox.information(
                self,
                "No Filter",
                "Please create a filter before saving a preset."
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
            with open(preset_path, 'w', encoding='utf-8') as f:
                data = {
                    'version': '1.0',
                    'mode': mode,
                    'is_complex': is_complex,
                    'filter': filter_expr.to_dict()
                }
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved filter preset: {preset_path}")
            QMessageBox.information(
                self,
                "Preset Saved",
                f"Filter preset '{name}' has been saved."
            )
        except Exception as e:
            logger.error(f"Failed to save preset: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Could not save preset:\n{str(e)}"
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
                "No filter presets found. Save a filter as a preset first."
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
            
            # Extract filter data
            if 'filter' in data:
                filter_dict = data['filter']
            else:
                # Legacy format - entire file is the filter
                filter_dict = data
            
            # Reconstruct filter object
            filter_expr = LogicalOperation.from_dict(filter_dict)
            
            # Get mode info if available
            suggested_mode = data.get('mode', 'simple')
            is_complex = data.get('is_complex', False)
            
            # Determine which mode to use
            if is_complex or self._is_complex_filter(filter_expr):
                # Switch to advanced mode
                self.ui.tabWidget.setCurrentIndex(1)
                self._advanced_widget.set_filter_expression(filter_expr)
            else:
                # Switch to simple mode
                self.ui.tabWidget.setCurrentIndex(0)
                self._simple_widget.set_filter_expression(filter_expr)
            
            logger.info(f"Loaded filter preset: {selected_file}")
            
        except Exception as e:
            logger.error(f"Failed to load preset: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Load Failed",
                f"Could not load preset:\n{str(e)}"
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
                logger.info(f"Deleted filter preset: {preset_file}")
                QMessageBox.information(
                    self,
                    "Preset Deleted",
                    f"Filter preset '{preset_name}' has been deleted."
                )
            except Exception as e:
                logger.error(f"Failed to delete preset: {e}", exc_info=True)
                QMessageBox.critical(
                    self,
                    "Delete Failed",
                    f"Could not delete preset:\n{str(e)}"
                )
    
    @Slot()
    def _show_help(self):
        """Show the filtering help documentation."""
        try:
            # Load help content from resources
            help_file = QFile(":/filtering_help.md")
            if not help_file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
                raise Exception("Could not open help file from resources")
            
            text_stream = QTextStream(help_file)
            help_content = text_stream.readAll()
            help_file.close()
            
            # Create a temporary file to pass to TextViewerDialog
            # (TextViewerDialog expects a file path)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
                f.write(help_content)
                temp_path = Path(f.name)
            
            # Show the help dialog
            # Important: Pass None as parent to make it independent
            # This prevents crashes when filter dialog closes before help dialog is destroyed
            dialog = TextViewerDialog(temp_path, parent=None)
            dialog.setWindowTitle("Filtering Subjects - Help")
            dialog.resize(800, 600)
            # Set window modality to application modal (blocks filter dialog)
            dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
            dialog.exec()
            
            # Clean up temp file after a delay to allow WebEngine to finish
            def cleanup_temp_file():
                try:
                    if temp_path.exists():
                        temp_path.unlink()
                except Exception as e:
                    logger.debug(f"Could not delete temp file: {e}")
            
            # Delay cleanup by 500ms to ensure WebEngine has released the file
            QTimer.singleShot(500, cleanup_temp_file)
            
            logger.debug("Displayed filtering help documentation")
            
        except Exception as e:
            logger.error(f"Failed to show help: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "Help Not Available",
                f"Could not load help documentation:\n{str(e)}"
            )
    
    def _on_tab_changed(self, index):
        """Handle tab switching between Simple and Advanced modes."""
        if index == 0:  # Switching to Simple mode
            # Try to convert from Advanced to Simple
            advanced_filter = self._advanced_widget.get_filter_expression()
            if advanced_filter and not self._can_convert_advanced_to_simple(advanced_filter):
                # Can't convert - show warning and switch back
                QMessageBox.warning(
                    self,
                    "Cannot Switch to Simple Mode",
                    "The current filter uses OR/NOT operations or nested groups "
                    "which are not supported in Simple mode.\n\n"
                    "Please simplify your filter or stay in Advanced mode."
                )
                # Switch back to advanced
                self.ui.tabWidget.blockSignals(True)
                self.ui.tabWidget.setCurrentIndex(1)
                self.ui.tabWidget.blockSignals(False)
            else:
                # Can convert - always sync (even if None to clear)
                self._simple_widget.set_filter_expression(advanced_filter)
        
        elif index == 1:  # Switching to Advanced mode
            # Convert from Simple to Advanced - always sync (even if None to clear)
            # Include incomplete conditions so users don't lose their work
            simple_filter = self._simple_widget.get_filter_expression(include_incomplete=True)
            self._advanced_widget.set_filter_expression(simple_filter)
    
    def _can_convert_advanced_to_simple(self, filter_expr: LogicalOperation) -> bool:
        """Check if Advanced filter can be converted to Simple mode."""
        if not filter_expr:
            return True
        
        # Must be an AND operation
        if not isinstance(filter_expr, LogicalOperation) or filter_expr.operator != 'AND':
            return False
        
        # All children must be conditions (no nested logical operations)
        for condition in filter_expr.conditions:
            if isinstance(condition, LogicalOperation):
                return False
        
        return True
    
    def get_filter_expression(self) -> Optional[LogicalOperation]:
        """
        Get the built filter expression.
        
        Returns:
            LogicalOperation if filter was applied, None otherwise.
        """
        return self._filter_expr
