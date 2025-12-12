"""
Tests for filtering functionality.

These tests verify the behavior of dataset filtering operations using the
FilterCondition system with logical operations.
"""

import pytest
from pathlib import Path

from src.bidsio.core.models import (
    BIDSDataset,
    BIDSSubject,
    BIDSSession,
    BIDSFile,
    IEEGData
)
from src.bidsio.core.filters import (
    SubjectIdFilter,
    ModalityFilter,
    ParticipantAttributeFilter,
    EntityFilter,
    ChannelAttributeFilter,
    ElectrodeAttributeFilter,
    LogicalOperation,
    apply_filter,
    get_matching_subject_ids
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def basic_dataset():
    """Create a basic dataset with subjects for testing."""
    dataset = BIDSDataset(root_path=Path("/test/data"))
    dataset.subjects = [
        BIDSSubject(subject_id="01"),
        BIDSSubject(subject_id="02"),
        BIDSSubject(subject_id="03")
    ]
    return dataset


@pytest.fixture
def dataset_with_modalities():
    """Create a dataset with subjects having different modalities."""
    dataset = BIDSDataset(root_path=Path("/test/data"))
    
    # Subject 01: has ieeg data
    subject1 = BIDSSubject(subject_id="01")
    subject1.files = [
        BIDSFile(path=Path("/test/data/sub-01/ieeg/sub-01_ieeg.edf"), modality="ieeg")
    ]
    
    # Subject 02: has anat data
    subject2 = BIDSSubject(subject_id="02")
    subject2.files = [
        BIDSFile(path=Path("/test/data/sub-02/anat/sub-02_T1w.nii.gz"), modality="anat")
    ]
    
    # Subject 03: has both ieeg and anat
    subject3 = BIDSSubject(subject_id="03")
    subject3.files = [
        BIDSFile(path=Path("/test/data/sub-03/ieeg/sub-03_ieeg.edf"), modality="ieeg"),
        BIDSFile(path=Path("/test/data/sub-03/anat/sub-03_T1w.nii.gz"), modality="anat")
    ]
    
    dataset.subjects = [subject1, subject2, subject3]
    return dataset


@pytest.fixture
def dataset_with_entities():
    """Create a dataset with subjects having different BIDS entities."""
    dataset = BIDSDataset(root_path=Path("/test/data"))
    
    # Subject 01: task-VISU
    subject1 = BIDSSubject(subject_id="01")
    subject1.files = [
        BIDSFile(
            path=Path("/test/data/sub-01/ieeg/sub-01_task-VISU_ieeg.edf"),
            modality="ieeg",
            entities={"task": "VISU"}
        )
    ]
    
    # Subject 02: task-REST
    subject2 = BIDSSubject(subject_id="02")
    subject2.files = [
        BIDSFile(
            path=Path("/test/data/sub-02/ieeg/sub-02_task-REST_ieeg.edf"),
            modality="ieeg",
            entities={"task": "REST"}
        )
    ]
    
    # Subject 03: both tasks
    subject3 = BIDSSubject(subject_id="03")
    subject3.files = [
        BIDSFile(
            path=Path("/test/data/sub-03/ieeg/sub-03_task-VISU_ieeg.edf"),
            modality="ieeg",
            entities={"task": "VISU"}
        ),
        BIDSFile(
            path=Path("/test/data/sub-03/ieeg/sub-03_task-REST_ieeg.edf"),
            modality="ieeg",
            entities={"task": "REST"}
        )
    ]
    
    dataset.subjects = [subject1, subject2, subject3]
    return dataset


@pytest.fixture
def dataset_with_participants():
    """Create a dataset with participant metadata."""
    dataset = BIDSDataset(root_path=Path("/test/data"))
    dataset.dataset_files = {
        'participants.tsv': [
            {'participant_id': 'sub-01', 'age': '25', 'sex': 'M', 'group': 'control'},
            {'participant_id': 'sub-02', 'age': '30', 'sex': 'F', 'group': 'patient'},
            {'participant_id': 'sub-03', 'age': '28', 'sex': 'M', 'group': 'patient'}
        ]
    }
    # Create subjects with their metadata populated
    subject1 = BIDSSubject(subject_id="01")
    subject1.metadata = {'age': '25', 'sex': 'M', 'group': 'control'}
    
    subject2 = BIDSSubject(subject_id="02")
    subject2.metadata = {'age': '30', 'sex': 'F', 'group': 'patient'}
    
    subject3 = BIDSSubject(subject_id="03")
    subject3.metadata = {'age': '28', 'sex': 'M', 'group': 'patient'}
    
    dataset.subjects = [subject1, subject2, subject3]
    return dataset


@pytest.fixture
def dataset_with_ieeg():
    """Create a dataset with iEEG channel and electrode data."""
    dataset = BIDSDataset(root_path=Path("/test/data"))
    
    # Subject 01: has channels with low_cutoff='0.5Hz'
    subject1 = BIDSSubject(subject_id="01")
    subject1.ieeg_data = IEEGData()
    subject1.ieeg_data.channels = {
        Path("/test/data/sub-01/ieeg/sub-01_channels.tsv"): [
            {'name': 'A1', 'low_cutoff': '0.5Hz', 'high_cutoff': '200Hz'},
            {'name': 'A2', 'low_cutoff': '0.5Hz', 'high_cutoff': '200Hz'}
        ]
    }
    subject1.ieeg_data.electrodes = {
        Path("/test/data/sub-01/ieeg/sub-01_electrodes.tsv"): [
            {'name': 'A1', 'material': 'platinum'},
            {'name': 'A2', 'material': 'platinum'}
        ]
    }
    
    # Subject 02: has channels with different low_cutoff
    subject2 = BIDSSubject(subject_id="02")
    subject2.ieeg_data = IEEGData()
    subject2.ieeg_data.channels = {
        Path("/test/data/sub-02/ieeg/sub-02_channels.tsv"): [
            {'name': 'B1', 'low_cutoff': '1.0Hz', 'high_cutoff': '200Hz'}
        ]
    }
    subject2.ieeg_data.electrodes = {
        Path("/test/data/sub-02/ieeg/sub-02_electrodes.tsv"): [
            {'name': 'B1', 'material': 'gold'}
        ]
    }
    
    # Subject 03: no iEEG data
    subject3 = BIDSSubject(subject_id="03")
    
    dataset.subjects = [subject1, subject2, subject3]
    return dataset


# ============================================================================
# SubjectIdFilter Tests
# ============================================================================

class TestSubjectIdFilter:
    """Tests for SubjectIdFilter."""
    
    def test_empty_filter_matches_all(self, basic_dataset):
        """Empty subject ID should match all subjects."""
        filter_obj = SubjectIdFilter(subject_id='')
        
        for subject in basic_dataset.subjects:
            assert filter_obj.evaluate(subject)
    
    def test_filter_matches_specific_subjects(self, basic_dataset):
        """Filter should match only specified subject ID."""
        filter_obj = SubjectIdFilter(subject_id="01")
        
        assert filter_obj.evaluate(basic_dataset.subjects[0])  # "01"
        assert not filter_obj.evaluate(basic_dataset.subjects[1])  # "02"
        assert not filter_obj.evaluate(basic_dataset.subjects[2])  # "03"
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        original = SubjectIdFilter(subject_id="01")
        
        data = original.to_dict()
        assert data['type'] == 'subject_id'
        assert data['subject_id'] == "01"
        
        restored = SubjectIdFilter.from_dict(data)
        assert restored.subject_id == original.subject_id


# ============================================================================
# ModalityFilter Tests
# ============================================================================

class TestModalityFilter:
    """Tests for ModalityFilter."""
    
    def test_empty_filter_matches_all(self, dataset_with_modalities):
        """Empty modality should match all subjects."""
        filter_obj = ModalityFilter(modality='')
        
        for subject in dataset_with_modalities.subjects:
            assert filter_obj.evaluate(subject)
    
    def test_filter_matches_subjects_with_modality(self, dataset_with_modalities):
        """Filter should match subjects with specified modality."""
        filter_obj = ModalityFilter(modality="ieeg")
        
        # Subject 01: has ieeg
        assert filter_obj.evaluate(dataset_with_modalities.subjects[0])
        # Subject 02: has only anat
        assert not filter_obj.evaluate(dataset_with_modalities.subjects[1])
        # Subject 03: has both
        assert filter_obj.evaluate(dataset_with_modalities.subjects[2])
    
    def test_filter_with_session_files(self):
        """Filter should check files in sessions too."""
        dataset = BIDSDataset(root_path=Path("/test"))
        subject = BIDSSubject(subject_id="01")
        
        # Add session with files
        session = BIDSSession(session_id="pre")
        session.files = [
            BIDSFile(path=Path("/test/sub-01/ses-pre/func/sub-01_ses-pre_bold.nii.gz"), modality="func")
        ]
        subject.sessions = [session]
        
        dataset.subjects = [subject]
        
        filter_obj = ModalityFilter(modality="func")
        assert filter_obj.evaluate(subject)
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        original = ModalityFilter(modality="ieeg")
        
        data = original.to_dict()
        assert data['type'] == 'modality'
        assert data['modality'] == "ieeg"
        
        restored = ModalityFilter.from_dict(data)
        assert restored.modality == original.modality


# ============================================================================
# EntityFilter Tests
# ============================================================================

class TestEntityFilter:
    """Tests for EntityFilter."""
    
    def test_filter_by_task_equals(self, dataset_with_entities):
        """Filter by task entity with equals operator."""
        filter_obj = EntityFilter(entity_code="task", operator="equals", value="VISU")
        
        # Subject 01: has task-VISU
        assert filter_obj.evaluate(dataset_with_entities.subjects[0])
        # Subject 02: has only task-REST
        assert not filter_obj.evaluate(dataset_with_entities.subjects[1])
        # Subject 03: has both
        assert filter_obj.evaluate(dataset_with_entities.subjects[2])
    
    def test_filter_by_task_not_equals(self, dataset_with_entities):
        """Filter by task entity with not_equals operator."""
        filter_obj = EntityFilter(entity_code="task", operator="not_equals", value="VISU")
        
        # Subject 01: has only task-VISU (not_equals fails)
        assert not filter_obj.evaluate(dataset_with_entities.subjects[0])
        # Subject 02: has only task-REST (not_equals succeeds)
        assert filter_obj.evaluate(dataset_with_entities.subjects[1])
        # Subject 03: has both tasks (has REST which != VISU)
        assert filter_obj.evaluate(dataset_with_entities.subjects[2])
    
    def test_filter_by_task_contains(self, dataset_with_entities):
        """Filter by task entity with contains operator."""
        filter_obj = EntityFilter(entity_code="task", operator="contains", value="VIS")
        
        # Subject 01: has task-VISU (contains "VIS")
        assert filter_obj.evaluate(dataset_with_entities.subjects[0])
        # Subject 02: has only task-REST (doesn't contain "VIS")
        assert not filter_obj.evaluate(dataset_with_entities.subjects[1])
        # Subject 03: has both (has VISU which contains "VIS")
        assert filter_obj.evaluate(dataset_with_entities.subjects[2])
    
    def test_empty_value_matches_all(self, dataset_with_entities):
        """Empty value should match all subjects."""
        filter_obj = EntityFilter(entity_code="task", operator="equals", value="")
        
        for subject in dataset_with_entities.subjects:
            assert filter_obj.evaluate(subject)
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        original = EntityFilter(entity_code="task", operator="contains", value="VISU")
        
        data = original.to_dict()
        assert data['type'] == 'entity'
        assert data['entity_code'] == "task"
        assert data['operator'] == "contains"
        assert data['value'] == "VISU"
        
        restored = EntityFilter.from_dict(data)
        assert restored.entity_code == original.entity_code
        assert restored.operator == original.operator
        assert restored.value == original.value


# ============================================================================
# ParticipantAttributeFilter Tests
# ============================================================================

class TestParticipantAttributeFilter:
    """Tests for ParticipantAttributeFilter."""
    
    def test_equals_operator_string(self, dataset_with_participants):
        """Test equals operator with string value."""
        filter_obj = ParticipantAttributeFilter(
            attribute_name="sex",
            operator="equals",
            value="M"
        )
        
        # Subject 01: sex=M
        assert filter_obj.evaluate(dataset_with_participants.subjects[0])
        # Subject 02: sex=F
        assert not filter_obj.evaluate(dataset_with_participants.subjects[1])
        # Subject 03: sex=M
        assert filter_obj.evaluate(dataset_with_participants.subjects[2])
    
    def test_not_equals_operator(self, dataset_with_participants):
        """Test not_equals operator."""
        filter_obj = ParticipantAttributeFilter(
            attribute_name="group",
            operator="not_equals",
            value="control"
        )
        
        # Subject 01: group=control
        assert not filter_obj.evaluate(dataset_with_participants.subjects[0])
        # Subject 02: group=patient
        assert filter_obj.evaluate(dataset_with_participants.subjects[1])
        # Subject 03: group=patient
        assert filter_obj.evaluate(dataset_with_participants.subjects[2])
    
    def test_contains_operator(self, dataset_with_participants):
        """Test contains operator."""
        filter_obj = ParticipantAttributeFilter(
            attribute_name="group",
            operator="contains",
            value="pat"
        )
        
        # Subject 01: group=control (doesn't contain "pat")
        assert not filter_obj.evaluate(dataset_with_participants.subjects[0])
        # Subjects 02 and 03: group=patient (contains "pat")
        assert filter_obj.evaluate(dataset_with_participants.subjects[1])
        assert filter_obj.evaluate(dataset_with_participants.subjects[2])
    
    def test_greater_than_operator_numeric(self, dataset_with_participants):
        """Test greater_than operator with numeric values."""
        filter_obj = ParticipantAttributeFilter(
            attribute_name="age",
            operator="greater_than",
            value="27"
        )
        
        # Subject 01: age=25 (not > 27)
        assert not filter_obj.evaluate(dataset_with_participants.subjects[0])
        # Subject 02: age=30 (> 27)
        assert filter_obj.evaluate(dataset_with_participants.subjects[1])
        # Subject 03: age=28 (> 27)
        assert filter_obj.evaluate(dataset_with_participants.subjects[2])
    
    def test_less_than_operator_numeric(self, dataset_with_participants):
        """Test less_than operator with numeric values."""
        filter_obj = ParticipantAttributeFilter(
            attribute_name="age",
            operator="less_than",
            value="29"
        )
        
        # Subject 01: age=25 (< 29)
        assert filter_obj.evaluate(dataset_with_participants.subjects[0])
        # Subject 02: age=30 (not < 29)
        assert not filter_obj.evaluate(dataset_with_participants.subjects[1])
        # Subject 03: age=28 (< 29)
        assert filter_obj.evaluate(dataset_with_participants.subjects[2])
    
    def test_missing_participant_data(self, basic_dataset):
        """Test behavior when participants.tsv doesn't exist."""
        filter_obj = ParticipantAttributeFilter(
            attribute_name="age",
            operator="equals",
            value="25"
        )
        
        # Should return False for all subjects when data missing
        for subject in basic_dataset.subjects:
            assert not filter_obj.evaluate(subject)
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        original = ParticipantAttributeFilter(
            attribute_name="age",
            operator="greater_than",
            value="25"
        )
        
        data = original.to_dict()
        assert data['type'] == 'participant_attribute'
        assert data['attribute_name'] == "age"
        assert data['operator'] == "greater_than"
        assert data['value'] == "25"
        
        restored = ParticipantAttributeFilter.from_dict(data)
        assert restored.attribute_name == original.attribute_name
        assert restored.operator == original.operator
        assert restored.value == original.value


# ============================================================================
# ChannelAttributeFilter Tests
# ============================================================================

class TestChannelAttributeFilter:
    """Tests for ChannelAttributeFilter."""
    
    def test_equals_operator(self, dataset_with_ieeg):
        """Test equals operator with channel attribute."""
        filter_obj = ChannelAttributeFilter(
            attribute_name="low_cutoff",
            operator="equals",
            value="0.5Hz"
        )
        
        # Subject 01: has channels with low_cutoff='0.5Hz'
        assert filter_obj.evaluate(dataset_with_ieeg.subjects[0])
        # Subject 02: has channels with low_cutoff='1.0Hz'
        assert not filter_obj.evaluate(dataset_with_ieeg.subjects[1])
        # Subject 03: no iEEG data
        assert not filter_obj.evaluate(dataset_with_ieeg.subjects[2])
    
    def test_contains_operator(self, dataset_with_ieeg):
        """Test contains operator with channel attribute."""
        filter_obj = ChannelAttributeFilter(
            attribute_name="low_cutoff",
            operator="contains",
            value="0.5"
        )
        
        # Subject 01: has channels with low_cutoff='0.5Hz'
        assert filter_obj.evaluate(dataset_with_ieeg.subjects[0])
        # Subject 02: has channels with low_cutoff='1.0Hz'
        assert not filter_obj.evaluate(dataset_with_ieeg.subjects[1])
    
    def test_no_ieeg_data(self, basic_dataset):
        """Test behavior when subject has no iEEG data."""
        filter_obj = ChannelAttributeFilter(
            attribute_name="low_cutoff",
            operator="equals",
            value="0.5Hz"
        )
        
        # Should return False for all subjects without iEEG data
        for subject in basic_dataset.subjects:
            assert not filter_obj.evaluate(subject)
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        original = ChannelAttributeFilter(
            attribute_name="low_cutoff",
            operator="equals",
            value="0.5Hz"
        )
        
        data = original.to_dict()
        assert data['type'] == 'channel_attribute'
        assert data['attribute_name'] == "low_cutoff"
        assert data['operator'] == "equals"
        assert data['value'] == "0.5Hz"
        
        restored = ChannelAttributeFilter.from_dict(data)
        assert restored.attribute_name == original.attribute_name
        assert restored.operator == original.operator
        assert restored.value == original.value


# ============================================================================
# ElectrodeAttributeFilter Tests
# ============================================================================

class TestElectrodeAttributeFilter:
    """Tests for ElectrodeAttributeFilter."""
    
    def test_equals_operator(self, dataset_with_ieeg):
        """Test equals operator with electrode attribute."""
        filter_obj = ElectrodeAttributeFilter(
            attribute_name="material",
            operator="equals",
            value="platinum"
        )
        
        # Subject 01: has electrodes with material='platinum'
        assert filter_obj.evaluate(dataset_with_ieeg.subjects[0])
        # Subject 02: has electrodes with material='gold'
        assert not filter_obj.evaluate(dataset_with_ieeg.subjects[1])
        # Subject 03: no iEEG data
        assert not filter_obj.evaluate(dataset_with_ieeg.subjects[2])
    
    def test_not_equals_operator(self, dataset_with_ieeg):
        """Test not_equals operator with electrode attribute."""
        filter_obj = ElectrodeAttributeFilter(
            attribute_name="material",
            operator="not_equals",
            value="platinum"
        )
        
        # Subject 01: has electrodes with material='platinum'
        assert not filter_obj.evaluate(dataset_with_ieeg.subjects[0])
        # Subject 02: has electrodes with material='gold'
        assert filter_obj.evaluate(dataset_with_ieeg.subjects[1])
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        original = ElectrodeAttributeFilter(
            attribute_name="material",
            operator="equals",
            value="platinum"
        )
        
        data = original.to_dict()
        assert data['type'] == 'electrode_attribute'
        assert data['attribute_name'] == "material"
        assert data['operator'] == "equals"
        assert data['value'] == "platinum"
        
        restored = ElectrodeAttributeFilter.from_dict(data)
        assert restored.attribute_name == original.attribute_name
        assert restored.operator == original.operator
        assert restored.value == original.value


# ============================================================================
# LogicalOperation Tests
# ============================================================================

class TestLogicalOperation:
    """Tests for LogicalOperation."""
    
    def test_and_operation(self, dataset_with_entities):
        """Test AND logical operation."""
        # Create filter: task='VISU' AND subject_id='03'
        filter1 = EntityFilter(entity_code="task", operator="equals", value="VISU")
        filter2 = SubjectIdFilter(subject_id="03")
        
        and_op = LogicalOperation(operator="AND", conditions=[filter1, filter2])
        
        # Subject 01: has VISU but not id=03
        assert not and_op.evaluate(dataset_with_entities.subjects[0])
        # Subject 02: doesn't have VISU
        assert not and_op.evaluate(dataset_with_entities.subjects[1])
        # Subject 03: has VISU AND id=03
        assert and_op.evaluate(dataset_with_entities.subjects[2])
    
    def test_or_operation(self, dataset_with_entities):
        """Test OR logical operation."""
        # Create filter: subject_id='01' OR subject_id='02'
        filter1 = SubjectIdFilter(subject_id="01")
        filter2 = SubjectIdFilter(subject_id="02")
        
        or_op = LogicalOperation(operator="OR", conditions=[filter1, filter2])
        
        # Subject 01: matches first condition
        assert or_op.evaluate(dataset_with_entities.subjects[0])
        # Subject 02: matches second condition
        assert or_op.evaluate(dataset_with_entities.subjects[1])
        # Subject 03: matches neither
        assert not or_op.evaluate(dataset_with_entities.subjects[2])
    
    def test_not_operation(self, basic_dataset):
        """Test NOT logical operation."""
        # Create filter: NOT(subject_id='02')
        filter1 = SubjectIdFilter(subject_id="02")
        
        not_op = LogicalOperation(operator="NOT", conditions=[filter1])
        
        # Subject 01: not id=02
        assert not_op.evaluate(basic_dataset.subjects[0])
        # Subject 02: is id=02 (NOT inverts it)
        assert not not_op.evaluate(basic_dataset.subjects[1])
        # Subject 03: not id=02
        assert not_op.evaluate(basic_dataset.subjects[2])
    
    def test_nested_operations(self, dataset_with_modalities):
        """Test nested logical operations."""
        # Create filter: (modality='ieeg' OR modality='anat') AND (subject_id='01' OR subject_id='03')
        filter1 = ModalityFilter(modality="ieeg")
        filter2 = ModalityFilter(modality="anat")
        or_op = LogicalOperation(operator="OR", conditions=[filter1, filter2])
        
        filter3 = SubjectIdFilter(subject_id="01")
        filter4 = SubjectIdFilter(subject_id="03")
        or_op2 = LogicalOperation(operator="OR", conditions=[filter3, filter4])
        and_op = LogicalOperation(operator="AND", conditions=[or_op, or_op2])
        
        # Subject 01: has ieeg AND id is 01
        assert and_op.evaluate(dataset_with_modalities.subjects[0])
        # Subject 02: has anat but id is 02
        assert not and_op.evaluate(dataset_with_modalities.subjects[1])
        # Subject 03: has both AND id is 03
        assert and_op.evaluate(dataset_with_modalities.subjects[2])
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        filter1 = SubjectIdFilter(subject_id="01")
        filter2 = ModalityFilter(modality="ieeg")
        
        original = LogicalOperation(operator="AND", conditions=[filter1, filter2])
        
        data = original.to_dict()
        assert data['type'] == 'logical_operation'
        assert data['operator'] == 'AND'
        assert len(data['conditions']) == 2
        
        restored = LogicalOperation.from_dict(data)
        assert restored.operator == original.operator
        assert len(restored.conditions) == 2


# ============================================================================
# apply_filter() Tests
# ============================================================================

class TestApplyFilter:
    """Tests for apply_filter function."""
    
    def test_apply_subject_id_filter(self, basic_dataset):
        """Test applying subject ID filter to dataset."""
        filter_obj = SubjectIdFilter(subject_id="01")
        
        result = apply_filter(basic_dataset, filter_obj)
        
        assert len(result.subjects) == 1
        assert result.subjects[0].subject_id == "01"
        assert result.root_path == basic_dataset.root_path
    
    def test_apply_modality_filter(self, dataset_with_modalities):
        """Test applying modality filter to dataset."""
        filter_obj = ModalityFilter(modality="ieeg")
        
        result = apply_filter(dataset_with_modalities, filter_obj)
        
        assert len(result.subjects) == 2  # Subjects 01 and 03 have ieeg
        assert result.subjects[0].subject_id == "01"
        assert result.subjects[1].subject_id == "03"
    
    def test_apply_combined_filter(self, dataset_with_entities):
        """Test applying combined filter (AND operation)."""
        filter1 = EntityFilter(entity_code="task", operator="equals", value="VISU")
        filter2 = SubjectIdFilter(subject_id="01")
        filter3 = SubjectIdFilter(subject_id="03")
        or_op = LogicalOperation(operator="OR", conditions=[filter2, filter3])
        
        combined = LogicalOperation(operator="AND", conditions=[filter1, or_op])
        
        result = apply_filter(dataset_with_entities, combined)
        
        assert len(result.subjects) == 2  # Subjects 01 and 03 have VISU
        assert result.subjects[0].subject_id == "01"
        assert result.subjects[1].subject_id == "03"
    
    def test_empty_result(self, basic_dataset):
        """Test filter that matches no subjects."""
        filter_obj = SubjectIdFilter(subject_id="99")
        
        result = apply_filter(basic_dataset, filter_obj)
        
        assert len(result.subjects) == 0
        assert result.root_path == basic_dataset.root_path
    
    def test_preserves_dataset_structure(self, dataset_with_participants):
        """Test that filtered dataset preserves original structure."""
        filter_obj = SubjectIdFilter(subject_id="01")
        
        result = apply_filter(dataset_with_participants, filter_obj)
        
        assert result.root_path == dataset_with_participants.root_path
        assert result.dataset_description == dataset_with_participants.dataset_description
        assert result.dataset_files == dataset_with_participants.dataset_files


# ============================================================================
# get_matching_subject_ids() Tests
# ============================================================================

class TestGetMatchingSubjectIds:
    """Tests for get_matching_subject_ids function."""
    
    def test_get_matching_ids(self, basic_dataset):
        """Test getting matching subject IDs."""
        filter1 = SubjectIdFilter(subject_id="01")
        filter2 = SubjectIdFilter(subject_id="03")
        or_op = LogicalOperation(operator="OR", conditions=[filter1, filter2])
        
        result = get_matching_subject_ids(basic_dataset, or_op)
        
        assert sorted(result) == ["01", "03"]
    
    def test_no_matches(self, basic_dataset):
        """Test with filter that matches no subjects."""
        filter_obj = SubjectIdFilter(subject_id="99")
        
        result = get_matching_subject_ids(basic_dataset, filter_obj)
        
        assert result == []
    
    def test_all_match(self, basic_dataset):
        """Test with filter that matches all subjects."""
        filter1 = SubjectIdFilter(subject_id="01")
        filter2 = SubjectIdFilter(subject_id="02")
        filter3 = SubjectIdFilter(subject_id="03")
        or_op = LogicalOperation(operator="OR", conditions=[filter1, filter2, filter3])
        
        result = get_matching_subject_ids(basic_dataset, or_op)
        
        assert len(result) == 3
        assert "01" in result
        assert "02" in result
        assert "03" in result


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_dataset(self):
        """Test filtering empty dataset."""
        dataset = BIDSDataset(root_path=Path("/test"))
        dataset.subjects = []
        
        filter_obj = SubjectIdFilter(subject_id="01")
        result = apply_filter(dataset, filter_obj)
        
        assert len(result.subjects) == 0
    
    def test_filter_with_no_conditions(self, basic_dataset):
        """Test logical operation with empty conditions list."""
        and_op = LogicalOperation(operator="AND", conditions=[])
        
        # Empty AND should match all (identity element)
        for subject in basic_dataset.subjects:
            assert and_op.evaluate(subject)
    
    def test_case_sensitivity_subject_ids(self):
        """Test that subject ID matching is case-sensitive."""
        dataset = BIDSDataset(root_path=Path("/test"))
        dataset.subjects = [BIDSSubject(subject_id="ABC")]
        
        filter_obj = SubjectIdFilter(subject_id="abc")
        result = apply_filter(dataset, filter_obj)
        
        assert len(result.subjects) == 0  # Case-sensitive, no match
