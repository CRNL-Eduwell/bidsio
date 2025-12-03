"""
About dialog for the application.

This module provides a dialog displaying application information.
"""

from PySide6.QtWidgets import QDialog

from bidsio.infrastructure.logging_config import get_logger
from bidsio.ui.forms.about_dialog_ui import Ui_AboutDialog


logger = get_logger(__name__)


class AboutDialog(QDialog):
    """
    About dialog showing application information.
    
    Uses generated UI from about_dialog.ui file.
    """
    
    def __init__(self, parent=None):
        """
        Initialize the About dialog.
        
        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI using generated class."""
        try:
            
            self.ui = Ui_AboutDialog()
            self.ui.setupUi(self)
            
            logger.debug("About dialog UI setup complete")
        except ImportError as e:
            logger.error(f"Failed to import generated UI file: {e}")
            logger.error("Run 'python scripts/generate_ui.py' to generate UI files")
            self.setWindowTitle("About bidsio")
            self.resize(400, 300)
