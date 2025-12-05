"""
Worker threads for background operations.

This module provides worker threads for long-running operations that should
not block the UI thread, such as dataset loading.
"""

from PySide6.QtCore import QThread, Signal

from bidsio.core.repository import BidsRepository
from bidsio.infrastructure.logging_config import get_logger


logger = get_logger(__name__)


class DatasetLoaderThread(QThread):
    """
    Worker thread for loading BIDS datasets without blocking the UI.
    
    This thread runs the dataset loading operation in the background and
    emits signals to update the progress dialog and notify completion.
    """
    
    # Signal emitted when progress updates (current, total, message)
    progress_updated = Signal(int, int, str)
    
    # Signal emitted when loading is complete (dataset)
    loading_complete = Signal(object)
    
    # Signal emitted when an error occurs (exception)
    loading_error = Signal(Exception)
    
    def __init__(self, repository: BidsRepository, parent=None):
        """
        Initialize the loader thread.
        
        Args:
            repository: BidsRepository instance to use for loading.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._repository = repository
    
    def run(self):
        """Run the dataset loading operation."""
        try:
            # Load dataset with progress callback
            dataset = self._repository.load(progress_callback=self._progress_callback)
            self.loading_complete.emit(dataset)
        except Exception as e:
            logger.error(f"Error loading dataset in thread: {e}", exc_info=True)
            self.loading_error.emit(e)
    
    def _progress_callback(self, current: int, total: int, message: str):
        """
        Progress callback invoked by the loader.
        
        Args:
            current: Current progress value.
            total: Total progress value.
            message: Status message.
        """
        self.progress_updated.emit(current, total, message)
