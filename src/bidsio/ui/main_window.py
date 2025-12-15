"""
Main application window.

This module defines the main window UI, which should be loaded from a .ui file.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional
from collections import Counter

from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QTreeWidgetItem, QApplication
from PySide6.QtGui import QAction, QIcon, QColor, QBrush
from PySide6.QtCore import Slot, Qt, QFile, QIODevice
from numpy import invert
from qt_material import apply_stylesheet

from bidsio.infrastructure.logging_config import get_logger
from bidsio.infrastructure.paths import get_persistent_data_directory
from bidsio.config.settings import get_settings_manager, get_settings
from bidsio.core.repository import BidsRepository
from bidsio.core.models import BIDSDataset, BIDSSubject, BIDSSession, BIDSFile, BIDSDerivative
from bidsio.core.filters import apply_filter, LogicalOperation
from bidsio.ui.about_dialog import AboutDialog
from bidsio.ui.preferences_dialog import PreferencesDialog
from bidsio.ui.json_viewer_dialog import JsonViewerDialog
from bidsio.ui.table_viewer_dialog import TableViewerDialog
from bidsio.ui.text_viewer_dialog import TextViewerDialog
from bidsio.ui.progress_dialog import ProgressDialog
from bidsio.ui.export_dialog import ExportDialog
from bidsio.ui.filter_builder_dialog import FilterBuilderDialog
from bidsio.ui.workers import DatasetLoaderThread, ExportWorkerThread
from bidsio.ui.widgets.details_panel import DetailsPanel
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
        self._filtered_dataset: Optional[BIDSDataset] = None
        self._active_filter: Optional[LogicalOperation] = None
        self._details_panel: Optional[DetailsPanel] = None
        self._last_dialog_filter: Optional[LogicalOperation] = None  # Last filter state in dialog
        
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
            
            # Replace the placeholder in the details panel with our custom widget
            self._details_panel = DetailsPanel()
            
            # Clear the existing layout and add our details panel
            if hasattr(self.ui, 'detailsLayout'):
                # Remove existing widgets from layout
                while self.ui.detailsLayout.count():
                    item = self.ui.detailsLayout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
                
                # Add our custom details panel
                self.ui.detailsLayout.addWidget(self._details_panel)
            
            # Apply window size from settings
            settings = get_settings()
            self.resize(settings.window_width, settings.window_height)

            # Set splitter sizes (60% tree, 40% details panel)
            if hasattr(self.ui, 'mainSplitter'):
                self.ui.mainSplitter.setSizes([int(settings.window_width * 0.6), int(settings.window_width * 0.4)])
            
            # Populate recent datasets menu
            self._update_recent_menu()
            
            logger.debug("UI setup complete")
        except ImportError as e:
            logger.error(f"Failed to import generated UI file: {e}")
            logger.error("Run 'python scripts/generate_ui.py' to generate UI files from .ui sources")
            # Fallback to basic window
            self.setWindowTitle("bidsio - BIDS Dataset Explorer")
            settings = get_settings()
            self.resize(settings.window_width, settings.window_height)
    
    def _connect_signals(self):
        """Connect signals and slots."""
        # Connect menu actions - they are accessible via self.ui
        if hasattr(self.ui, 'actionLoadDataset'):
            self.ui.actionLoadDataset.triggered.connect(self.load_dataset)
        
        if hasattr(self.ui, 'actionClose'):
            self.ui.actionClose.triggered.connect(self.close)
        
        if hasattr(self.ui, 'actionAbout'):
            self.ui.actionAbout.triggered.connect(self.show_about)
        
        if hasattr(self.ui, 'actionPreferences'):
            self.ui.actionPreferences.triggered.connect(self.show_preferences)
        
        # Connect export action and button
        if hasattr(self.ui, 'actionExport'):
            self.ui.actionExport.triggered.connect(self.export_selection)
        
        if hasattr(self.ui, 'exportButton'):
            self.ui.exportButton.clicked.connect(self.export_selection)
        
        if hasattr(self.ui, 'filterButton'):
            self.ui.filterButton.clicked.connect(self._show_filter_dialog)
        
        if hasattr(self.ui, 'clearFilterButton'):
            self.ui.clearFilterButton.clicked.connect(self._clear_filter)
        
        # Connect filter menu actions
        if hasattr(self.ui, 'actionFilter'):
            self.ui.actionFilter.triggered.connect(self._show_filter_dialog)
        
        if hasattr(self.ui, 'actionClearFilter'):
            self.ui.actionClearFilter.triggered.connect(self._clear_filter)
        
        # Connect tree widget selection
        if hasattr(self.ui, 'datasetTreeWidget'):
            self.ui.datasetTreeWidget.itemSelectionChanged.connect(self._on_tree_selection_changed)
            self.ui.datasetTreeWidget.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
            #self.ui.datasetTreeWidget.setItemDelegate(CompactDelegate(row_height=24, parent=self))
            self.ui.datasetTreeWidget.setUniformRowHeights(True)
        
        logger.debug("Signals connected")
    
    def _update_recent_menu(self):
        """Update the recent datasets menu with current list."""
        if not hasattr(self.ui, 'menuOpenRecent'):
            return
        
        # Clear existing actions
        self.ui.menuOpenRecent.clear()
        
        # Get recent datasets from settings
        settings_manager = get_settings_manager()
        settings = settings_manager.get()
        recent_datasets = settings.recent_datasets
        
        if not recent_datasets:
            # Add a disabled "No recent datasets" action
            no_recent_action = QAction("No recent datasets", self)
            no_recent_action.setEnabled(False)
            self.ui.menuOpenRecent.addAction(no_recent_action)
        else:
            # Add action for each recent dataset
            for dataset_path in recent_datasets:
                action = QAction(dataset_path, self)
                action.triggered.connect(lambda checked=False, path=dataset_path: self._load_recent_dataset(path))
                self.ui.menuOpenRecent.addAction(action)
            
            # Add separator and "Clear Recent" action
            self.ui.menuOpenRecent.addSeparator()
            clear_action = QAction("Clear Recent Datasets", self)
            clear_action.triggered.connect(self._clear_recent_datasets)
            self.ui.menuOpenRecent.addAction(clear_action)
        
        logger.debug(f"Recent menu updated with {len(recent_datasets)} items")
    
    @Slot()
    def _load_recent_dataset(self, dataset_path: str):
        """
        Load a dataset from the recent datasets list.
        
        Args:
            dataset_path: Path to the dataset to load.
        """
        logger.info(f"Loading recent dataset: {dataset_path}")
        
        # Check if path exists
        if not Path(dataset_path).exists():
            QMessageBox.warning(
                self,
                "Dataset Not Found",
                f"The dataset path no longer exists:\n{dataset_path}\n\n"
                f"It will be removed from recent datasets."
            )
            # Remove from recent datasets
            settings_manager = get_settings_manager()
            settings = settings_manager.get()
            if dataset_path in settings.recent_datasets:
                settings.recent_datasets.remove(dataset_path)
                settings_manager.save()
                self._update_recent_menu()
            return
        
        # Start loading with progress dialog
        self._start_dataset_loading(Path(dataset_path))
    
    @Slot()
    def _clear_recent_datasets(self):
        """Clear the recent datasets list."""
        reply = QMessageBox.question(
            self,
            "Clear Recent Datasets",
            "Are you sure you want to clear the recent datasets list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            settings_manager = get_settings_manager()
            settings = settings_manager.get()
            settings.recent_datasets.clear()
            settings_manager.save()
            self._update_recent_menu()
            logger.info("Recent datasets cleared")
    
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
            self._start_dataset_loading(Path(directory))
    
    def _start_dataset_loading(self, dataset_path: Path):
        """
        Start loading a dataset with progress dialog.
        
        This method creates a repository, validates the path, and starts
        the loading operation in a background thread with a progress dialog.
        
        Args:
            dataset_path: Path to the BIDS dataset to load.
        """
        try:
            # Create repository (this validates the path)
            self._repository = BidsRepository(dataset_path)
            
            # Check if lazy loading is enabled
            settings = get_settings()
            if settings.lazy_loading:
                # Lazy loading: load immediately in main thread (will be fast)
                self._dataset = self._repository.load()
                self._on_dataset_loaded(self._dataset)
                
                # Add to recent datasets
                settings_manager = get_settings_manager()
                settings_manager.add_recent_dataset(str(dataset_path))
                self._update_recent_menu()
            else:
                # Eager loading: load in background thread with progress dialog
                self._start_threaded_loading(dataset_path)
                
        except FileNotFoundError as e:
            logger.error(f"Dataset path not found: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Dataset path not found:\n{str(e)}"
            )
        except ValueError as e:
            logger.error(f"Invalid BIDS dataset: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Invalid BIDS dataset:\n{str(e)}\n\n"
                f"Make sure the directory contains a dataset_description.json file."
            )
        except Exception as e:
            logger.error(f"Failed to initialize dataset loading: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load dataset:\n{str(e)}"
            )
    
    def _start_threaded_loading(self, dataset_path: Path):
        """
        Start loading dataset in a background thread with progress dialog.
        
        Args:
            dataset_path: Path to the BIDS dataset to load.
        """
        # Ensure repository exists
        if self._repository is None:
            raise ValueError("Repository not initialized")
        
        # Create progress dialog
        progress_dialog = ProgressDialog(self)
        progress_dialog.setWindowTitle("Loading Dataset")
        
        # Create loader thread
        loader_thread = DatasetLoaderThread(self._repository, self)
        
        # Connect signals
        loader_thread.progress_updated.connect(progress_dialog.update_progress)
        loader_thread.loading_complete.connect(
            lambda dataset: self._on_threaded_loading_complete(dataset, dataset_path, progress_dialog)
        )
        loader_thread.loading_error.connect(
            lambda error: self._on_threaded_loading_error(error, progress_dialog)
        )
        
        # Start loading
        loader_thread.start()
        
        # Show progress dialog (blocks until loading completes)
        progress_dialog.exec()
    
    def _on_threaded_loading_complete(self, dataset: BIDSDataset, dataset_path: Path, progress_dialog: ProgressDialog):
        """
        Handle successful completion of threaded dataset loading.
        
        Args:
            dataset: The loaded dataset.
            dataset_path: Path to the dataset.
            progress_dialog: The progress dialog to close.
        """
        self._dataset = dataset
        
        # Close progress dialog
        progress_dialog.complete()
        
        # Update UI with loaded dataset
        self._on_dataset_loaded(dataset)
        
        # Add to recent datasets
        settings_manager = get_settings_manager()
        settings_manager.add_recent_dataset(str(dataset_path))
        self._update_recent_menu()
        
        logger.info(f"Dataset loaded successfully in thread")
    
    def _on_threaded_loading_error(self, error: Exception, progress_dialog: ProgressDialog):
        """
        Handle error during threaded dataset loading.
        
        Args:
            error: The exception that occurred.
            progress_dialog: The progress dialog to close.
        """
        # Close progress dialog
        progress_dialog.reject()
        
        # Show error message
        logger.error(f"Failed to load dataset in thread: {error}", exc_info=True)
        QMessageBox.critical(
            self,
            "Error",
            f"Failed to load dataset:\n{str(error)}"
        )
    
    def _on_dataset_loaded(self, dataset: BIDSDataset):
        """
        Handle successful dataset loading (common for both lazy and eager loading).
        
        Args:
            dataset: The loaded dataset.
        """
        # Update UI with loaded dataset
        self._update_ui()
        
        # Enable export and filter actions now that dataset is loaded
        if hasattr(self.ui, 'actionExport'):
            self.ui.actionExport.setEnabled(True)
        if hasattr(self.ui, 'exportButton'):
            self.ui.exportButton.setEnabled(True)
        if hasattr(self.ui, 'filterButton'):
            self.ui.filterButton.setEnabled(True)
        if hasattr(self.ui, 'actionFilter'):
            self.ui.actionFilter.setEnabled(True)
        
        # Show success message
        num_subjects = len(dataset.subjects)
        dataset_name = dataset.dataset_description.get('Name', 'Unknown')
        logger.info(f"Dataset loaded successfully: {dataset_name}, {num_subjects} subjects")
    
    def _extract_custom_qss(self) -> Optional[Path]:
        """
        Extract the custom QSS file from resources to persistent data folder.
        
        Returns:
            Path to the extracted QSS file, or None if extraction failed.
        """
        try:
            # Get persistent data directory
            persistent_dir = get_persistent_data_directory()
            persistent_dir.mkdir(parents=True, exist_ok=True)
            
            # Target path for the custom QSS file
            qss_target = persistent_dir / "custom.qss"
            
            # Read the QSS file from Qt resources
            qss_resource = QFile(":/custom.qss")
            if not qss_resource.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
                logger.error(f"Failed to open resource: {qss_resource.errorString()}")
                return None
            
            # Read content from resource
            qss_content = bytes(qss_resource.readAll().data()).decode('utf-8')
            qss_resource.close()
            
            # Write to persistent data folder
            with open(qss_target, 'w', encoding='utf-8') as f:
                f.write(qss_content)
            
            logger.info(f"Custom QSS file extracted to: {qss_target}")
            return qss_target
            
        except Exception as e:
            logger.error(f"Failed to extract custom QSS file: {e}")
            return None
    
    def apply_theme(self, theme: str):
        """
        Apply the specified theme to the application.
        
        Args:
            theme: Name of the theme to apply.
        """
        try:
            app = QApplication.instance()
            if not theme.endswith('.xml'):
                theme = f"{theme}.xml"
            
            invert_secondary = theme.startswith('light_')
            
            # Extract custom QSS file to persistent data folder
            custom_qss_path = self._extract_custom_qss()
            
            if app:
                # Apply theme with custom QSS file if available
                if custom_qss_path and custom_qss_path.exists():
                    apply_stylesheet(
                        app, 
                        theme=theme, 
                        invert_secondary=invert_secondary, 
                        css_file=str(custom_qss_path)
                    )
                    logger.info(f"Theme applied: {theme} with custom QSS: {custom_qss_path}")
                else:
                    apply_stylesheet(app, theme=theme, invert_secondary=invert_secondary, css_file=None)
                    logger.info(f"Theme applied: {theme} (without custom QSS)")
        except Exception as e:
            logger.error(f"Failed to apply theme: {e}")

    @Slot()
    def show_about(self):
        """Show the About dialog."""
        dialog = AboutDialog(self)
        dialog.exec()
        logger.debug("About dialog shown")
    
    @Slot()
    def show_preferences(self):
        """Show the Preferences dialog."""
        dialog = PreferencesDialog(self)
        dialog.close_preferences_dialog.connect(self._on_preferences_dialog_closed)
        dialog.preview_theme_changed.connect(self.apply_theme)
        result = dialog.exec()
        
        if result:
            logger.info("Preferences saved")
            # Settings are automatically saved by the dialog
        else:
            logger.debug("Preferences dialog cancelled")
    
    @Slot()
    def _on_preferences_dialog_closed(self):
        """Handle preferences dialog closed signal."""
        try:
            app = QApplication.instance()
            if app:
                settings = get_settings()
                self.apply_theme(settings.theme)
                logger.info(f"Theme applied: {settings.theme}")
        except Exception as e:
            logger.error(f"Failed to apply theme: {e}")
    
    @Slot()
    def export_selection(self):
        """Export the filtered dataset subset."""
        if not self._dataset:
            QMessageBox.warning(
                self,
                "No Dataset",
                "Please load a BIDS dataset before exporting."
            )
            return
        
        # Use filtered dataset if active, otherwise use full dataset
        export_source = self._filtered_dataset if self._filtered_dataset else self._dataset
        
        # Show export dialog
        dialog = ExportDialog(export_source, self)
        
        if not dialog.exec():
            logger.debug("Export cancelled by user")
            return
        
        # Get export request
        export_request = dialog.get_export_request()
        if not export_request:
            logger.warning("Export request is None")
            return
        
        # Create and configure progress dialog
        progress_dialog = ProgressDialog(self)
        progress_dialog.setWindowTitle("Exporting Dataset")
        
        # Create worker thread
        self._export_worker = ExportWorkerThread(export_request)
        self._export_worker.progress_updated.connect(
            lambda current, total, filepath: self._on_export_progress(progress_dialog, current, total, filepath)
        )
        self._export_worker.export_complete.connect(
            lambda output_path: self._on_export_complete(progress_dialog, output_path)
        )
        self._export_worker.export_error.connect(
            lambda error_msg: self._on_export_error(progress_dialog, error_msg)
        )
        
        # Start export
        self._export_worker.start()
        progress_dialog.exec()
        
        logger.info("Export initiated")
    
    def _on_export_progress(self, progress_dialog: ProgressDialog, current: int, total: int, filepath: str):
        """Handle export progress updates."""
        filename = Path(filepath).name
        message = f"Copying file {current}/{total}:\n{filename}"
        progress_dialog.update_progress(current, total, message)
    
    def _on_export_complete(self, progress_dialog: ProgressDialog, output_path: Path):
        """Handle export completion."""
        progress_dialog.accept()
        
        # Show success message with option to open location
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Export Complete")
        msg_box.setText("Dataset export completed successfully!")
        msg_box.setInformativeText(f"Exported to:\n{output_path}")
        
        open_button = msg_box.addButton("Open Location", QMessageBox.ButtonRole.ActionRole)
        ok_button = msg_box.addButton(QMessageBox.StandardButton.Ok)
        
        msg_box.exec()
        
        # Open location if requested
        if msg_box.clickedButton() == open_button:
            self._open_file_location(output_path)
        
        logger.info(f"Export completed: {output_path}")
    
    def _on_export_error(self, progress_dialog: ProgressDialog, error_msg: str):
        """Handle export error."""
        progress_dialog.reject()
        
        QMessageBox.critical(
            self,
            "Export Error",
            f"An error occurred during export:\n\n{error_msg}"
        )
        
        logger.error(f"Export failed: {error_msg}")
    
    def _open_file_location(self, path: Path):
        """Open file explorer at the given path."""
        if os.name == 'nt':  # Windows
            subprocess.run(['explorer', str(path)])
        elif os.name == 'posix':  # macOS/Linux
            if subprocess.run(['which', 'xdg-open'], capture_output=True).returncode == 0:
                subprocess.run(['xdg-open', str(path)])
            else:
                subprocess.run(['open', str(path)])
    
    @Slot()
    def _show_filter_dialog(self):
        """Show the filter builder dialog."""
        if not self._dataset:
            QMessageBox.warning(
                self,
                "No Dataset",
                "Please load a dataset first before applying filters."
            )
            return
        
        # If in lazy mode, load iEEG data before showing filter dialog
        settings = get_settings()
        if settings.lazy_loading and self._repository:
            # Show progress dialog while loading iEEG data
            progress_dialog = ProgressDialog(self)
            progress_dialog.setWindowTitle("Loading iEEG Metadata")
            progress_dialog.update_progress(0, 100, "Loading channel and electrode data for filtering...")
            progress_dialog.show()
            QApplication.processEvents()
            
            try:
                def progress_callback(current, total, message):
                    progress_dialog.update_progress(current, total, message)
                    QApplication.processEvents()
                
                self._repository.load_ieeg_data_for_all_subjects(progress_callback)
                progress_dialog.close()
            except Exception as e:
                progress_dialog.close()
                logger.error(f"Failed to load iEEG data: {e}", exc_info=True)
                QMessageBox.warning(
                    self,
                    "Warning",
                    f"Failed to load some iEEG metadata:\n{str(e)}\n\nFiltering will continue with available data."
                )
        
        # Show filter builder dialog with last dialog state (not active filter)
        # This ensures dialog state persists even if filter was cleared from main window
        dialog = FilterBuilderDialog(self._dataset, self._last_dialog_filter, self)
        if dialog.exec() == FilterBuilderDialog.DialogCode.Accepted:
            filter_expr = dialog.get_filter_expression()
            # Update last dialog state
            self._last_dialog_filter = filter_expr
            if filter_expr:
                self._apply_filter(filter_expr)
            else:
                # No filter expression means show all subjects
                self._clear_filter()
    
    def _apply_filter(self, filter_expr: LogicalOperation):
        """
        Apply a filter expression to the dataset.
        
        Args:
            filter_expr: The filter expression to apply.
        """
        if not self._dataset:
            return
        
        try:
            # Apply filter to get filtered dataset
            self._filtered_dataset = apply_filter(self._dataset, filter_expr)
            self._active_filter = filter_expr
            
            # Update tree view with gray-out
            self._populate_tree()
            
            # Update status bar
            matching_count = len(self._filtered_dataset.subjects)
            total_count = len(self._dataset.subjects)
            self.statusBar().showMessage(
                f"Filter active: {matching_count} of {total_count} subjects match"
            )
            
            # Enable clear filter button and menu action
            if hasattr(self.ui, 'clearFilterButton'):
                self.ui.clearFilterButton.setEnabled(True)
            if hasattr(self.ui, 'actionClearFilter'):
                self.ui.actionClearFilter.setEnabled(True)
            
            logger.info(f"Filter applied: {matching_count}/{total_count} subjects match")
            
        except Exception as e:
            logger.error(f"Failed to apply filter: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Filter Error",
                f"Failed to apply filter:\n{str(e)}"
            )
    
    def _clear_filter(self):
        """Clear the active filter and show all subjects."""
        self._filtered_dataset = None
        self._active_filter = None
        # Note: We do NOT clear _last_dialog_filter here
        # This preserves dialog state when reopening after clearing
        
        # Update tree view (remove gray-out)
        self._populate_tree()
        
        # Disable clear filter button and menu action
        if hasattr(self.ui, 'clearFilterButton'):
            self.ui.clearFilterButton.setEnabled(False)
        if hasattr(self.ui, 'actionClearFilter'):
            self.ui.actionClearFilter.setEnabled(False)
        
        # Update status bar
        self.statusBar().showMessage("Filter cleared - showing all subjects")
        logger.info("Filter cleared")
    
    def _update_ui(self):
        """Update UI with current dataset/view model state."""
        if not self._dataset or not hasattr(self.ui, 'datasetTreeWidget'):
            return
        
        # Populate the tree with dataset structure
        self._populate_tree()
        
        # Update status bar with statistics
        self._update_status_bar()
        
        # Clear details panel
        if self._details_panel:
            self._details_panel.clear()
        
        logger.debug("UI updated with dataset")
    
    def _populate_tree(self):
        """Populate the tree widget with dataset structure."""
        if not hasattr(self.ui, 'datasetTreeWidget') or not self._dataset or not self._repository:
            return
        
        tree = self.ui.datasetTreeWidget
        tree.clear()
        
        # Create root item for dataset
        dataset_name = self._dataset.dataset_description.get('Name', 'BIDS Dataset')
        root_item = QTreeWidgetItem([dataset_name])
        root_item.setIcon(0, QIcon(":/icons/folder_icon.svg"))
        root_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'dataset', 'data': self._dataset})
        tree.addTopLevelItem(root_item)
        
        # Check if lazy loading is enabled
        settings = get_settings()
        if settings.lazy_loading:
            # For lazy loading, add subject stubs that will load on expansion
            subject_ids = self._repository.get_subject_ids()
            for subject_id in subject_ids:
                self._add_subject_stub_to_tree(root_item, subject_id)
            logger.debug(f"Populated tree with {len(subject_ids)} subject stubs (lazy)")
        else:
            # For eager loading, add all subjects normally
            for subject in self._dataset.subjects:
                self._add_subject_to_tree(root_item, subject)
            logger.debug(f"Populated tree with {len(self._dataset.subjects)} subjects (eager)")
        
        # Add dataset-level files (README, LICENSE, CHANGES) after subjects
        self._add_dataset_files_to_tree(root_item)
        
        # Expand only the root
        root_item.setExpanded(True)
        
        # Connect tree expansion signal for lazy loading
        if settings.lazy_loading:
            tree.itemExpanded.connect(self._on_tree_item_expanded)
    
    def _add_subject_stub_to_tree(self, parent_item: QTreeWidgetItem, subject_id: str):
        """
        Add a subject stub to the tree (for lazy loading).
        
        The subject data will be loaded when the item is expanded.
        
        Args:
            parent_item: Parent tree item.
            subject_id: Subject identifier.
        """
        subject_text = f"sub-{subject_id}"
        subject_item = QTreeWidgetItem([subject_text])
        subject_item.setIcon(0, QIcon(":/icons/person_icon.svg"))
        subject_item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': 'subject_stub', 
            'subject_id': subject_id,
            'loaded': False
        })
        
        # Check if subject matches filter (if active)
        if self._filtered_dataset:
            subject_ids = [s.subject_id for s in self._filtered_dataset.subjects]
            if subject_id not in subject_ids:
                # Gray out non-matching subject
                subject_item.setForeground(0, QBrush(QColor(150, 150, 150)))
                subject_item.setFlags(subject_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        
        parent_item.addChild(subject_item)
        
        # Add a dummy child so the expand arrow appears (only if not grayed out)
        if self._filtered_dataset is None or subject_id in [s.subject_id for s in self._filtered_dataset.subjects]:
            dummy_item = QTreeWidgetItem(["Loading..."])
            subject_item.addChild(dummy_item)
    
    @Slot(QTreeWidgetItem)
    def _on_tree_item_expanded(self, item: QTreeWidgetItem):
        """
        Handle tree item expansion (for lazy loading).
        
        Args:
            item: The tree item that was expanded.
        """
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get('type') != 'subject_stub':
            return
        
        # Check if already loaded
        if data.get('loaded', False):
            return
        
        subject_id = data.get('subject_id')
        if not subject_id or not self._repository:
            return
        
        logger.debug(f"Loading subject on expansion: {subject_id}")
        
        # Load the subject
        subject = self._repository.get_subject(subject_id)
        if subject is None:
            logger.warning(f"Failed to load subject: {subject_id}")
            # Remove dummy child and add error message
            item.takeChildren()
            error_item = QTreeWidgetItem(["Failed to load"])
            item.addChild(error_item)
            return
        
        # Remove dummy children
        item.takeChildren()
        
        # Update item data
        item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': 'subject',
            'data': subject,
            'loaded': True
        })
        
        # Add sessions if present
        if subject.sessions:
            for session in subject.sessions:
                self._add_session_to_tree(item, session)
        else:
            # No sessions - add modality folders directly
            self._add_modality_folders_to_tree(item, subject.files)
        
        logger.debug(f"Subject loaded: {subject_id}")
    
    def _add_subject_to_tree(self, parent_item: QTreeWidgetItem, subject: BIDSSubject):
        """Add a subject and its contents to the tree."""
        # Create subject item
        subject_text = f"sub-{subject.subject_id}"
        
        subject_item = QTreeWidgetItem([subject_text])
        subject_item.setIcon(0, QIcon(":/icons/person_icon.svg"))
        subject_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'subject', 'data': subject})
        
        # Check if subject matches filter (if active)
        is_filtered_out = False
        if self._filtered_dataset:
            subject_ids = [s.subject_id for s in self._filtered_dataset.subjects]
            if subject.subject_id not in subject_ids:
                # Gray out non-matching subject
                subject_item.setForeground(0, QBrush(QColor(150, 150, 150)))
                subject_item.setFlags(subject_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                is_filtered_out = True
        
        parent_item.addChild(subject_item)
        
        # Don't add children if filtered out
        if is_filtered_out:
            return
        
        # Add sessions if present
        if subject.sessions:
            for session in subject.sessions:
                self._add_session_to_tree(subject_item, session)
        else:
            # No sessions - add modality folders directly
            self._add_modality_folders_to_tree(subject_item, subject.files)
        
        # Add derivatives section if present
        if subject.derivatives:
            derivatives_item = QTreeWidgetItem(["derivatives"])
            derivatives_item.setIcon(0, QIcon(":/icons/analytics_icon.svg"))
            derivatives_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'derivatives_folder', 
                'data': subject
            })
            subject_item.addChild(derivatives_item)
            
            for derivative in subject.derivatives:
                self._add_derivative_to_tree(derivatives_item, derivative, subject.subject_id)
    
    def _add_session_to_tree(self, parent_item: QTreeWidgetItem, session: BIDSSession):
        """Add a session and its contents to the tree."""
        session_text = f"ses-{session.session_id}"
        session_item = QTreeWidgetItem([session_text])
        session_item.setIcon(0, QIcon(":/icons/folder_open_icon.svg"))
        session_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'session', 'data': session})
        parent_item.addChild(session_item)
        
        # Add modality folders
        self._add_modality_folders_to_tree(session_item, session.files)
    
    def _add_modality_folders_to_tree(self, parent_item: QTreeWidgetItem, files: list[BIDSFile]):
        """Add modality folders and their files to the tree."""
        # Group files by modality
        modalities = {}
        for file in files:
            modality = file.modality or 'unknown'
            if modality not in modalities:
                modalities[modality] = []
            modalities[modality].append(file)
        
        # Add modality folders
        for modality, modality_files in sorted(modalities.items()):
            modality_text = f"{modality}"
            modality_item = QTreeWidgetItem([modality_text])
            modality_item.setIcon(0, QIcon(":/icons/folder_open_icon.svg"))
            modality_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'modality', 
                'data': {'modality': modality, 'files': modality_files}
            })
            parent_item.addChild(modality_item)
            
            # Add files
            for file in sorted(modality_files, key=lambda f: f.path.name):
                self._add_file_to_tree(modality_item, file)
    
    def _add_file_to_tree(self, parent_item: QTreeWidgetItem, file: BIDSFile):
        """Add a file to the tree."""
        file_text = f"{file.path.name}"
        file_item = QTreeWidgetItem([file_text])
        file_item.setIcon(0, QIcon(":/icons/file_icon.svg"))
        file_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'file', 'data': file})
        parent_item.addChild(file_item)
    
    def _add_derivative_to_tree(self, parent_item: QTreeWidgetItem, derivative, subject_id: str):
        """
        Add a derivative pipeline to the tree.
        
        Args:
            parent_item: The derivatives folder item.
            derivative: The BIDSDerivative to add.
            subject_id: The subject ID (for context).
        """
        pipeline_text = f"{derivative.pipeline_name}"
        pipeline_item = QTreeWidgetItem([pipeline_text])
        pipeline_item.setIcon(0, QIcon(":/icons/package_icon.svg"))
        pipeline_item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': 'derivative',
            'data': derivative,
            'subject_id': subject_id
        })
        parent_item.addChild(pipeline_item)
        
        # Add sessions if present (mirroring subject structure)
        if derivative.sessions:
            for session in derivative.sessions:
                self._add_derivative_session_to_tree(pipeline_item, session)
        else:
            # No sessions - add modality folders directly
            self._add_modality_folders_to_tree(pipeline_item, derivative.files)
    
    def _add_derivative_session_to_tree(self, parent_item: QTreeWidgetItem, session: BIDSSession):
        """
        Add a derivative session to the tree.
        
        Uses same structure as regular sessions.
        
        Args:
            parent_item: The pipeline item.
            session: The BIDSSession to add.
        """
        # Get pipeline name from parent item
        parent_data = parent_item.data(0, Qt.ItemDataRole.UserRole)
        pipeline_name = parent_data.get('data').pipeline_name if parent_data and 'data' in parent_data else 'unknown'
        
        session_text = f"ses-{session.session_id}"
        session_item = QTreeWidgetItem([session_text])
        session_item.setIcon(0, QIcon(":/icons/folder_open_icon.svg"))
        session_item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': 'derivative_session',
            'data': {'session': session, 'pipeline_name': pipeline_name}
        })
        parent_item.addChild(session_item)
        
        # Add modality folders
        self._add_modality_folders_to_tree(session_item, session.files)
    
    def _add_dataset_files_to_tree(self, parent_item: QTreeWidgetItem):
        """
        Add dataset-level files (README, LICENSE, CHANGES) to the tree.
        
        Args:
            parent_item: The dataset root item to add files to.
        """
        if not self._dataset:
            return
        
        # Display dataset-level files that were loaded by the BidsLoader
        for dataset_file in self._dataset.dataset_files:
            self._add_file_to_tree(parent_item, dataset_file)
    
    def _update_status_bar(self):
        """Update the status bar with dataset statistics."""
        if not self._dataset or not hasattr(self.ui, 'statusbar') or not self._repository:
            return
        
        settings = get_settings()
        
        if settings.lazy_loading:
            # For lazy loading, show total subject count from filesystem
            subject_ids = self._repository.get_subject_ids()
            num_subjects = len(subject_ids)
            status_text = f"Subjects: {num_subjects}"
        else:
            # For eager loading, show full statistics
            num_subjects = len(self._dataset.subjects)
            
            # Count sessions
            num_sessions = sum(len(s.sessions) for s in self._dataset.subjects)
            
            # Count files
            total_files = 0
            for subject in self._dataset.subjects:
                total_files += len(subject.files)
                for session in subject.sessions:
                    total_files += len(session.files)
            
            status_text = f"Subjects: {num_subjects} | Sessions: {num_sessions} | Files: {total_files}"
        
        self.ui.statusbar.showMessage(status_text)
    
    @Slot()
    def _on_tree_selection_changed(self):
        """Handle tree selection changes and update details panel."""
        if not hasattr(self.ui, 'datasetTreeWidget') or not self._details_panel:
            return
        
        tree = self.ui.datasetTreeWidget
        selected_items = tree.selectedItems()
        
        if not selected_items:
            self._details_panel.clear()
            return
        
        item = selected_items[0]
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data:
            self._details_panel.clear()
            return
        
        item_type = item_data.get('type')
        data = item_data.get('data')
        
        # Display different content based on item type
        if item_type == 'dataset':
            self._display_dataset_details(data)
        elif item_type == 'subject':
            self._display_subject_details(data)
        elif item_type == 'session':
            self._display_session_details(data)
        elif item_type == 'modality':
            self._display_modality_details(data)
        elif item_type == 'file':
            self._display_file_details(data)
        elif item_type == 'derivatives_folder':
            self._display_derivatives_folder_details(data)
        elif item_type == 'derivative':
            self._display_derivative_details(data)
        elif item_type == 'derivative_session':
            self._display_derivative_session_details(data)
        else:
            self._details_panel.clear()
    
    @Slot(QTreeWidgetItem, int)
    def _on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """
        Handle double-click on tree items.
        
        Opens files or folders based on their type:
        - Folders: Open in OS file explorer
        - JSON files: Open in custom JSON viewer
        - CSV/TSV files: Open in custom table viewer
        - Markdown/text files: Open in custom text viewer
        - Other files: Open with default program
        """
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not item_data:
            return
        
        item_type = item_data.get('type')
        data = item_data.get('data')
        
        if item_type == 'file':
            self._open_file(data)
        elif item_type in ['dataset', 'subject', 'session', 'modality', 'derivatives_folder', 'derivative', 'derivative_session']:
            self._open_folder(item_type, data)
    
    def _display_dataset_details(self, dataset: BIDSDataset):
        """Display dataset information in details panel."""
        if not self._details_panel:
            return
        
        desc = dataset.dataset_description
        
        # Count statistics
        num_subjects = len(dataset.subjects)
        num_sessions = sum(len(s.sessions) for s in dataset.subjects)
        total_files = sum(len(s.files) for s in dataset.subjects) + sum(
            len(ses.files) for s in dataset.subjects for ses in s.sessions
        )
        
        sections = [
            {
                'title': 'Dataset Information',
                'items': [
                    {'key': 'Name', 'value': desc.get('Name', 'N/A')},
                    {'key': 'BIDS Version', 'value': desc.get('BIDSVersion', 'N/A')},
                    {'key': 'Dataset Type', 'value': desc.get('DatasetType', 'N/A')},
                    {'key': 'Authors', 'value': ', '.join(desc.get('Authors', [])) or 'N/A'},
                    {'key': 'License', 'value': desc.get('License', 'N/A')},
                ]
            },
            {
                'title': 'Statistics',
                'items': [
                    {'key': 'Subjects', 'value': num_subjects},
                    {'key': 'Sessions', 'value': num_sessions},
                    {'key': 'Total Files', 'value': total_files},
                ]
            }
        ]
        
        self._details_panel.set_content(sections)
    
    def _display_subject_details(self, subject: BIDSSubject):
        """Display subject information in details panel."""
        if not self._details_panel:
            return
        
        # Count files
        num_sessions = len(subject.sessions)
        total_files = len(subject.files) + sum(len(ses.files) for ses in subject.sessions)
        
        # Build subject items with metadata
        subject_items = []
        
        # Add participant metadata if available
        if subject.metadata:
            for key, value in subject.metadata.items():
                subject_items.append({'key': key, 'value': value})
        
        sections = [
            {
                'title': f'Subject: sub-{subject.subject_id}',
                'items': subject_items
            },
            {
                'title': 'Statistics',
                'items': [
                    {'key': 'Sessions', 'value': num_sessions},
                    {'key': 'Total Files', 'value': total_files},
                ]
            }
        ]
        
        self._details_panel.set_content(sections)
    
    def _display_session_details(self, session: BIDSSession):
        """Display session information in details panel."""
        if not self._details_panel:
            return
        
        # Count modalities
        modalities = Counter(f.modality for f in session.files if f.modality)
        
        sections = [
            {
                'title': f'Session: ses-{session.session_id}',
                'items': [
                    {'key': modality, 'value': f'{count} file{"s" if count != 1 else ""}'}
                    for modality, count in sorted(modalities.items())
                ]
            }
        ]
        
        self._details_panel.set_content(sections)
    
    def _display_modality_details(self, data: dict):
        """Display modality information in details panel."""
        if not self._details_panel:
            return
        
        modality = data.get('modality', 'unknown')
        files = data.get('files', [])
        
        # Count by suffix
        suffixes = Counter(f.suffix for f in files if f.suffix)
        
        # Count by task (if applicable)
        tasks = Counter(f.entities.get('task') for f in files if 'task' in f.entities)
        
        sections = [
            {
                'title': f'Modality: {modality}',
                'items': [
                    {'key': 'Total Files', 'value': len(files)}
                ]
            },
            {
                'title': 'Files by Type',
                'items': [
                    {'key': suffix, 'value': f'{count} file{"s" if count != 1 else ""}'}
                    for suffix, count in sorted(suffixes.items())
                ]
            }
        ]
        
        # Add task section if tasks exist
        if tasks:
            sections.append({
                'title': 'Files by Task',
                'items': [
                    {'key': f'task-{task}', 'value': f'{count} file{"s" if count != 1 else ""}'}
                    for task, count in sorted(tasks.items())
                ]
            })
        
        self._details_panel.set_content(sections)
    
    def _display_file_details(self, file: BIDSFile):
        """Display file information in details panel."""
        if not self._details_panel:
            return
        
        # Load metadata if not already loaded (lazy loading support)
        # Do this BEFORE building the sections to avoid double UI update
        if file.metadata is None:
            file.load_metadata()
        
        # Get file size
        try:
            file_size = file.path.stat().st_size
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            elif file_size < 1024 * 1024 * 1024:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{file_size / (1024 * 1024 * 1024):.2f} GB"
        except Exception:
            size_str = "Unknown"
        
        sections = [
            {
                'title': 'File Details',
                'items': [
                    {'key': 'Filename', 'value': file.path.name},
                    {'key': 'Suffix', 'value': file.suffix or 'N/A'},
                    {'key': 'Extension', 'value': file.extension or 'N/A'},
                    {'key': 'Modality', 'value': file.modality or 'N/A'},
                ]
            }
        ]
        
        # Add entities if present
        if file.entities:
            entity_items = [
                {'key': key, 'value': value}
                for key, value in file.entities.items()
            ]
            sections.append({
                'title': 'Entities',
                'items': entity_items
            })
        
        # Add file info
        sections.append({
            'title': 'File Info',
            'items': [
                {'key': 'Path', 'value': str(file.path)},
                {'key': 'Size', 'value': size_str},
            ]
        })
        
        # Add metadata if present (already loaded at the beginning of the function)
        if file.metadata:
            metadata_items = []
            for key, value in file.metadata.items():
                # Convert value to string, handle different types
                if isinstance(value, (list, dict)):
                    value_str = str(value)
                    # Truncate long values
                    if len(value_str) > 100:
                        value_str = value_str[:97] + '...'
                else:
                    value_str = str(value)
                metadata_items.append({'key': key, 'value': value_str})
            
            sections.append({
                'title': 'Metadata (from JSON sidecar)',
                'items': metadata_items
            })
        
        self._details_panel.set_content(sections)
    
    def _display_derivatives_folder_details(self, subject: BIDSSubject):
        """Display derivatives folder information in details panel."""
        if not self._details_panel:
            return
        
        # Count derivatives and files
        num_derivatives = len(subject.derivatives)
        total_files = sum(
            len(deriv.files) + sum(len(ses.files) for ses in deriv.sessions)
            for deriv in subject.derivatives
        )
        
        # List derivative pipelines
        pipeline_items = [
            {'key': deriv.pipeline_name, 'value': f'{len(deriv.files) + sum(len(ses.files) for ses in deriv.sessions)} file{"s" if (len(deriv.files) + sum(len(ses.files) for ses in deriv.sessions)) != 1 else ""}'}
            for deriv in subject.derivatives
        ]
        
        sections = [
            {
                'title': f'Derivatives for sub-{subject.subject_id}',
                'items': [
                    {'key': 'Pipelines', 'value': num_derivatives},
                    {'key': 'Total Files', 'value': total_files},
                ]
            }
        ]
        
        if pipeline_items:
            sections.append({
                'title': 'Pipelines',
                'items': pipeline_items
            })
        
        self._details_panel.set_content(sections)
    
    def _display_derivative_details(self, derivative: BIDSDerivative):
        """Display derivative pipeline information in details panel."""
        if not self._details_panel:
            return
        
        # Count statistics
        num_sessions = len(derivative.sessions)
        total_files = len(derivative.files) + sum(len(ses.files) for ses in derivative.sessions)
        
        # Build derivative items
        derivative_items = [
            {'key': 'Pipeline Name', 'value': derivative.pipeline_name},
            {'key': 'Sessions', 'value': num_sessions},
            {'key': 'Total Files', 'value': total_files},
        ]
        
        # Add description if available
        if derivative.pipeline_description:
            desc = derivative.pipeline_description
            if 'Name' in desc:
                derivative_items.append({'key': 'Pipeline Full Name', 'value': desc['Name']})
            if 'PipelineDescription' in desc:
                derivative_items.append({'key': 'Description', 'value': desc['PipelineDescription'].get('Name', 'N/A')})
            if 'GeneratedBy' in desc:
                generated_by = desc['GeneratedBy']
                if isinstance(generated_by, list) and generated_by:
                    gen = generated_by[0]
                    if 'Name' in gen:
                        derivative_items.append({'key': 'Generated By', 'value': gen['Name']})
                    if 'Version' in gen:
                        derivative_items.append({'key': 'Version', 'value': gen['Version']})
        
        sections = [
            {
                'title': f'Derivative: {derivative.pipeline_name}',
                'items': derivative_items
            }
        ]
        
        self._details_panel.set_content(sections)
    
    def _display_derivative_session_details(self, data: dict):
        """Display derivative session information in details panel."""
        if not self._details_panel:
            return
        
        session = data.get('session')
        pipeline_name = data.get('pipeline_name', 'unknown')
        
        if not session:
            self._details_panel.clear()
            return
        
        # Count modalities
        modalities = Counter(f.modality for f in session.files if f.modality)
        
        sections = [
            {
                'title': f'Derivative Session: {pipeline_name}/ses-{session.session_id}',
                'items': [
                    {'key': modality, 'value': f'{count} file{"s" if count != 1 else ""}'}
                    for modality, count in sorted(modalities.items())
                ]
            }
        ]
        
        self._details_panel.set_content(sections)
    
    def _open_file(self, file: BIDSFile):
        """
        Open a file based on its type.
        
        Args:
            file: The BIDS file to open.
        """
        file_path = file.path
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            QMessageBox.warning(
                self,
                "File Not Found",
                f"The file does not exist:\n{file_path}"
            )
            return
        
        # Get file extension
        extension = file_path.suffix.lower()
        
        try:
            # JSON files - open in custom JSON viewer
            if extension == '.json':
                dialog = JsonViewerDialog(file_path, self)
                dialog.exec()
                logger.debug(f"Opened JSON file: {file_path.name}")
            
            # CSV/TSV files - open in custom table viewer
            elif extension in ['.csv', '.tsv']:
                dialog = TableViewerDialog(file_path, self)
                dialog.exec()
                logger.debug(f"Opened table file: {file_path.name}")
            
            # Markdown and text files - open in custom text viewer
            # Also handle files without extension (README, CHANGES, LICENSE, etc.)
            elif extension in ['.md', '.markdown', '.txt', '.rst'] or extension == '' or file_path.name.upper() in ['README', 'CHANGES', 'LICENSE', 'AUTHORS']:
                dialog = TextViewerDialog(file_path, self)
                dialog.exec()
                logger.debug(f"Opened text file: {file_path.name}")
            
            # Other files - open with default program
            else:
                self._open_with_default_program(file_path)
                
        except Exception as e:
            logger.error(f"Failed to open file: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open file:\n{str(e)}"
            )
    
    def _open_folder(self, item_type: str, data):
        """
        Open a folder in the OS file explorer.
        
        Args:
            item_type: Type of item (dataset, subject, session, modality, derivatives_folder, derivative, derivative_session).
            data: Data associated with the item.
        """
        # Determine the folder path based on item type
        folder_path = None
        
        if item_type == 'dataset' and isinstance(data, BIDSDataset):
            folder_path = data.root_path
        elif item_type == 'subject' and isinstance(data, BIDSSubject):
            # Construct subject path from dataset root
            if self._dataset:
                folder_path = self._dataset.root_path / f"sub-{data.subject_id}"
        elif item_type == 'derivatives_folder' and isinstance(data, BIDSSubject):
            # Open derivatives folder at dataset root
            if self._dataset:
                folder_path = self._dataset.root_path / "derivatives"
        elif item_type == 'derivative' and isinstance(data, BIDSDerivative):
            # Open derivative subject folder - get path from files
            if data.files:
                # Get path from first file and navigate to subject directory
                first_file = data.files[0].path
                # Navigate up to find sub-XX directory
                current = first_file.parent
                while current and self._dataset and current != self._dataset.root_path:
                    if 'sub-' in current.name and current.name.startswith('sub-'):
                        folder_path = current
                        break
                    current = current.parent
            elif data.sessions:
                # Get path from first session's files
                for session in data.sessions:
                    if session.files:
                        first_file = session.files[0].path
                        # Navigate up to find sub-XX directory
                        current = first_file.parent
                        while current and self._dataset and current != self._dataset.root_path:
                            if 'sub-' in current.name and current.name.startswith('sub-'):
                                folder_path = current
                                break
                            current = current.parent
                        if folder_path:
                            break
        elif item_type == 'derivative_session' and isinstance(data, dict):
            # Open derivative session folder - get path from files
            session = data.get('session')
            if session and session.files:
                # Get parent directory from first file (go up to session folder)
                first_file_path = session.files[0].path
                # Navigate up to find ses-XX directory
                current = first_file_path.parent
                while current and self._dataset and current != self._dataset.root_path:
                    if current.name == f"ses-{session.session_id}":
                        folder_path = current
                        break
                    current = current.parent
        elif item_type == 'session' and isinstance(data, BIDSSession):
            # Need to find parent subject to construct path
            # This is a bit tricky - we need to get the path from a file if available
            if data.files:
                # Get parent directory from first file (go up to session folder)
                # Files are in modality folders, so we need to go up one more level
                first_file_path = data.files[0].path
                # Path structure: .../sub-XX/ses-YY/modality/file.nii.gz
                # We want: .../sub-XX/ses-YY/
                folder_path = first_file_path.parent.parent
        elif item_type == 'modality' and isinstance(data, dict):
            # For modality folders, get path from first file
            files = data.get('files', [])
            if files:
                # Get parent directory of first file (the modality folder)
                folder_path = files[0].path.parent
        
        if not folder_path or not folder_path.exists():
            logger.warning(f"Folder not found for {item_type}")
            QMessageBox.warning(
                self,
                "Folder Not Found",
                f"Cannot open folder for {item_type}"
            )
            return
        
        try:
            # Open folder in OS file explorer
            if os.name == 'nt':  # Windows
                os.startfile(folder_path)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.run(['xdg-open', str(folder_path)])
            
            logger.debug(f"Opened folder: {folder_path}")
            
        except Exception as e:
            logger.error(f"Failed to open folder: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open folder:\n{str(e)}"
            )
    
    def _open_with_default_program(self, file_path: Path):
        """
        Open a file with its default system program.
        
        Args:
            file_path: Path to the file to open.
        """
        try:
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.run(['xdg-open', str(file_path)])
            
            logger.debug(f"Opened with default program: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Failed to open with default program: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open file with default program:\n{str(e)}"
            )
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Save window geometry to settings
        settings_manager = get_settings_manager()
        settings_manager.update(
            window_width=self.width(),
            window_height=self.height()
        )
        settings_manager.save()
        
        logger.info(f"Main window closing (size: {self.width()}x{self.height()})")
        event.accept()
