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
from PySide6.QtGui import QAction
from PySide6.QtCore import Slot, Qt
from numpy import invert
from qt_material import apply_stylesheet

from bidsio.infrastructure.logging_config import get_logger
from bidsio.config.settings import get_settings_manager, get_settings
from bidsio.core.repository import BidsRepository
from bidsio.core.models import BIDSDataset, BIDSSubject, BIDSSession, BIDSFile, FilterCriteria
from bidsio.ui.view_models import DatasetViewModel
from bidsio.ui.about_dialog import AboutDialog
from bidsio.ui.preferences_dialog import PreferencesDialog
from bidsio.ui.json_viewer_dialog import JsonViewerDialog
from bidsio.ui.table_viewer_dialog import TableViewerDialog
from bidsio.ui.text_viewer_dialog import TextViewerDialog
from bidsio.ui.progress_dialog import ProgressDialog
from bidsio.ui.workers import DatasetLoaderThread
from bidsio.ui.widgets.details_panel import DetailsPanel
from bidsio.ui.widgets.delegates import CompactDelegate
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
        self._details_panel: Optional[DetailsPanel] = None
        
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
        
        # Connect tree widget selection
        if hasattr(self.ui, 'datasetTreeWidget'):
            self.ui.datasetTreeWidget.itemSelectionChanged.connect(self._on_tree_selection_changed)
            self.ui.datasetTreeWidget.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
            self.ui.datasetTreeWidget.setItemDelegate(CompactDelegate(row_height=24, parent=self))
            self.ui.datasetTreeWidget.setUniformRowHeights(True)
        
        # TODO: connect toolbar buttons
        # TODO: connect filter controls
        # TODO: connect export action
        
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
        
        # Show success message
        num_subjects = len(dataset.subjects)
        dataset_name = dataset.dataset_description.get('Name', 'Unknown')
        logger.info(f"Dataset loaded successfully: {dataset_name}, {num_subjects} subjects")
    
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
            
            if app:
                apply_stylesheet(app, theme=theme, invert_secondary=invert_secondary)
                logger.info(f"Theme applied: {theme}")
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
        root_item = QTreeWidgetItem([f"📁 {dataset_name}"])
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
        subject_text = f"🧍 sub-{subject_id}"
        subject_item = QTreeWidgetItem([subject_text])
        subject_item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': 'subject_stub', 
            'subject_id': subject_id,
            'loaded': False
        })
        parent_item.addChild(subject_item)
        
        # Add a dummy child so the expand arrow appears
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
        subject_text = f"🧍 sub-{subject.subject_id}"
        
        subject_item = QTreeWidgetItem([subject_text])
        subject_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'subject', 'data': subject})
        parent_item.addChild(subject_item)
        
        # Add sessions if present
        if subject.sessions:
            for session in subject.sessions:
                self._add_session_to_tree(subject_item, session)
        else:
            # No sessions - add modality folders directly
            self._add_modality_folders_to_tree(subject_item, subject.files)
    
    def _add_session_to_tree(self, parent_item: QTreeWidgetItem, session: BIDSSession):
        """Add a session and its contents to the tree."""
        session_text = f"📂 ses-{session.session_id}"
        session_item = QTreeWidgetItem([session_text])
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
            modality_text = f"📂 {modality}"
            modality_item = QTreeWidgetItem([modality_text])
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
        file_text = f"📄 {file.path.name}"
        file_item = QTreeWidgetItem([file_text])
        file_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'file', 'data': file})
        parent_item.addChild(file_item)
    
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
        elif item_type in ['dataset', 'subject', 'session', 'modality']:
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
        
        # Add metadata if present
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
            item_type: Type of item (dataset, subject, session, modality).
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
        
        # TODO: prompt to save any unsaved work
        # TODO: cleanup resources
        
        logger.info(f"Main window closing (size: {self.width()}x{self.height()})")
        event.accept()


# TODO: create separate dialog classes for:
# - Export configuration dialog
# - Filter configuration dialog
# - Dataset information dialog
# - About dialog
