"""
Progress dialog for loading operations.

This module provides a dialog for showing progress during long-running operations
like dataset loading.
"""

from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Signal, Slot, Qt

from .forms.progress_dialog_ui import Ui_ProgressDialog


class ProgressDialog(QDialog):
    """
    Dialog for showing progress during loading operations.
    
    This dialog displays a progress bar and status message during
    long-running operations like dataset loading.
    """
    
    # Signal emitted when the dialog should be closed
    finished = Signal()
    
    def __init__(self, parent=None):
        """
        Initialize the progress dialog.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI using generated class."""
        self.ui = Ui_ProgressDialog()
        self.ui.setupUi(self)
        
        # Set window flags to make it a proper dialog window
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.CustomizeWindowHint
        )
        
        # Ensure it's centered and stays on top
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
    
    @Slot(int, int, str)
    def update_progress(self, current: int, total: int, message: str):
        """
        Update the progress bar and message.
        
        Args:
            current: Current progress value.
            total: Total progress value.
            message: Status message to display.
        """
        if total > 0:
            percentage = int((current / total) * 100)
            self.ui.progressBar.setValue(percentage)
        
        self.ui.messageLabel.setText(message)
    
    @Slot()
    def complete(self):
        """Mark the operation as complete and close the dialog."""
        self.ui.progressBar.setValue(100)
        self.ui.messageLabel.setText("Loading complete!")
        self.accept()
