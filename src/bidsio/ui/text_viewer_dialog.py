"""
Text viewer dialog.

This module provides a dialog for displaying text and markdown files.
"""

from pathlib import Path

from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Qt

from bidsio.infrastructure.logging_config import get_logger
from bidsio.ui.forms.text_viewer_dialog_ui import Ui_TextViewerDialog


logger = get_logger(__name__)

# Try to import markdown library for better rendering
try:
    import markdown
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False
    logger.debug("markdown library not available, using Qt's basic markdown support")


class TextViewerDialog(QDialog):
    """
    Dialog for viewing text and markdown files.
    
    Supports plain text and markdown formatting.
    """
    
    def __init__(self, file_path: Path, parent=None):
        """
        Initialize the text viewer dialog.
        
        Args:
            file_path: Path to the text/markdown file to display.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self._file_path = file_path
        
        self._setup_ui()
        self._load_text()
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.ui = Ui_TextViewerDialog()
        self.ui.setupUi(self)
        
        # Set file name in window title
        self.setWindowTitle(f"File: {self._file_path.name}")
        
        # Hide the file name label
        self.ui.fileNameLabel.hide()
    
    def _load_text(self):
        """Load and display the text file."""
        try:
            # Try UTF-8 first, then fall back to other encodings
            content = None
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(self._file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                # Last resort - read as binary and decode with errors='replace'
                with open(self._file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            
            # Check if file is markdown (by extension or name)
            is_markdown = (
                self._file_path.suffix.lower() in ['.md', '.markdown'] or
                self._file_path.name.upper() in ['README', 'CHANGES']
            )
            
            if is_markdown:
                if HAS_MARKDOWN:
                    # Use markdown library for better HTML rendering
                    html_content = markdown.markdown(
                        content,
                        extensions=['extra', 'codehilite', 'tables', 'fenced_code']
                    )
                    self.ui.textBrowser.setHtml(html_content)
                else:
                    # Fall back to Qt's basic markdown support
                    self.ui.textBrowser.setMarkdown(content)
            else:
                # Display as plain text
                self.ui.textBrowser.setPlainText(content)
            
            logger.debug(f"Loaded text file: {self._file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load text file: {e}", exc_info=True)
            self.ui.textBrowser.setPlainText(f"Error loading file:\n{str(e)}")
