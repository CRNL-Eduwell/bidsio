"""
Worker threads for background operations.

This module provides worker threads for long-running operations that should
not block the UI thread, such as dataset loading and exporting.
"""

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from bidsio.core.repository import BidsRepository
from bidsio.core.export import ExportRequest, export_dataset
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


class ExportWorkerThread(QThread):
    """
    Worker thread for exporting BIDS dataset subsets without blocking the UI.
    
    This thread runs the export operation in the background and emits signals
    to update the progress dialog and notify completion.
    """
    
    # Signal emitted when progress updates (current, total, filename)
    progress_updated = Signal(int, int, str)
    
    # Signal emitted when export is complete (output_path)
    export_complete = Signal(Path)
    
    # Signal emitted when an error occurs (error_message)
    export_error = Signal(str)
    
    def __init__(self, export_request: ExportRequest, parent=None):
        """
        Initialize the export worker thread.
        
        Args:
            export_request: ExportRequest with configuration.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._export_request = export_request
        self._cancelled = False
    
    def run(self):
        """Run the export operation."""
        try:
            # Export dataset with progress callback
            output_path = export_dataset(
                request=self._export_request,
                progress_callback=self._progress_callback
            )
            
            if not self._cancelled:
                self.export_complete.emit(output_path)
                
        except Exception as e:
            logger.error(f"Error exporting dataset in thread: {e}", exc_info=True)
            if not self._cancelled:
                self.export_error.emit(str(e))
    
    def cancel(self):
        """Cancel the export operation."""
        self._cancelled = True
        logger.info("Export cancelled by user")
    
    def _progress_callback(self, current: int, total: int, filepath: Path):
        """
        Progress callback invoked during export.
        
        Args:
            current: Current file number.
            total: Total number of files.
            filepath: Path of current file being copied.
        """
        if not self._cancelled:
            self.progress_updated.emit(current, total, str(filepath))
