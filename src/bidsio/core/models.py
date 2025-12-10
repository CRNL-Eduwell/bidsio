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


@dataclass
class SelectedEntities:
    """
    Entities selected for export.
    
    This represents which entity values should be included in the export.
    Each entity maps to a list of selected values.
    """
    
    entities: dict[str, list[str]] = field(default_factory=dict)
    """Dictionary mapping entity codes to selected values (e.g., {'sub': ['01', '02'], 'task': ['rest']})."""
    
    derivative_pipelines: list[str] = field(default_factory=list)
    """List of derivative pipeline names to include (e.g., ['fmriprep', 'freesurfer'])."""


@dataclass
class FilterCriteria:
    """
    Filtering options for selecting a subset of a BIDS dataset.
    
    All fields are optional; None means no filtering on that dimension.
    NOTE: This class is kept for backwards compatibility but export now uses SelectedEntities.
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
    
    selected_entities: SelectedEntities
    """Entities selected for export."""
    
    output_path: Path
    """Destination directory for the exported dataset."""
    
    overwrite: bool = False
    """Whether to overwrite/merge with existing destination."""


@dataclass
class ExportStats:
    """
    Statistics about files to be exported.
    """
    
    file_count: int = 0
    """Number of files to export."""
    
    total_size: int = 0
    """Total size in bytes."""
    
    def get_size_string(self) -> str:
        """Get human-readable size string."""
        if self.total_size < 1024:
            return f"{self.total_size} B"
        elif self.total_size < 1024 ** 2:
            return f"{self.total_size / 1024:.1f} KB"
        elif self.total_size < 1024 ** 3:
            return f"{self.total_size / (1024 ** 2):.1f} MB"
        else:
            return f"{self.total_size / (1024 ** 3):.2f} GB"


# ============================================================================
# Filter Condition Models
# ============================================================================


@dataclass
class FilterCondition:
    """
    Base class for all filter conditions.
    
    Each filter condition must implement an evaluate() method that determines
    whether a subject matches the condition.
    """
    
    def evaluate(self, subject: BIDSSubject, dataset: BIDSDataset) -> bool:
        """
        Evaluate whether a subject matches this filter condition.
        
        Args:
            subject: The subject to evaluate.
            dataset: The full dataset (for context if needed).
            
        Returns:
            True if the subject matches the condition, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement evaluate()")
    
    def to_dict(self) -> dict:
        """
        Serialize filter condition to dictionary for JSON storage.
        
        Returns:
            Dictionary representation of the filter condition.
        """
        raise NotImplementedError("Subclasses must implement to_dict()")
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FilterCondition':
        """
        Deserialize filter condition from dictionary.
        
        Args:
            data: Dictionary representation of the filter condition.
            
        Returns:
            FilterCondition instance.
        """
        raise NotImplementedError("Subclasses must implement from_dict()")


