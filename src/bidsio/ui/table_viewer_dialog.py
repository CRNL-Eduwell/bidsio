"""
Table viewer dialog.

This module provides a dialog for displaying CSV/TSV files in a table view.
"""

import csv
from pathlib import Path

from PySide6.QtWidgets import QDialog
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from bidsio.infrastructure.logging_config import get_logger
from bidsio.ui.forms.table_viewer_dialog_ui import Ui_TableViewerDialog


logger = get_logger(__name__)


class TableModel(QAbstractTableModel):
    """
    Table model for displaying CSV/TSV data.
    """
    
    def __init__(self, headers: list[str], rows: list[list[str]], parent=None):
        """
        Initialize the table model.
        
        Args:
            headers: Column headers.
            rows: Data rows.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._headers = headers
        self._rows = rows
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """Return the number of rows."""
        return len(self._rows)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        """Return the number of columns."""
        return len(self._headers)
    
    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        """Return data for the given index and role."""
        if not index.isValid():
            return None
        
        if role == Qt.ItemDataRole.DisplayRole:
            return self._rows[index.row()][index.column()]
        
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        """Return header data."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self._headers[section]
            else:
                return str(section + 1)
        
        return None


class TableViewerDialog(QDialog):
    """
    Dialog for viewing CSV/TSV files in a table format.
    """
    
    def __init__(self, file_path: Path, parent=None):
        """
        Initialize the table viewer dialog.
        
        Args:
            file_path: Path to the CSV/TSV file to display.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self._file_path = file_path
        
        self._setup_ui()
        self._load_table()
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.ui = Ui_TableViewerDialog()
        self.ui.setupUi(self)
        
        # Set file name in window title
        self.setWindowTitle(f"File: {self._file_path.name}")
        
        # Hide the file name label
        self.ui.fileNameLabel.hide()
    
    def _load_table(self):
        """Load and display the CSV/TSV file."""
        try:
            # Detect delimiter based on extension
            delimiter = '\t' if self._file_path.suffix.lower() == '.tsv' else ','
            
            # Read file
            with open(self._file_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f, delimiter=delimiter)
                
                # Read all rows
                all_rows = list(reader)
                
                if not all_rows:
                    logger.warning(f"Empty file: {self._file_path}")
                    return
                
                # First row is headers
                headers = all_rows[0]
                data_rows = all_rows[1:]
                
                # Create model and set it
                model = TableModel(headers, data_rows, self)
                self.ui.tableView.setModel(model)
                
                # Disable sorting to prevent confusion
                self.ui.tableView.setSortingEnabled(False)
                
                # Configure header to stretch sections proportionally
                header = self.ui.tableView.horizontalHeader()
                header.setStretchLastSection(True)
                
                # Resize columns to content
                self.ui.tableView.resizeColumnsToContents()
                
                # Add some padding to each column to ensure headers are fully visible
                for col in range(len(headers)):
                    current_width = self.ui.tableView.columnWidth(col)
                    self.ui.tableView.setColumnWidth(col, current_width + 20)
                
                logger.debug(f"Loaded table: {len(data_rows)} rows, {len(headers)} columns")
                
        except Exception as e:
            logger.error(f"Failed to load table file: {e}", exc_info=True)
            # Could show error in table view or message box
