"""
Export Dialog.

This dialog allows users to configure and execute dataset exports.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QPushButton, QMessageBox
from PySide6.QtCore import Qt, Slot, QTimer

from bidsio.infrastructure.logging_config import get_logger
from bidsio.core.models import BIDSDataset, ExportRequest, ExportStats, SelectedEntities
from bidsio.core.export import calculate_export_stats
from bidsio.core.entity_config import get_entity_full_name
from bidsio.ui.entity_selector_dialog import EntitySelectorDialog
from bidsio.ui.forms.export_dialog_ui import Ui_ExportDialog


logger = get_logger(__name__)

# Toggle for real-time stats calculation (set to False if performance issues)
ENABLE_REALTIME_STATS = True


class ExportDialog(QDialog):
    """
    Dialog for configuring dataset export.
    
    Displays dynamic entity selectors based on dataset content and
    calculates export statistics in real-time.
    """
    
    def __init__(self, dataset: BIDSDataset, parent=None):
        """
        Initialize the export dialog.
        
        Args:
            dataset: The BIDS dataset to export from.
            parent: Parent widget.
        """
        super().__init__(parent)
        
        self._dataset = dataset
        self._selected_entities: dict[str, list[str]] = {}
        self._selected_pipelines: list[str] = []
        self._entity_buttons: dict[str, tuple[QPushButton, QLabel]] = {}
        
        # Timer for debounced stats calculation
        self._stats_timer = QTimer()
        self._stats_timer.setSingleShot(True)
        self._stats_timer.setInterval(500)  # 500ms debounce
        self._stats_timer.timeout.connect(self._calculate_stats)
        
        self._setup_ui()
        self._connect_signals()
        self._populate_entities()
        self._update_stats()
        
        logger.debug(f"ExportDialog initialized for dataset: {dataset.root_path}")
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.ui = Ui_ExportDialog()
        self.ui.setupUi(self)
        
        # Add Export button to button box
        self._export_button = self.ui.buttonBox.addButton("Export", self.ui.buttonBox.ButtonRole.AcceptRole)
        self._export_button.setEnabled(False)  # Disabled until stats calculated
        self._export_button.clicked.connect(self.accept)
    
    def _connect_signals(self):
        """Connect UI signals to slots."""
        self.ui.browseButton.clicked.connect(self._browse_destination)
        self.ui.pipelinesSelectButton.clicked.connect(self._select_pipelines)
        self.ui.destinationLineEdit.textChanged.connect(self._validate_inputs)
    
    def _populate_entities(self):
        """Populate entity selectors dynamically based on dataset content."""
        # Get all entities present in the dataset
        entities_data = self._dataset.get_all_entities()
        
        if not entities_data:
            logger.warning("No entities found in dataset")
            return
        
        # Create a selector row for each entity
        for entity_code, entity_values in entities_data.items():
            entity_full_name = get_entity_full_name(entity_code)
            
            # Create horizontal layout for this entity
            row_layout = QHBoxLayout()
            
            # Label
            label = QLabel(f"{entity_full_name}:")
            label.setMinimumWidth(120)
            row_layout.addWidget(label)
            
            # Select button
            select_button = QPushButton("Select...")
            select_button.clicked.connect(lambda checked=False, code=entity_code: self._select_entity(code))
            row_layout.addWidget(select_button)
            
            # Count label
            count_label = QLabel(f"({len(entity_values)} selected)")
            count_label.setMinimumWidth(120)
            row_layout.addWidget(count_label)
            
            # Stretch
            row_layout.addStretch()
            
            # Add to entities layout
            self.ui.entitiesLayout.addLayout(row_layout)
            
            # Store references
            self._entity_buttons[entity_code] = (select_button, count_label)
            
            # Initialize selection (all selected by default)
            self._selected_entities[entity_code] = entity_values.copy()
        
        # Get derivative pipelines
        pipelines = self._dataset.get_all_derivative_pipelines()
        if pipelines:
            self._selected_pipelines = pipelines.copy()  # All selected by default
            self.ui.pipelinesCountLabel.setText(f"({len(pipelines)} selected)")
        else:
            # Hide derivatives group box if no derivatives present
            self.ui.derivativesGroupBox.setVisible(False)
        
        logger.debug(f"Populated {len(entities_data)} entity selectors")
    
    @Slot()
    def _browse_destination(self):
        """Open directory browser for destination selection."""
        current_path = self.ui.destinationLineEdit.text()
        start_dir = current_path if current_path else str(Path.home())
        
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Export Destination",
            start_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            self.ui.destinationLineEdit.setText(directory)
    
    @Slot(str)
    def _select_entity(self, entity_code: str):
        """
        Open entity selector dialog for a specific entity.
        
        Args:
            entity_code: The entity code to select values for.
        """
        entity_full_name = get_entity_full_name(entity_code)
        all_values = self._dataset.get_all_entity_values(entity_code)
        current_selection = self._selected_entities.get(entity_code, all_values)
        
        dialog = EntitySelectorDialog(
            entity_name=entity_full_name,
            entity_values=all_values,
            initial_selection=current_selection,
            parent=self
        )
        
        if dialog.exec():
            selected = dialog.get_selected_values()
            self._selected_entities[entity_code] = selected
            
            # Update count label
            if entity_code in self._entity_buttons:
                _, count_label = self._entity_buttons[entity_code]
                count_label.setText(f"({len(selected)} selected)")
            
            # Update stats (always, for any entity change)
            if ENABLE_REALTIME_STATS:
                self._schedule_stats_update()
    
    @Slot()
    def _select_pipelines(self):
        """Open entity selector dialog for derivative pipelines."""
        pipelines = self._dataset.get_all_derivative_pipelines()
        
        if not pipelines:
            return
        
        dialog = EntitySelectorDialog(
            entity_name="Pipelines",
            entity_values=pipelines,
            initial_selection=self._selected_pipelines,
            parent=self
        )
        
        if dialog.exec():
            self._selected_pipelines = dialog.get_selected_values()
            self.ui.pipelinesCountLabel.setText(f"({len(self._selected_pipelines)} selected)")
            self._schedule_stats_update()
    
    def _schedule_stats_update(self):
        """Schedule stats update with debouncing."""
        if ENABLE_REALTIME_STATS:
            self._stats_timer.start()
    
    @Slot()
    def _calculate_stats(self):
        """Calculate and display export statistics."""
        self.ui.calculatingLabel.setText("Calculating...")
        
        try:
            selected_entities = SelectedEntities(
                entities=self._selected_entities.copy(),
                derivative_pipelines=self._selected_pipelines.copy()
            )
            
            stats = calculate_export_stats(self._dataset, selected_entities)
            
            self.ui.fileCountLabel.setText(f"Files to export: {stats.file_count}")
            self.ui.sizeLabel.setText(f"Estimated size: {stats.get_size_string()}")
            self.ui.calculatingLabel.setText("")
            
            # Enable/disable export button based on file count
            self._validate_inputs()
            
        except Exception as e:
            logger.error(f"Error calculating stats: {e}")
            self.ui.calculatingLabel.setText("Error calculating statistics")
    
    def _update_stats(self):
        """Initial stats update."""
        if ENABLE_REALTIME_STATS:
            self._calculate_stats()
        else:
            self.ui.fileCountLabel.setText("Files to export: (stats disabled)")
            self.ui.sizeLabel.setText("Estimated size: (stats disabled)")
            self._validate_inputs()
    
    @Slot()
    def _validate_inputs(self):
        """Validate inputs and enable/disable Export button."""
        destination = self.ui.destinationLineEdit.text().strip()
        has_destination = bool(destination)
        
        # Check if any files would be exported
        has_selection = any(len(vals) > 0 for vals in self._selected_entities.values())
        
        # Enable export button if valid
        self._export_button.setEnabled(has_destination and has_selection)
    
    def _is_bids_dataset_present(self, path: Path) -> bool:
        """
        Check if a BIDS dataset is present at the given path.
        
        Args:
            path: Path to check.
            
        Returns:
            True if BIDS dataset indicators are found, False otherwise.
        """
        # Check for common BIDS dataset indicators
        dataset_description = path / 'dataset_description.json'
        has_subjects = any(item.name.startswith('sub-') and item.is_dir() for item in path.iterdir() if item.is_dir())
        participants_file = path / 'participants.tsv'
        
        # Consider it a BIDS dataset if it has dataset_description.json or subject folders
        return dataset_description.exists() or has_subjects or participants_file.exists()
    
    def get_export_request(self) -> Optional[ExportRequest]:
        """
        Get the configured export request.
        
        Returns:
            ExportRequest if configuration is valid, None otherwise.
        """
        destination = self.ui.destinationLineEdit.text().strip()
        
        if not destination:
            return None
        
        output_path = Path(destination)
        
        # Check if destination contains a BIDS dataset
        overwrite = False
        if output_path.exists() and self._is_bids_dataset_present(output_path):
            reply = QMessageBox.question(
                self,
                "BIDS Dataset Exists",
                f"A BIDS dataset already exists at:\n{output_path}\n\n"
                "Existing files will be overwritten if they match exported files.\n"
                "Other files will be kept.\n\n"
                "Do you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return None
            
            overwrite = True
        
        selected_entities = SelectedEntities(
            entities=self._selected_entities.copy(),
            derivative_pipelines=self._selected_pipelines.copy()
        )
        
        return ExportRequest(
            source_dataset=self._dataset,
            selected_entities=selected_entities,
            output_path=output_path,
            overwrite=overwrite
        )
