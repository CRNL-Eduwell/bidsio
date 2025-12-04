"""
JSON viewer dialog.

This module provides a dialog for displaying JSON files in a tree view format.
"""

import json
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QDialog, QTreeWidgetItem
from PySide6.QtCore import Qt

from bidsio.infrastructure.logging_config import get_logger
from bidsio.ui.forms.json_viewer_dialog_ui import Ui_JsonViewerDialog


logger = get_logger(__name__)


class JsonViewerDialog(QDialog):
    """
    Dialog for viewing JSON files in a tree structure.
    
    Displays JSON data with keys and values, handling nested objects and arrays.
    """
    
    def __init__(self, file_path: Path, parent=None):
        """
        Initialize the JSON viewer dialog.
        
        Args:
            file_path: Path to the JSON file to display.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self._file_path = file_path
        
        self._setup_ui()
        self._load_json()
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.ui = Ui_JsonViewerDialog()
        self.ui.setupUi(self)
        
        # Set file name in window title
        self.setWindowTitle(f"File: {self._file_path.name}")
        
        # Hide the file name label
        self.ui.fileNameLabel.hide()
        
        # Configure tree widget
        self.ui.jsonTreeWidget.setColumnWidth(0, 400)
    
    def _load_json(self):
        """Load and display the JSON file."""
        try:
            with open(self._file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Populate tree with JSON data
            self._populate_tree(data)
            
            logger.debug(f"Loaded JSON file: {self._file_path}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON file: {e}")
            error_item = QTreeWidgetItem(["Error", f"Invalid JSON: {str(e)}"])
            self.ui.jsonTreeWidget.addTopLevelItem(error_item)
            
        except Exception as e:
            logger.error(f"Failed to load JSON file: {e}", exc_info=True)
            error_item = QTreeWidgetItem(["Error", f"Failed to load: {str(e)}"])
            self.ui.jsonTreeWidget.addTopLevelItem(error_item)
    
    def _populate_tree(self, data: Any, parent: QTreeWidgetItem | None = None):
        """
        Recursively populate the tree widget with JSON data.
        
        Args:
            data: JSON data (dict, list, or primitive).
            parent: Parent tree item (None for root).
        """
        if isinstance(data, dict):
            for key, value in data.items():
                self._add_item(key, value, parent)
                
        elif isinstance(data, list):
            for index, value in enumerate(data):
                self._add_item(f"[{index}]", value, parent)
                
        else:
            # Primitive value - should not happen at root
            self._add_item("value", data, parent)
    
    def _add_item(self, key: str, value: Any, parent: QTreeWidgetItem | None = None):
        """
        Add a key-value pair to the tree.
        
        Args:
            key: Key name.
            value: Value (can be nested dict/list or primitive).
            parent: Parent tree item (None for root).
        """
        if isinstance(value, dict):
            # Create parent item for nested object
            item = QTreeWidgetItem([key, "{object}"])
            if parent:
                parent.addChild(item)
            else:
                self.ui.jsonTreeWidget.addTopLevelItem(item)
            
            # Add nested items
            for nested_key, nested_value in value.items():
                self._add_item(nested_key, nested_value, item)
                
        elif isinstance(value, list):
            # Create parent item for array
            item = QTreeWidgetItem([key, f"[array, {len(value)} items]"])
            if parent:
                parent.addChild(item)
            else:
                self.ui.jsonTreeWidget.addTopLevelItem(item)
            
            # Add array items
            for index, array_value in enumerate(value):
                self._add_item(f"[{index}]", array_value, item)
                
        else:
            # Primitive value
            value_str = str(value) if value is not None else "null"
            item = QTreeWidgetItem([key, value_str])
            
            if parent:
                parent.addChild(item)
            else:
                self.ui.jsonTreeWidget.addTopLevelItem(item)
