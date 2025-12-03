"""
Core domain models for BIDS dataset representation.

This module contains pure data models representing BIDS entities.
These models are GUI-agnostic and should not import any UI frameworks.
"""

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class BIDSFile:
    """Represents a single file in a BIDS dataset."""
    
    path: Path
    """Absolute or relative path to the file."""
    
    modality: Optional[str] = None
    """Imaging modality (e.g., 'anat', 'func', 'dwi')."""
    
    suffix: Optional[str] = None
    """File suffix (e.g., 'T1w', 'bold', 'events')."""
    
    extension: Optional[str] = None
    """File extension (e.g., '.nii.gz', '.json', '.tsv')."""
    
    entities: dict[str, str] = field(default_factory=dict)
    """BIDS entities extracted from filename (e.g., {'task': 'rest', 'run': '01'})."""
    
    # TODO: add metadata property that loads associated JSON sidecar
    # TODO: add validation for BIDS compliance


@dataclass
class BIDSRun:
    """Represents a single run within a BIDS session."""
    
    run_id: Optional[str] = None
    """Run identifier (e.g., '01', '02'), if applicable."""
    
    task: Optional[str] = None
    """Task name for functional runs."""
    
    files: list[BIDSFile] = field(default_factory=list)
    """List of files associated with this run."""
    
    # TODO: add methods to retrieve files by modality or suffix
    # TODO: consider grouping files by acquisition or reconstruction


@dataclass
class BIDSSession:
    """Represents a single session within a BIDS subject."""
    
    session_id: Optional[str] = None
    """Session identifier (e.g., '01', 'pre', 'post')."""
    
    runs: list[BIDSRun] = field(default_factory=list)
    """List of runs in this session."""
    
    files: list[BIDSFile] = field(default_factory=list)
    """Session-level files (e.g., anatomical scans not tied to a run)."""
    
    # TODO: add methods to filter runs by task or modality
    # TODO: consider session-level metadata


@dataclass
class BIDSSubject:
    """Represents a subject in a BIDS dataset."""
    
    subject_id: str
    """Subject identifier (e.g., '01', 'sub-001')."""
    
    sessions: list[BIDSSession] = field(default_factory=list)
    """List of sessions for this subject."""
    
    files: list[BIDSFile] = field(default_factory=list)
    """Subject-level files not associated with a specific session."""
    
    metadata: dict[str, str] = field(default_factory=dict)
    """Participant metadata from participants.tsv (age, sex, group, etc.)."""
    
    # TODO: add methods to query sessions by ID


@dataclass
class BIDSDataset:
    """Represents a complete BIDS dataset."""
    
    root_path: Path
    """Root directory of the BIDS dataset."""
    
    subjects: list[BIDSSubject] = field(default_factory=list)
    """List of subjects in the dataset."""
    
    dataset_description: dict = field(default_factory=dict)
    """Contents of dataset_description.json."""
    
    # TODO: add properties for dataset-level files (README, CHANGES, participants.tsv)
    # TODO: add methods to query subjects by ID
    # TODO: add method to get all unique tasks, modalities, sessions
    # TODO: consider caching for performance with large datasets
    
    def get_subject(self, subject_id: str) -> Optional[BIDSSubject]:
        """
        Retrieve a subject by ID.
        
        Args:
            subject_id: The subject identifier to search for.
            
        Returns:
            The BIDSSubject if found, None otherwise.
        """
        # TODO: implement efficient lookup (consider using dict internally)
        for subject in self.subjects:
            if subject.subject_id == subject_id:
                return subject
        return None
    
    def get_all_modalities(self) -> set[str]:
        """
        Get all unique imaging modalities in the dataset.
        
        Returns:
            Set of modality strings (e.g., {'anat', 'func', 'dwi'}).
        """
        # TODO: implement by traversing all files
        raise NotImplementedError("get_all_modalities is not implemented yet.")
    
    def get_all_tasks(self) -> set[str]:
        """
        Get all unique task names in the dataset.
        
        Returns:
            Set of task strings (e.g., {'rest', 'nback', 'faces'}).
        """
        # TODO: implement by traversing all runs
        raise NotImplementedError("get_all_tasks is not implemented yet.")


@dataclass
class FilterCriteria:
    """
    Filtering options for selecting a subset of a BIDS dataset.
    
    All fields are optional; None means no filtering on that dimension.
    """
    
    subject_ids: Optional[list[str]] = None
    """List of subject IDs to include."""
    
    session_ids: Optional[list[str]] = None
    """List of session IDs to include."""
    
    task_names: Optional[list[str]] = None
    """List of task names to include."""
    
    modalities: Optional[list[str]] = None
    """List of modalities to include."""
    
    run_ids: Optional[list[str]] = None
    """List of run IDs to include."""
    
    # TODO: add more filtering options (e.g., acquisition date, file type)
    # TODO: add validation to ensure criteria are sensible


@dataclass
class ExportRequest:
    """
    Specification for exporting a subset of a BIDS dataset.
    """
    
    source_dataset: BIDSDataset
    """The source dataset to export from."""
    
    filter_criteria: FilterCriteria
    """Criteria for selecting which data to export."""
    
    output_path: Path
    """Destination directory for the exported dataset."""
    
    copy_mode: str = "copy"
    """How to handle files: 'copy', 'symlink', or 'hardlink'."""
    
    include_derivatives: bool = False
    """Whether to include derivative files."""
    
    # TODO: add option to export participants.tsv with only selected subjects
    # TODO: add option to generate a manifest file listing exported files
    # TODO: validate output_path is writable
