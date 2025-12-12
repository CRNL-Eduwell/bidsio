"""
Core domain models for BIDS dataset representation.

This module contains pure data models representing BIDS entities.
These models are GUI-agnostic and should not import any UI frameworks.
"""

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from .entity_config import BIDS_ENTITIES


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


@dataclass
class IEEGData:
    """
    Container for iEEG-specific TSV data (channels and electrodes).
    
    This class stores the relationship between iEEG data files and their
    associated _channels.tsv and _electrodes.tsv metadata files.
    """
    
    channels: dict[Path, list[dict]] = field(default_factory=dict)
    """Mapping from _channels.tsv file path to list of channel dictionaries."""
    
    electrodes: dict[Path, list[dict]] = field(default_factory=dict)
    """Mapping from _electrodes.tsv file path to list of electrode dictionaries."""
    
    def get_all_channel_attributes(self) -> set[str]:
        """
        Get all unique channel attribute names across all channel files.
        
        Returns:
            Set of attribute names (column headers).
        """
        attributes = set()
        for channel_list in self.channels.values():
            if channel_list:
                attributes.update(channel_list[0].keys())
        return attributes
    
    def get_all_electrode_attributes(self) -> set[str]:
        """
        Get all unique electrode attribute names across all electrode files.
        
        Returns:
            Set of attribute names (column headers).
        """
        attributes = set()
        for electrode_list in self.electrodes.values():
            if electrode_list:
                attributes.update(electrode_list[0].keys())
        return attributes


@dataclass
class BIDSDerivative:
    """Represents a derivative pipeline for a subject."""
    
    pipeline_name: str
    """Name of the derivative pipeline (e.g., 'fmriprep', 'freesurfer')."""
    
    sessions: list[BIDSSession] = field(default_factory=list)
    """List of sessions with derivative data (mirrors subject structure)."""
    
    files: list[BIDSFile] = field(default_factory=list)
    """Subject-level derivative files not in sessions."""
    
    pipeline_description: dict = field(default_factory=dict)
    """Contents of pipeline's dataset_description.json if present."""


@dataclass
class BIDSSubject:
    """Represents a subject in a BIDS dataset."""
    
    subject_id: str
    """Subject identifier (e.g., '01', 'sub-001')."""
    
    sessions: list[BIDSSession] = field(default_factory=list)
    """List of sessions for this subject."""
    
    files: list[BIDSFile] = field(default_factory=list)
    """Subject-level files not associated with a specific session."""
    
    derivatives: list[BIDSDerivative] = field(default_factory=list)
    """List of derivative pipelines for this subject."""
    
    metadata: dict[str, str] = field(default_factory=dict)
    """Participant metadata from participants.tsv (age, sex, group, etc.)."""
    
    ieeg_data: Optional[IEEGData] = None
    """iEEG-specific data (channels and electrodes TSV files) if subject has iEEG data."""
    
    def get_derivative(self, pipeline_name: str) -> Optional[BIDSDerivative]:
        """
        Retrieve a derivative pipeline by name.
        
        Args:
            pipeline_name: The pipeline name to search for.
            
        Returns:
            The BIDSDerivative if found, None otherwise.
        """
        for derivative in self.derivatives:
            if derivative.pipeline_name == pipeline_name:
                return derivative
        return None


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
    
    def get_all_entity_values(self, entity: str) -> list[str]:
        """
        Get all unique values for a specific BIDS entity in the dataset.
        
        Args:
            entity: The entity code (e.g., 'sub', 'ses', 'task', 'run').
            
        Returns:
            Sorted list of unique values for that entity.
        """
        values = set()
        
        # Special handling for 'sub' entity - extract from subject IDs
        if entity == 'sub':
            for subject in self.subjects:
                values.add(subject.subject_id)
            return sorted(values)
        
        # Special handling for 'ses' entity - extract from session IDs
        if entity == 'ses':
            for subject in self.subjects:
                for session in subject.sessions:
                    if session.session_id:
                        values.add(session.session_id)
            return sorted(values)
        
        # For other entities, traverse all files and extract from file entities
        for subject in self.subjects:
            # Check subject-level files
            for file in subject.files:
                if entity in file.entities:
                    values.add(file.entities[entity])
            
            # Check session-level files
            for session in subject.sessions:
                for file in session.files:
                    if entity in file.entities:
                        values.add(file.entities[entity])
        
        return sorted(values)
    
    def get_all_derivative_pipelines(self) -> list[str]:
        """
        Get all derivative pipeline names in the dataset.
        
        Extracts pipeline names from loaded derivative data across all subjects.
        
        Returns:
            Sorted list of unique pipeline names (e.g., ['fmriprep', 'freesurfer']).
        """
        pipelines = set()
        
        # Collect pipeline names from all subjects
        for subject in self.subjects:
            for derivative in subject.derivatives:
                pipelines.add(derivative.pipeline_name)
        
        return sorted(pipelines)
    
    def get_all_entities(self) -> dict[str, list[str]]:
        """
        Get all entities present in the dataset with their values.
        
        Returns:
            Dictionary mapping entity codes to lists of values.
            Only includes entities that actually exist in the dataset.
        """
        entities_data = {}
        
        # Check each known BIDS entity
        for entity_code in BIDS_ENTITIES.keys():
            values = self.get_all_entity_values(entity_code)
            if values:  # Only include if values exist
                entities_data[entity_code] = values
        
        return entities_data

