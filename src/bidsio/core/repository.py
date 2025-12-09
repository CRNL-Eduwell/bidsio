"""
Repository pattern for accessing BIDS dataset data.

This module provides a clean interface for loading and querying BIDS datasets
without exposing implementation details.
"""

from pathlib import Path
from typing import Optional, Callable

from .models import BIDSDataset, BIDSSubject, FilterCriteria
from ..infrastructure.bids_loader import BidsLoader
from ..config.settings import get_settings


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
            
        Raises:
            FileNotFoundError: If the root path does not exist.
            ValueError: If the path is not a directory or not a valid BIDS dataset.
        """
        self.root_path = Path(root_path)
        self._dataset: Optional[BIDSDataset] = None
        self._settings = get_settings()
        self._loader: Optional[BidsLoader] = None
        self._is_lazy_loaded = False
        
        # Validate that root_path exists
        if not self.root_path.exists():
            raise FileNotFoundError(f"Dataset path does not exist: {self.root_path}")
        
        if not self.root_path.is_dir():
            raise ValueError(f"Path is not a directory: {self.root_path}")
        
        # Validate BIDS structure (check for dataset_description.json)
        desc_path = self.root_path / "dataset_description.json"
        if not desc_path.exists():
            raise ValueError(f"Not a valid BIDS dataset (missing dataset_description.json): {self.root_path}")
    
    def load(self, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> BIDSDataset:
        """
        Load and index the BIDS dataset.
        
        Uses lazy or eager loading based on settings.
        
        Args:
            progress_callback: Optional callback function(current, total, message) for progress updates.
        
        Returns:
            A BIDSDataset object representing the loaded dataset.
            
        Raises:
            ValueError: If the path is not a valid BIDS dataset.
            FileNotFoundError: If the root path does not exist.
        """
        # Validation is already done in __init__
        
        # Create loader instance
        self._loader = BidsLoader(self.root_path, progress_callback=progress_callback)
        
        # Choose loading strategy based on settings
        if self._settings.lazy_loading:
            # Lazy loading: only load dataset structure, subjects loaded on-demand
            self._dataset = self._loader.load_lazy()
            self._is_lazy_loaded = True
        else:
            # Eager loading: load everything immediately
            self._dataset = self._loader.load()
            self._is_lazy_loaded = False
        
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
        
        If lazy loading is enabled, this will load the subject on-demand.
        
        Args:
            subject_id: The subject identifier.
            
        Returns:
            The BIDSSubject if found, None otherwise.
        """
        if self._dataset is None:
            return None
        
        # Check if subject is already loaded
        existing_subject = self._dataset.get_subject(subject_id)
        if existing_subject is not None:
            return existing_subject
        
        # If lazy loaded and subject not found, try loading it on-demand
        if self._is_lazy_loaded and self._loader is not None:
            subject = self._loader.load_subject(subject_id)
            if subject is not None:
                # Add to dataset
                self._dataset.subjects.append(subject)
                return subject
        
        return None
    
    def get_subject_ids(self) -> list[str]:
        """
        Get a list of all subject IDs in the dataset.
        
        For lazy loading, this is fast as it only lists directories.
        For eager loading, returns IDs from already loaded subjects.
        
        Returns:
            List of subject IDs.
        """
        if self._is_lazy_loaded and self._loader is not None:
            # For lazy loading, get IDs from filesystem
            return self._loader.get_subject_ids()
        elif self._dataset is not None:
            # For eager loading, get from loaded subjects
            return [s.subject_id for s in self._dataset.subjects]
        else:
            return []
    
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
    
    def load_ieeg_data_for_all_subjects(self, progress_callback: Optional[Callable[[int, int, str], None]] = None):
        """
        Load iEEG TSV data for all subjects in the dataset.
        
        This is useful for lazy-loaded datasets when filtering is about to be applied.
        For eager-loaded datasets, this is a no-op as iEEG data is already loaded.
        
        Args:
            progress_callback: Optional callback function(current, total, message) for progress updates.
        """
        if self._dataset is None or self._loader is None:
            return
        
        # If not lazy loaded, iEEG data is already loaded
        if not self._is_lazy_loaded:
            return
        
        total_subjects = len(self._dataset.subjects)
        
        for idx, subject in enumerate(self._dataset.subjects):
            # Skip if iEEG data already loaded for this subject
            if subject.ieeg_data is not None:
                continue
            
            # Report progress
            if progress_callback:
                progress_callback(idx + 1, total_subjects, f"Loading iEEG data for subject: {subject.subject_id}")
            
            # Load iEEG data
            subject_path = self.root_path / f"sub-{subject.subject_id}"
            if subject_path.exists():
                subject.ieeg_data = self._loader._load_ieeg_data(subject_path)
