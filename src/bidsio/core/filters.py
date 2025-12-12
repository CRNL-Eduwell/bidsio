"""
Filtering operations for BIDS datasets.

This module contains functions for filtering BIDSDataset objects based on
various criteria using the new FilterCondition system.
"""

from .models import (
    BIDSDataset,
    BIDSSubject,
    FilterCondition,
    LogicalOperation
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
