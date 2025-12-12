"""
Filtering operations for BIDS datasets.

This module contains filter condition classes and functions for filtering
BIDSDataset objects based on various criteria.
"""

from dataclasses import dataclass, field

from .models import BIDSSubject, BIDSDataset


@dataclass
class FilterCondition:
    """
    Base class for all filter conditions.
    
    Each filter condition must implement an evaluate() method that determines
    whether a subject matches the condition.
    """
    
    def evaluate(self, subject: 'BIDSSubject') -> bool:
        """
        Evaluate whether a subject matches this condition.
        
        Args:
            subject: The subject to evaluate.
            
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
    """Filter by subject ID."""
    
    subject_id: str = ''
    """Subject ID to match."""
    
    def evaluate(self, subject: 'BIDSSubject') -> bool:
        """Check if subject ID matches."""
        if not self.subject_id:
            return True
        return subject.subject_id == self.subject_id
    
    def to_dict(self) -> dict:
        return {
            'type': 'subject_id',
            'subject_id': self.subject_id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SubjectIdFilter':
        # Handle old format with subject_ids list for backward compatibility
        if 'subject_ids' in data:
            subject_ids = data.get('subject_ids', [])
            subject_id = subject_ids[0] if subject_ids else ''
            return cls(subject_id=subject_id)
        return cls(subject_id=data.get('subject_id', ''))


@dataclass
class ModalityFilter(FilterCondition):
    """Filter by imaging modality."""
    
    modality: str = ''
    """Modality to match (e.g., 'ieeg', 'anat')."""
    
    def evaluate(self, subject: 'BIDSSubject') -> bool:
        """Check if subject has files with the specified modality."""
        if not self.modality:
            return True
        
        # Check all files in subject
        for file in subject.files:
            if file.modality == self.modality:
                return True
        
        # Check all files in sessions
        for session in subject.sessions:
            for file in session.files:
                if file.modality == self.modality:
                    return True
        
        return False
    
    def to_dict(self) -> dict:
        return {
            'type': 'modality',
            'modality': self.modality
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ModalityFilter':
        # Handle old format with modalities list for backward compatibility
        if 'modalities' in data:
            modalities = data.get('modalities', [])
            modality = modalities[0] if modalities else ''
            return cls(modality=modality)
        return cls(modality=data.get('modality', ''))


@dataclass
class ParticipantAttributeFilter(FilterCondition):
    """Filter by participant metadata from participants.tsv."""
    
    attribute_name: str = ''
    """Name of the attribute to filter on (e.g., 'age', 'sex', 'group')."""
    
    operator: str = 'equals'
    """Comparison operator: 'equals', 'contains', 'greater_than', 'less_than', 'not_equals'."""
    
    value: str | int | float = ''
    """Value to compare against."""
    
    def evaluate(self, subject: 'BIDSSubject') -> bool:
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
    
    def evaluate(self, subject: 'BIDSSubject') -> bool:
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
    
    def evaluate(self, subject: 'BIDSSubject') -> bool:
        """Check if subject has iEEG channels matching the condition."""
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
    
    def evaluate(self, subject: 'BIDSSubject') -> bool:
        """Check if subject has iEEG electrodes matching the condition."""
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
    
    def evaluate(self, subject: 'BIDSSubject') -> bool:
        """Evaluate the logical operation recursively."""
        if not self.conditions:
            return True
        
        if self.operator == 'AND':
            return all(cond.evaluate(subject) for cond in self.conditions)
        elif self.operator == 'OR':
            return any(cond.evaluate(subject) for cond in self.conditions)
        elif self.operator == 'NOT':
            # NOT operates on the first condition only
            if self.conditions:
                return not self.conditions[0].evaluate(subject)
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


def apply_filter(
    dataset: BIDSDataset,
    filter_expr: FilterCondition | LogicalOperation
) -> BIDSDataset:
    """
    Apply a filter expression to a dataset and return a new filtered dataset.
    
    This function evaluates the filter expression against each subject and
    creates a new BIDSDataset containing only the subjects that match.
    
    Args:
        dataset: The source dataset to filter.
        filter_expr: The filter expression to apply (single condition or logical operation).
        
    Returns:
        A new BIDSDataset with only matching subjects. The dataset structure
        (root_path, description, etc.) is preserved, but the subjects list
        contains only those that passed the filter.
    """
    filtered_subjects = []
    
    for subject in dataset.subjects:
        if filter_expr.evaluate(subject):
            filtered_subjects.append(subject)
    
    # Create new dataset with filtered subjects
    return BIDSDataset(
        root_path=dataset.root_path,
        subjects=filtered_subjects,
        dataset_description=dataset.dataset_description,
        dataset_files=dataset.dataset_files
    )


def get_matching_subject_ids(
    dataset: BIDSDataset,
    filter_expr: FilterCondition | LogicalOperation
) -> list[str]:
    """
    Get list of subject IDs that match a filter expression.
    
    This is a lightweight alternative to apply_filter() when you only need
    the subject IDs rather than a full filtered dataset.
    
    Args:
        dataset: The source dataset.
        filter_expr: The filter expression to apply.
        
    Returns:
        List of subject IDs that match the filter.
    """
    matching_ids = []
    
    for subject in dataset.subjects:
        if filter_expr.evaluate(subject):
            matching_ids.append(subject.subject_id)
    
    return matching_ids
