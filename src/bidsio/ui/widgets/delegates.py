"""
Custom Qt delegates for controlling widget behavior.

This module provides custom delegates for Qt views.
"""

from PySide6.QtWidgets import QStyledItemDelegate
from PySide6.QtCore import QSize


class CompactDelegate(QStyledItemDelegate):
    """Custom delegate to control row height in tree/list/table widgets."""
    
    def __init__(self, row_height: int = 24, parent=None):
        """
        Initialize the delegate.
        
        Args:
            row_height: Height in pixels for each row (default: 24).
                       Common values: 20 (very compact), 24 (compact), 28 (comfortable).
            parent: Parent widget.
        """
        super().__init__(parent)
        self._row_height = row_height
    
    def sizeHint(self, option, index):
        """
        Return custom size hint with specified row height.
        
        Args:
            option: Style options.
            index: Model index.
            
        Returns:
            QSize with custom height.
        """
        size = super().sizeHint(option, index)
        size.setHeight(self._row_height)
        return size
