"""
Main application window.

This module defines the main window UI, which should be loaded from a .ui file.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox
from PySide6.QtCore import Slot

from bidsio.infrastructure.logging_config import get_logger
from bidsio.core.repository import BidsRepository
from bidsio.core.models import BIDSDataset, FilterCriteria
from bidsio.ui.view_models import DatasetViewModel
from bidsio.ui.about_dialog import AboutDialog
from bidsio.ui.forms.main_window_ui import Ui_MainWindow


logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window.
    
    This class loads the UI from main_window.ui and wires up the signals/slots.
    Business logic is delegated to core/infrastructure modules.
    """
    
    def __init__(self, parent=None):
        """Initialize the main window."""
        super().__init__(parent)
        
        self._repository: Optional[BidsRepository] = None
        self._dataset: Optional[BIDSDataset] = None
        self._view_model: Optional[DatasetViewModel] = None
        
        self._setup_ui()
        self._connect_signals()
        
        logger.info("MainWindow initialized")
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Import the generated UI class
        try:
            # Setup UI using generated class
            self.ui = Ui_MainWindow()
            self.ui.setupUi(self)
            
            logger.debug("UI setup complete")
        except ImportError as e:
            logger.error(f"Failed to import generated UI file: {e}")
            logger.error("Run 'python scripts/generate_ui.py' to generate UI files from .ui sources")
            # Fallback to basic window
            self.setWindowTitle("bidsio - BIDS Dataset Explorer")
            self.resize(1200, 800)
    
    def _connect_signals(self):
        """Connect signals and slots."""
        # Connect menu actions - they are accessible via self.ui
        if hasattr(self.ui, 'actionLoadDataset'):
            self.ui.actionLoadDataset.triggered.connect(self.load_dataset)
        
        if hasattr(self.ui, 'actionClose'):
            self.ui.actionClose.triggered.connect(self.close)
        
        if hasattr(self.ui, 'actionAbout'):
            self.ui.actionAbout.triggered.connect(self.show_about)
        
        # TODO: connect toolbar buttons
        # TODO: connect dataset browser selection changes
        # TODO: connect filter controls
        # TODO: connect export action
        
        logger.debug("Signals connected")
    
    @Slot()
    def load_dataset(self):
        """
        Load a BIDS dataset directory.
        
        Shows a directory picker dialog and loads the selected dataset.
        """
        directory = QFileDialog.getExistingDirectory(
            self,
            "Load BIDS Dataset",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if directory:
            logger.info(f"Loading dataset from: {directory}")
            try:
                # TODO: actual loading implementation
                # self._repository = BidsRepository(Path(directory))
                # self._dataset = self._repository.load()
                # self._view_model = DatasetViewModel(self._dataset)
                # self._update_ui()
                
                QMessageBox.information(
                    self,
                    "Not Implemented",
                    "Dataset loading is not yet implemented."
                )
            except Exception as e:
                logger.error(f"Failed to load dataset: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to load dataset:\n{str(e)}"
                )
    
    @Slot()
    def show_about(self):
        """Show the About dialog."""
        dialog = AboutDialog(self)
        dialog.exec()
        logger.debug("About dialog shown")
    
    @Slot()
    def close_dataset(self):
        """Close the currently open dataset."""
        # TODO: clear current dataset
        # TODO: reset UI to empty state
        # TODO: clear view model
        
        logger.info("Closing dataset")
        pass
    
    @Slot()
    def apply_filters(self):
        """Apply current filter criteria to the dataset."""
        # TODO: gather filter criteria from UI controls
        # TODO: create FilterCriteria object
        # TODO: query repository with criteria
        # TODO: update view model with filtered results
        # TODO: refresh UI
        
        logger.info("Applying filters")
        pass
    
    @Slot()
    def export_selection(self):
        """Export the filtered dataset subset."""
        # TODO: show export dialog
        # TODO: gather export parameters
        # TODO: create ExportRequest
        # TODO: call export function from core.export
        # TODO: show progress dialog
        # TODO: handle completion or errors
        
        logger.info("Exporting selection")
        pass
    
    def _update_ui(self):
        """Update UI with current dataset/view model state."""
        # TODO: populate subject list
        # TODO: update statistics display
        # TODO: refresh table views
        # TODO: enable/disable actions based on state
        
        pass
    
    def closeEvent(self, event):
        """Handle window close event."""
        # TODO: save window geometry to settings
        # TODO: prompt to save any unsaved work
        # TODO: cleanup resources
        
        logger.info("Main window closing")
        event.accept()


# TODO: create separate dialog classes for:
# - Export configuration dialog
# - Filter configuration dialog
# - Dataset information dialog
# - About dialog
