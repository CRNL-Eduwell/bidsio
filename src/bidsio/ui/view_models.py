"""
View models for presenting data in the UI.

View models bridge the gap between domain models and UI components,
providing data in formats suitable for display.
"""

from typing import Any
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex

from bidsio.core.models import BIDSDataset, BIDSSubject, BIDSSession
from bidsio.infrastructure.logging_config import get_logger


logger = get_logger(__name__)


class DatasetViewModel:
    """
    View model for a BIDS dataset.
    
    Provides high-level access to dataset information for UI display.
    """
    
    def __init__(self, dataset: BIDSDataset):
        """
        Initialize the view model with a dataset.
        
        Args:
            dataset: The BIDS dataset to present.
        """
        self.dataset = dataset
        
        # TODO: pre-compute summary statistics
        # TODO: create indexes for efficient querying
    
    def get_subject_count(self) -> int:
        """Get the number of subjects in the dataset."""
        return len(self.dataset.subjects)
    
    def get_session_count(self) -> int:
        """Get the total number of sessions across all subjects."""
        # TODO: implement counting
        return 0
    
    def get_file_count(self) -> int:
        """Get the total number of files in the dataset."""
        # TODO: implement counting by traversing dataset
        return 0
    
    def get_modalities(self) -> list[str]:
        """Get list of all modalities in the dataset."""
        # TODO: collect unique modalities
        return []
    
    def get_tasks(self) -> list[str]:
        """Get list of all tasks in the dataset."""
        # TODO: collect unique tasks
        return []


class SubjectTableModel(QAbstractTableModel):
    """
    Table model for displaying subjects in a QTableView.
    
    Columns: Subject ID, Session Count, File Count
    """
    
    def __init__(self, subjects: list[BIDSSubject], parent=None):
        """
        Initialize the table model.
        
        Args:
            subjects: List of subjects to display.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._subjects = subjects
        self._columns = ["Subject ID", "Sessions", "Files"]
    
    def rowCount(self, parent=QModelIndex()) -> int:
        """Return the number of rows."""
        return len(self._subjects)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        """Return the number of columns."""
        return len(self._columns)
    
    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole) -> Any:
        """Return data for the given index and role."""
        if not index.isValid():
            return None
        
        if role == Qt.ItemDataRole.DisplayRole:
            subject = self._subjects[index.row()]
            col = index.column()
            
            if col == 0:
                return subject.subject_id
            elif col == 1:
                # TODO: return session count
                return len(subject.sessions)
            elif col == 2:
                # TODO: return file count (including all sessions)
                return 0
        
        return None
    
    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole) -> Any:
        """Return header data."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return self._columns[section]
            else:
                return str(section + 1)
        return None
    
    def update_subjects(self, subjects: list[BIDSSubject]):
        """
        Update the subject list and refresh the view.
        
        Args:
            subjects: New list of subjects to display.
        """
        self.beginResetModel()
        self._subjects = subjects
        self.endResetModel()


class FileTreeModel:
    """
    Tree model for displaying BIDS files in a hierarchical view.
    
    Structure: Subject -> Session -> Modality -> Files
    """
    
    def __init__(self, dataset: BIDSDataset):
        """
        Initialize the tree model.
        
        Args:
            dataset: The BIDS dataset to display.
        """
        self.dataset = dataset
        
        # TODO: implement QAbstractItemModel for tree structure
        # TODO: create tree nodes for subjects, sessions, modalities
        # TODO: support lazy loading for large datasets


# TODO: create view models for:
# - Session display
# - File details
# - Filter criteria presentation
# - Export progress
