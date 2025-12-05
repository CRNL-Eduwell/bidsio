"""
Details panel widget for displaying context-sensitive information.

This widget displays information about selected items in a key-value format.
"""

from PySide6.QtWidgets import QWidget, QLabel, QFrame
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from bidsio.ui.forms.details_panel_ui import Ui_DetailsPanel


class DetailsPanel(QWidget):
    """
    Custom widget for displaying details about selected items.
    
    Shows information in sections with headers and key-value pairs.
    """
    
    def __init__(self, parent=None):
        """Initialize the details panel."""
        super().__init__(parent)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.ui = Ui_DetailsPanel()
        self.ui.setupUi(self)
        
        # Get reference to the main layout from UI
        self._layout = self.ui.mainLayout
    
    def clear(self):
        """Clear all content and show placeholder."""
        # Remove all widgets from layout immediately to avoid double layout calculation
        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)  # Remove from parent immediately
                widget.deleteLater()    # Schedule for cleanup
        
        # Re-add placeholder and spacer
        self.ui.placeholderLabel = QLabel("Select an item to view details")
        self.ui.placeholderLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ui.placeholderLabel.setWordWrap(True)
        font = self.ui.placeholderLabel.font()
        font.setPointSize(11)
        font.setItalic(True)
        self.ui.placeholderLabel.setFont(font)
        self._layout.addWidget(self.ui.placeholderLabel)
        self._layout.addStretch()
    
    def set_content(self, sections: list[dict]):
        """
        Set the content of the details panel.
        
        Args:
            sections: List of section dictionaries with structure:
                {
                    'title': 'Section Title',
                    'items': [
                        {'key': 'Key Name', 'value': 'Value'},
                        ...
                    ]
                }
        """
        # Clear existing content immediately to avoid double layout calculation
        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)  # Remove from parent immediately
                widget.deleteLater()    # Schedule for cleanup
        
        # Add sections
        for section in sections:
            self._add_section(section['title'], section.get('items', []))
        
        # Add stretch at the end
        self._layout.addStretch()
    
    def _add_section(self, title: str, items: list[dict]):
        """
        Add a section with title and key-value items.
        
        Args:
            title: Section title.
            items: List of {'key': ..., 'value': ...} dictionaries.
        """
        # Section title
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        self._layout.addWidget(title_label)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self._layout.addWidget(line)
        
        # Key-value pairs
        if items:
            for item in items:
                key = item.get('key', '')
                value = item.get('value', '')
                self._add_key_value_pair(key, value)
        else:
            # No items in section
            no_data_label = QLabel("No data available")
            no_data_label.setStyleSheet("color: gray; font-style: italic;")
            self._layout.addWidget(no_data_label)
        
        # Add spacing after section
        self._layout.addSpacing(15)
    
    def _add_key_value_pair(self, key: str, value: str):
        """
        Add a key-value pair to the layout.
        
        Args:
            key: The key/label.
            value: The value.
        """
        # Create a single label with key and value on the same line
        label = QLabel()
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | 
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        label.setWordWrap(True)
        label.setContentsMargins(10, 2, 0, 2)
        
        # Format: bold key, normal value
        label.setText(f"<b>{key}:</b> {value}")
        
        self._layout.addWidget(label)
