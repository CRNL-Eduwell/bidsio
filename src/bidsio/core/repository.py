"""
Repository pattern for accessing BIDS dataset data.

This module provides a clean interface for loading and querying BIDS datasets
without exposing implementation details.
"""

from pathlib import Path
from typing import Optional

from .models import BIDSDataset, BIDSSubject, FilterCriteria
from ..infrastructure.bids_loader import BidsLoader


class BidsRepository:
    """
    Repository for loading and accessing BIDS datasets.
    
    This class provides the main interface for interacting with BIDS data,
    abstracting away the details of filesystem access and dataset indexing.
    """
    
    def __init__(self, root_path: Path):
        """
        Initialize the repository with a BIDS dataset root path.
        
        Args:
            root_path: Path to the root directory of a BIDS dataset.
        """
        self.root_path = Path(root_path)
        self._dataset: Optional[BIDSDataset] = None
        
        # TODO: validate that root_path exists and is a directory
        # TODO: consider lazy loading vs eager loading strategy
    
    def load(self) -> BIDSDataset:
        """
        Load and index the BIDS dataset.
        
        Returns:
            A BIDSDataset object representing the loaded dataset.
            
        Raises:
            ValueError: If the path is not a valid BIDS dataset.
            FileNotFoundError: If the root path does not exist.
        """
        # Validate that root_path exists
        if not self.root_path.exists():
            raise FileNotFoundError(f"Dataset path does not exist: {self.root_path}")
        
        if not self.root_path.is_dir():
            raise ValueError(f"Path is not a directory: {self.root_path}")
        
        # Delegate to infrastructure layer for loading
        loader = BidsLoader(self.root_path)
        self._dataset = loader.load()
        
        return self._dataset
    
    def get_dataset(self) -> Optional[BIDSDataset]:
        """
        Get the currently loaded dataset.
        
        Returns:
            The loaded BIDSDataset, or None if not yet loaded.
        """
        return self._dataset
    
    def get_subject(self, subject_id: str) -> Optional[BIDSSubject]:
        """
        Retrieve a specific subject from the dataset.
        
        Args:
            subject_id: The subject identifier.
            
        Returns:
            The BIDSSubject if found, None otherwise.
        """
        if self._dataset is None:
            return None
        return self._dataset.get_subject(subject_id)
    
    def query(self, criteria: FilterCriteria) -> BIDSDataset:
        """
        Query the dataset with filter criteria.
        
        Args:
            criteria: Filtering criteria to apply.
            
        Returns:
            A new BIDSDataset containing only the filtered data.
        """
        # TODO: implement filtering logic
        # TODO: consider performance for large datasets
        # TODO: delegate to filters module
        raise NotImplementedError("query() is not implemented yet.")
    
    def get_summary_statistics(self) -> dict:
        """
        Get summary statistics about the dataset.
        
        Returns:
            Dictionary with statistics (subject count, session count, etc.).
        """
        # TODO: implement statistics gathering
        # TODO: include counts for subjects, sessions, runs
        # TODO: include unique tasks, modalities
        raise NotImplementedError("get_summary_statistics is not implemented yet.")
