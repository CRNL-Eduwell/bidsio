"""
BIDS entity configuration.

This module provides a centralized mapping of BIDS entity codes to their full names.
These entities are used throughout the application for filtering, exporting, and display.
"""

# Mapping of BIDS entity codes to full names
# Based on BIDS specification: https://bids-specification.readthedocs.io/
BIDS_ENTITIES = {
    'sub': 'Subject',
    'ses': 'Session',
    'sample': 'Sample',
    'task': 'Task',
    'tracksys': 'Tracking System',
    'acq': 'Acquisition',
    'nuc': 'Nucleus',
    'voi': 'Volume of Interest',
    'ce': 'Contrast Enhancing Agent',
    'trc': 'Tracer',
    'stain': 'Stain',
    'rec': 'Reconstruction',
    'dir': 'Phase-Encoding Direction',
    'run': 'Run',
    'mod': 'Corresponding Modality',
    'echo': 'Echo',
    'flip': 'Flip Angle',
    'inv': 'Inversion Time',
    'mt': 'Magnetization Transfer',
    'part': 'Part',
    'proc': 'Processed (on device)',
    'hemi': 'Hemisphere',
    'space': 'Space',
    'split': 'Split',
    'recording': 'Recording',
    'chunk': 'Chunk',
    'seg': 'Segmentation',
    'res': 'Resolution',
    'den': 'Density',
    'label': 'Label',
    'desc': 'Description',
}


def get_entity_full_name(entity_code: str) -> str:
    """
    Get the full name for a BIDS entity code.
    
    Args:
        entity_code: The BIDS entity code (e.g., 'sub', 'ses', 'task').
        
    Returns:
        The full name of the entity (e.g., 'Subject', 'Session', 'Task').
        If the entity code is not recognized, returns the code itself.
    """
    return BIDS_ENTITIES.get(entity_code, entity_code)


def get_all_entity_codes() -> list[str]:
    """
    Get all supported BIDS entity codes.
    
    Returns:
        List of all entity codes in the order they appear in the specification.
    """
    return list(BIDS_ENTITIES.keys())
