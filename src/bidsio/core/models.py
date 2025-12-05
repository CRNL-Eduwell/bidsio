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
    
    metadata: Optional[dict] = None
    """Metadata from associated JSON sidecar file.
    
    - In eager mode: Loaded during dataset parsing and stored here.
    - In lazy mode: Set to None initially, loaded on-demand via load_metadata().
    """
    
    # TODO: add validation for BIDS compliance
    
    def load_metadata(self, force_reload: bool = False) -> Optional[dict]:
        """
        Load metadata from the associated JSON sidecar file (lazy loading).
        
        This method is designed for lazy loading mode. In eager mode, metadata
        is already loaded during dataset parsing.
        
        BIDS sidecar files have the same name as the data file but with .json extension.
        For example, sub-01_T1w.nii.gz has sidecar sub-01_T1w.json
        
        Args:
            force_reload: If True, reload metadata even if already cached.
        
        Returns:
            Dictionary of metadata if sidecar exists, None otherwise.
        """
        # Return cached metadata unless force_reload is True
        if self.metadata is not None and not force_reload:
            return self.metadata
        
        # Don't load metadata for JSON files themselves
        if self.extension == '.json':
            return None
        
        # Construct JSON sidecar path
        # Remove extensions like .nii.gz, .tsv, etc. and add .json
        json_path = self.path.parent / (self.path.name.replace(self.extension or '', '') + '.json')
        
        if not json_path.exists():
            return None
        
        try:
            import json
            with open(json_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
                return self.metadata
        except (json.JSONDecodeError, IOError) as e:
            # Log error but don't fail - metadata is optional
            return None
@dataclass
class BIDSSession:
    """Represents a single session within a BIDS subject."""
    
    session_id: Optional[str] = None
    """Session identifier (e.g., '01', 'pre', 'post')."""
    
    files: list[BIDSFile] = field(default_factory=list)
    """All files in this session (run info is in file entities)."""
    
    # TODO: add methods to filter files by task, modality, or run
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
    
    dataset_files: list[BIDSFile] = field(default_factory=list)
    """Dataset-level files (README, LICENSE, CHANGES, etc.)."""
        
    def get_subject(self, subject_id: str) -> Optional[BIDSSubject]:
        """
        Retrieve a subject by ID.
        
        Args:
            subject_id: The subject identifier to search for.
            
        Returns:
            The BIDSSubject if found, None otherwise.
        """
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
        modalities = set()
        
        # Traverse all subjects
        for subject in self.subjects:
            # Check subject-level files
            for file in subject.files:
                if file.modality:
                    modalities.add(file.modality)
            
            # Check session-level files
            for session in subject.sessions:
                for file in session.files:
                    if file.modality:
                        modalities.add(file.modality)
        
        return modalities
    
    def get_all_tasks(self) -> set[str]:
        """
        Get all unique task names in the dataset.
        
        Returns:
            Set of task strings (e.g., {'rest', 'nback', 'faces'}).
        """
        tasks = set()
        
        # Traverse all subjects
        for subject in self.subjects:
            # Check subject-level files
            for file in subject.files:
                if 'task' in file.entities:
                    tasks.add(file.entities['task'])
            
            # Check session-level files
            for session in subject.sessions:
                for file in session.files:
                    if 'task' in file.entities:
                        tasks.add(file.entities['task'])
        
        return tasks


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