@dataclass
class SubjectIdFilter(FilterCondition):
    """Filter by subject ID(s)."""
    
    subject_ids: list[str] = field(default_factory=list)
    """List of subject IDs to include."""
    
    def evaluate(self, subject: BIDSSubject, dataset: BIDSDataset) -> bool:
        """Check if subject ID is in the list."""
        if not self.subject_ids:
            return True
        return subject.subject_id in self.subject_ids
    
    def to_dict(self) -> dict:
        return {
            'type': 'subject_id',
            'subject_ids': self.subject_ids
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SubjectIdFilter':
        return cls(subject_ids=data.get('subject_ids', []))


@dataclass
class ModalityFilter(FilterCondition):
    """Filter by imaging modality."""
    
    modalities: list[str] = field(default_factory=list)
    """List of modalities to include (e.g., ['ieeg', 'anat'])."""
    
    def evaluate(self, subject: BIDSSubject, dataset: BIDSDataset) -> bool:
        """Check if subject has files with any of the specified modalities."""
        if not self.modalities:
            return True
        
        # Check all files in subject
        for file in subject.files:
            if file.modality in self.modalities:
                return True
        
        # Check all files in sessions
        for session in subject.sessions:
            for file in session.files:
                if file.modality in self.modalities:
                    return True
        
        return False
    
    def to_dict(self) -> dict:
        return {
            'type': 'modality',
            'modalities': self.modalities
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ModalityFilter':
        return cls(modalities=data.get('modalities', []))


@dataclass
class ParticipantAttributeFilter(FilterCondition):
    """Filter by participant metadata from participants.tsv."""
    
    attribute_name: str = ''
    """Name of the attribute to filter on (e.g., 'age', 'sex', 'group')."""
    
    operator: str = 'equals'
    """Comparison operator: 'equals', 'contains', 'greater_than', 'less_than', 'not_equals'."""
    
    value: str | int | float = ''
    """Value to compare against."""
    
    def evaluate(self, subject: BIDSSubject, dataset: BIDSDataset) -> bool:
        """Check if participant attribute matches the condition."""
        if not self.attribute_name or self.value == '':
            return True
        
        # Get attribute value from subject metadata
        attr_value = subject.metadata.get(self.attribute_name)
        if attr_value is None:
            return False
        
        # Apply operator
        # For equals/not_equals, try numeric comparison first, then fall back to string
        if self.operator in ['equals', 'not_equals']:
            try:
                # Try numeric comparison
                attr_value_num = float(attr_value)
                compare_value_num = float(self.value)
                if self.operator == 'equals':
                    return attr_value_num == compare_value_num
                else:  # not_equals
                    return attr_value_num != compare_value_num
            except (ValueError, TypeError):
                # Fall back to string comparison
                attr_value_str = str(attr_value)
                compare_value_str = str(self.value)
                if self.operator == 'equals':
                    return attr_value_str == compare_value_str
                else:  # not_equals
                    return attr_value_str != compare_value_str
        elif self.operator == 'contains':
            try:
                attr_value_str = str(attr_value)
                compare_value_str = str(self.value)
                return compare_value_str in attr_value_str
            except (ValueError, TypeError):
                return False
        elif self.operator in ['greater_than', 'less_than']:
            try:
                attr_value_num = float(attr_value)
                compare_value_num = float(self.value)
                if self.operator == 'greater_than':
                    return attr_value_num > compare_value_num
                else:  # less_than
                    return attr_value_num < compare_value_num
            except (ValueError, TypeError):
                return False
        else:
            return False
    
    def to_dict(self) -> dict:
        return {
            'type': 'participant_attribute',
            'attribute_name': self.attribute_name,
            'operator': self.operator,
            'value': self.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ParticipantAttributeFilter':
        return cls(
            attribute_name=data.get('attribute_name', ''),
            operator=data.get('operator', 'equals'),
            value=data.get('value', '')
        )


@dataclass
class EntityFilter(FilterCondition):
    """Filter by BIDS entity value."""
    
    entity_code: str = ''
    """Entity code (e.g., 'task', 'run', 'ses', 'acq')."""
    
    operator: str = 'equals'
    """Comparison operator: 'equals', 'contains', 'not_equals'."""
    
    value: str = ''
    """Value to compare against."""
    
    def evaluate(self, subject: BIDSSubject, dataset: BIDSDataset) -> bool:
        """Check if subject has files with entity values matching the condition."""
        if not self.entity_code or self.value == '':
            return True
        
        # Special handling for 'ses' entity
        if self.entity_code == 'ses':
            for session in subject.sessions:
                if session.session_id and self._compare_values(session.session_id, self.value):
                    return True
            return False
        
        # Check all files in subject
        for file in subject.files:
            if self.entity_code in file.entities:
                entity_value = file.entities[self.entity_code]
                if self._compare_values(entity_value, self.value):
                    return True
        
        # Check all files in sessions
        for session in subject.sessions:
            for file in session.files:
                if self.entity_code in file.entities:
                    entity_value = file.entities[self.entity_code]
                    if self._compare_values(entity_value, self.value):
                        return True
        
        return False
    
    def _compare_values(self, entity_value: str, compare_value: str) -> bool:
        """Compare entity value with filter value using the operator."""
        entity_value = str(entity_value)
        compare_value = str(compare_value)
        
        if self.operator == 'equals':
            return entity_value == compare_value
        elif self.operator == 'not_equals':
            return entity_value != compare_value
        elif self.operator == 'contains':
            return compare_value in entity_value
        else:
            return False
    
    def to_dict(self) -> dict:
        return {
            'type': 'entity',
            'entity_code': self.entity_code,
            'operator': self.operator,
            'value': self.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'EntityFilter':
        return cls(
            entity_code=data.get('entity_code', ''),
            operator=data.get('operator', 'equals'),
            value=data.get('value', '')
        )


@dataclass
class ChannelAttributeFilter(FilterCondition):
    """Filter by iEEG channel attributes (_channels.tsv)."""
    
    attribute_name: str = ''
    """Name of the channel attribute to filter on (e.g., 'low_cutoff', 'high_cutoff', 'type')."""
    
    operator: str = 'equals'
    """Comparison operator: 'equals', 'contains', 'greater_than', 'less_than', 'not_equals'."""
    
    value: str | int | float = ''
    """Value to compare against."""
    
    def evaluate(self, subject: BIDSSubject, dataset: BIDSDataset) -> bool:
        """Check if any iEEG file has channels matching the criteria."""
        if not self.attribute_name or self.value == '':
            return True
        
        # Check if subject has iEEG data
        if not subject.ieeg_data or not subject.ieeg_data.channels:
            return False
        
        # Check all channel files
        for channel_list in subject.ieeg_data.channels.values():
            for channel in channel_list:
                if self.attribute_name not in channel:
                    continue
                
                attr_value = channel[self.attribute_name]
                
                # Apply operator
                match = False
                
                # For equals/not_equals, try numeric comparison first, then fall back to string
                if self.operator in ['equals', 'not_equals']:
                    try:
                        # Try numeric comparison
                        attr_value_num = float(attr_value)
                        compare_value_num = float(self.value)
                        if self.operator == 'equals':
                            match = attr_value_num == compare_value_num
                        else:  # not_equals
                            match = attr_value_num != compare_value_num
                    except (ValueError, TypeError):
                        # Fall back to string comparison
                        attr_value_str = str(attr_value)
                        compare_value_str = str(self.value)
                        if self.operator == 'equals':
                            match = attr_value_str == compare_value_str
                        else:  # not_equals
                            match = attr_value_str != compare_value_str
                elif self.operator == 'contains':
                    try:
                        attr_value_str = str(attr_value)
                        compare_value_str = str(self.value)
                        match = compare_value_str in attr_value_str
                    except (ValueError, TypeError):
                        match = False
                elif self.operator in ['greater_than', 'less_than']:
                    try:
                        attr_value_num = float(attr_value)
                        compare_value_num = float(self.value)
                        if self.operator == 'greater_than':
                            match = attr_value_num > compare_value_num
                        else:  # less_than
                            match = attr_value_num < compare_value_num
                    except (ValueError, TypeError):
                        match = False
                
                if match:
                    return True
        
        return False
    
    def to_dict(self) -> dict:
        return {
            'type': 'channel_attribute',
            'attribute_name': self.attribute_name,
            'operator': self.operator,
            'value': self.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ChannelAttributeFilter':
        return cls(
            attribute_name=data.get('attribute_name', ''),
            operator=data.get('operator', 'equals'),
            value=data.get('value', '')
        )


@dataclass
class ElectrodeAttributeFilter(FilterCondition):
    """Filter by iEEG electrode attributes (_electrodes.tsv)."""
    
    attribute_name: str = ''
    """Name of the electrode attribute to filter on (e.g., 'material', 'manufacturer', 'x', 'y', 'z')."""
    
    operator: str = 'equals'
    """Comparison operator: 'equals', 'contains', 'greater_than', 'less_than', 'not_equals'."""
    
    value: str | int | float = ''
    """Value to compare against."""
    
    def evaluate(self, subject: BIDSSubject, dataset: BIDSDataset) -> bool:
        """Check if any iEEG file has electrodes matching the criteria."""
        if not self.attribute_name or self.value == '':
            return True
        
        # Check if subject has iEEG data
        if not subject.ieeg_data or not subject.ieeg_data.electrodes:
            return False
        
        # Check all electrode files
        for electrode_list in subject.ieeg_data.electrodes.values():
            for electrode in electrode_list:
                if self.attribute_name not in electrode:
                    continue
                
                attr_value = electrode[self.attribute_name]
                
                # Apply operator
                match = False
                
                # For equals/not_equals, try numeric comparison first, then fall back to string
                if self.operator in ['equals', 'not_equals']:
                    try:
                        # Try numeric comparison
                        attr_value_num = float(attr_value)
                        compare_value_num = float(self.value)
                        if self.operator == 'equals':
                            match = attr_value_num == compare_value_num
                        else:  # not_equals
                            match = attr_value_num != compare_value_num
                    except (ValueError, TypeError):
                        # Fall back to string comparison
                        attr_value_str = str(attr_value)
                        compare_value_str = str(self.value)
                        if self.operator == 'equals':
                            match = attr_value_str == compare_value_str
                        else:  # not_equals
                            match = attr_value_str != compare_value_str
                elif self.operator == 'contains':
                    try:
                        attr_value_str = str(attr_value)
                        compare_value_str = str(self.value)
                        match = compare_value_str in attr_value_str
                    except (ValueError, TypeError):
                        match = False
                elif self.operator in ['greater_than', 'less_than']:
                    try:
                        attr_value_num = float(attr_value)
                        compare_value_num = float(self.value)
                        if self.operator == 'greater_than':
                            match = attr_value_num > compare_value_num
                        else:  # less_than
                            match = attr_value_num < compare_value_num
                    except (ValueError, TypeError):
                        match = False
                
                if match:
                    return True
        
        return False
    
    def to_dict(self) -> dict:
        return {
            'type': 'electrode_attribute',
            'attribute_name': self.attribute_name,
            'operator': self.operator,
            'value': self.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ElectrodeAttributeFilter':
        return cls(
            attribute_name=data.get('attribute_name', ''),
            operator=data.get('operator', 'equals'),
            value=data.get('value', '')
        )


@dataclass
class LogicalOperation:
    """
    Logical combination of filter conditions.
    
    Supports AND, OR, and NOT operations for composing complex filters.
    """
    
    operator: str = 'AND'
    """Logical operator: 'AND', 'OR', 'NOT'."""
    
    conditions: list['FilterCondition | LogicalOperation'] = field(default_factory=list)
    """List of child conditions or nested logical operations."""
    
    def evaluate(self, subject: BIDSSubject, dataset: BIDSDataset) -> bool:
        """Evaluate the logical operation recursively."""
        if not self.conditions:
            return True
        
        if self.operator == 'AND':
            return all(cond.evaluate(subject, dataset) for cond in self.conditions)
        elif self.operator == 'OR':
            return any(cond.evaluate(subject, dataset) for cond in self.conditions)
        elif self.operator == 'NOT':
            # NOT operates on the first condition only
            if self.conditions:
                return not self.conditions[0].evaluate(subject, dataset)
            return True
        else:
            return False
    
    def to_dict(self) -> dict:
        return {
            'type': 'logical_operation',
            'operator': self.operator,
            'conditions': [cond.to_dict() for cond in self.conditions]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LogicalOperation':
        """
        Deserialize logical operation from dictionary.
        
        Args:
            data: Dictionary representation.
            
        Returns:
            LogicalOperation instance.
        """
        conditions = []
        for cond_data in data.get('conditions', []):
            cond_type = cond_data.get('type')
            if cond_type == 'subject_id':
                conditions.append(SubjectIdFilter.from_dict(cond_data))
            elif cond_type == 'modality':
                conditions.append(ModalityFilter.from_dict(cond_data))
            elif cond_type == 'participant_attribute':
                conditions.append(ParticipantAttributeFilter.from_dict(cond_data))
            elif cond_type == 'entity':
                conditions.append(EntityFilter.from_dict(cond_data))
            elif cond_type == 'channel_attribute':
                conditions.append(ChannelAttributeFilter.from_dict(cond_data))
            elif cond_type == 'electrode_attribute':
                conditions.append(ElectrodeAttributeFilter.from_dict(cond_data))
            elif cond_type == 'logical_operation':
                conditions.append(LogicalOperation.from_dict(cond_data))
        
        return cls(
            operator=data.get('operator', 'AND'),
            conditions=conditions
        )
