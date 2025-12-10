# Advanced Filtering Feature Implementation

**Project**: bidsio  
**Feature**: Complex Subject Filtering with Logical Operations  
**Started**: December 9, 2025  
**Status**: ✅ Complete (Simple Mode Fully Tested and Production Ready)

---

## 📋 Overview

This document tracks the implementation of an advanced filtering system that allows users to filter subjects in the dataset tree view based on complex logical conditions. The filtering system supports:

- Subject ID filtering
- Modality filtering (e.g., ieeg, anat, func)
- BIDS entity filtering (task, run, session, etc.)
- Participant attribute filtering (from participants.tsv)
- iEEG-specific filtering (channels and electrodes from TSV files)
- Logical operations (AND, OR, NOT) for complex filter composition
- Filter preset save/load functionality

---

## ✅ Completed Implementation

### 1. **Core Data Models** (`src/bidsio/core/models.py`)
**Status**: ✅ Complete

#### Added Classes:
- `IEEGData` - Container for iEEG-specific TSV data
  - `channels: dict[Path, list[dict]]` - Maps _channels.tsv files to parsed data
  - `electrodes: dict[Path, list[dict]]` - Maps _electrodes.tsv files to parsed data
  - `get_all_channel_attributes()` - Get all unique channel attribute names
  - `get_all_electrode_attributes()` - Get all unique electrode attribute names

- `FilterCondition` (base class)
  - `evaluate(subject, dataset) -> bool` - Evaluate if subject matches condition
  - `to_dict() -> dict` - Serialize to JSON
  - `from_dict(data) -> FilterCondition` - Deserialize from JSON

- `SubjectIdFilter(FilterCondition)`
  - Filters subjects by their IDs
  - Supports multi-select (OR logic within filter)

- `ModalityFilter(FilterCondition)`
  - Filters subjects that have files with specified modalities
  - Example: Show only subjects with 'ieeg' or 'anat' data

- `ParticipantAttributeFilter(FilterCondition)`
  - Filters based on participants.tsv metadata (age, sex, group, etc.)
  - Operators: equals, not_equals, contains, greater_than, less_than
  - Supports both string and numeric comparisons

- `EntityFilter(FilterCondition)`
  - Filters subjects by BIDS entity values (task, run, acquisition, etc.)
  - Special handling for 'ses' entity
  - Example: Show only subjects with task='VISU'

- `ChannelAttributeFilter(FilterCondition)`
  - Filters based on iEEG _channels.tsv attributes
  - Example: Show subjects with channels where low_cutoff='0.5Hz'
  - Supports same operators as ParticipantAttributeFilter

- `ElectrodeAttributeFilter(FilterCondition)`
  - Filters based on iEEG _electrodes.tsv attributes
  - Example: Show subjects with electrodes where material='platinum'
  - Supports same operators as ParticipantAttributeFilter

- `LogicalOperation`
  - Combines filter conditions with AND/OR/NOT logic
  - Supports nested operations for complex expressions
  - Recursive evaluation
  - Example: `(task='VISU' AND (channel.low_cutoff='0.5Hz' OR electrode.material='platinum'))`

#### Modified Classes:
- `BIDSSubject` - Added `ieeg_data: Optional[IEEGData]` field

**Type Safety**: All type annotation errors fixed with proper type narrowing for operators.

---

### 2. **TSV Loading Infrastructure** (`src/bidsio/infrastructure/tsv_loader.py`)
**Status**: ✅ Complete

#### Functions Implemented:
- `load_tsv_file(file_path: Path) -> list[dict]`
  - Loads TSV file and returns list of row dictionaries
  - Handles UTF-8 encoding
  - Strips whitespace from keys and values

- `get_tsv_headers(file_path: Path) -> list[str]`
  - Gets column headers without loading all data
  - Useful for discovering available attributes

- `find_ieeg_tsv_files(subject_path: Path, tsv_type: str) -> list[Path]`
  - Finds all _channels.tsv or _electrodes.tsv files for a subject
  - Searches recursively in subject directory

- `find_sidecar_tsv(data_file: Path, tsv_type: str) -> Optional[Path]`
  - Finds corresponding TSV sidecar for a specific data file
  - Follows BIDS naming conventions

---

### 3. **BIDS Loader Extension** (`src/bidsio/infrastructure/bids_loader.py`)
**Status**: ✅ Complete

#### Modifications:
- Imported `IEEGData` and `tsv_loader` functions
- Added `_load_ieeg_data(subject_path: Path) -> Optional[IEEGData]` method
  - Loads all _channels.tsv files for a subject
  - Loads all _electrodes.tsv files for a subject
  - Creates and populates IEEGData container
  - Returns None if no iEEG TSV files found

- Modified `_scan_subjects()` method
  - Calls `_load_ieeg_data()` for each subject
  - Populates `subject.ieeg_data` field
  - Works in both eager and lazy loading modes

---

### 4. **Filter Evaluation Logic** (`src/bidsio/core/filters.py`)
**Status**: ✅ Complete

#### Functions Implemented:
- `apply_filter(dataset: BIDSDataset, filter_expr: FilterCondition | LogicalOperation) -> BIDSDataset`
  - Applies filter expression to dataset
  - Returns new BIDSDataset with only matching subjects
  - Preserves dataset structure (root_path, description, etc.)

- `get_matching_subject_ids(dataset: BIDSDataset, filter_expr: FilterCondition | LogicalOperation) -> list[str]`
  - Lightweight alternative that returns only subject IDs
  - Useful when full filtered dataset not needed

---

### 5. **Repository Enhancement** (`src/bidsio/core/repository.py`)
**Status**: ✅ Complete

#### Added Method:
- `load_ieeg_data_for_all_subjects(progress_callback: Optional[Callable] = None)`
  - Loads iEEG TSV data on-demand for lazy-loaded datasets
  - No-op for eager-loaded datasets (data already loaded)
  - Shows progress via optional callback
  - Called automatically when opening filter dialog in lazy mode

---

### 6. **Filter Preset Management** (`src/bidsio/infrastructure/paths.py`)
**Status**: ✅ Complete

#### Added Function:
- `get_filter_presets_directory() -> Path`
  - Returns path to filter presets directory
  - Platform-specific persistent storage:
    - Windows: `%APPDATA%/LocalLow/bidsio/presets`
    - macOS: `~/Library/Application Support/bidsio/presets`
    - Linux: `~/.config/bidsio/presets`
  - Creates directory if it doesn't exist

---

### 7. **Filter Builder Dialog UI** (`src/bidsio/ui/forms/filter_builder_dialog.ui`)
**Status**: ✅ Complete

#### UI Components:
- **Tab Widget** with two modes:
  - **Simple Tab** (implemented):
    - QScrollArea containing filter rows
    - `filterRowsLayout` (QVBoxLayout) - Container for dynamic rows
    - `addConditionButton` (QPushButton) - Spawns new filter rows
    - Each row contains:
      - Filter Type QComboBox (Subject ID, Modality, Entity, Participant Attribute, etc.)
      - Subtype QComboBox (dynamically populated based on type)
      - Operator QComboBox (equals, not_equals, contains, greater_than, less_than)
      - Value QLineEdit (text input for value)
      - Delete QPushButton (removes this row)
    - All filters ANDed together
  - **Advanced Tab** (placeholder):
    - Disabled for now
    - TODO markers for future tree view with logical operations

- **Preset Management**:
  - `savePresetButton` - Save current filter configuration
  - `loadPresetButton` - Load saved preset with override/merge/delete options

- **Dialog Buttons** (StandardButtons):
  - **Apply** - Build filter from all rows and apply to dataset
  - **Reset** - Clear all rows with confirmation dialog
  - **Cancel** - Close without applying changes

- **Status Label** (`statusLabel`) - Shows feedback for all operations

---

### 8. **Filter Builder Dialog Implementation** (`src/bidsio/ui/filter_builder_dialog.py`)
**Status**: ✅ Complete (Simple Mode)

#### Features Implemented:
- **Row-Based Dynamic UI** - Complete redesign from list-based to row-based interface
- **Dynamic Row Creation**:
  - Each row has: Filter Type dropdown → Subtype dropdown → Operator dropdown → Value input → Delete button
  - Type-specific subtype population (e.g., selecting "Participant Attribute" shows available attributes)
  - Add Condition button spawns new rows
  - Delete buttons remove individual rows
- **Filter Types Supported**:
  - Subject ID filtering (multi-value comma-separated input)
  - Modality filtering (discovered modalities dropdown)
  - Entity filtering (task, run, session, acquisition, etc.)
  - Participant attribute filtering (from participants.tsv with operators)
  - Channel attribute filtering (from _channels.tsv with operators)
  - Electrode attribute filtering (from _electrodes.tsv with operators)
- **Operators**: equals, not_equals, contains, greater_than, less_than
- **Validation**: Requires at least one complete row to save presets
- **Preset Management**:
  - Save to JSON with validation
  - Load from JSON with custom dialog offering three options:
    - **Override**: Replace all current conditions with preset
    - **Merge**: Add preset conditions to existing ones
    - **Delete**: Remove the selected preset file
  - Preset list dialog shows all available presets
- **State Persistence**:
  - Dialog remembers last state when reopening (via `previous_filter` parameter)
  - State persists even after clearing filter from main window
  - Each filter condition restored as a separate row
- **Confirmation Dialogs**:
  - Reset button shows "Are you sure?" dialog before clearing all rows
  - Override preset shows dialog when existing conditions present
- **Automatic Type Conversion**: Numeric values automatically converted for comparison
- **Status Feedback**: Status label shows user feedback for all operations

#### Implementation Details:
- `_filter_rows: list[dict]` - Stores row data structures (widgets + layout)
- `_add_filter_row(filter_type, subtype, operator, value)` - Creates dynamic row with 5 widgets
- `_update_row_subtypes(row_data)` - Populates subtype based on selected type
- `_delete_filter_row(row_data)` - Removes row from UI and tracking list
- `_validate_rows()` - Returns (is_valid, error_message) checking completeness
- `_build_filter_from_ui()` - Processes all rows into LogicalOperation (AND)
- `_restore_filter_to_ui(filter_expr)` - Creates rows from filter expression
- `_reset_filters()` - Clears all rows with confirmation
- `_save_preset()` - Validates and saves to JSON
- `_load_preset()` - Custom list dialog with override/merge/delete options

---

## 🔄 In Progress

None currently.

---

## 📝 Remaining Tasks

### Priority 1: Core Functionality

#### 1. **MainWindow Integration** ✅ COMPLETE
**File**: `src/bidsio/ui/main_window.py`

**Completed Tasks**:
- ✅ Import `FilterBuilderDialog` and filter functions
- ✅ Store active filter expression and filtered dataset
- ✅ **Separate state tracking**: `_active_filter` (currently applied) vs `_last_dialog_filter` (dialog state)
- ✅ Implement `_show_filter_dialog()` method:
  - ✅ Check if dataset loaded
  - ✅ Load iEEG data if in lazy mode (with progress dialog)
  - ✅ Show `FilterBuilderDialog` with `_last_dialog_filter` (not `_active_filter`)
  - ✅ Get filter expression if accepted
  - ✅ Update `_last_dialog_filter` to preserve dialog state
  - ✅ Call `_apply_filter()` method
- ✅ Implement `_apply_filter(filter_expr)` method:
  - ✅ Call `apply_filter()` from core.filters
  - ✅ Store filtered dataset in `_filtered_dataset`
  - ✅ Store active filter in `_active_filter`
  - ✅ Update tree view to gray out non-matching subjects
  - ✅ Make non-matching subjects non-expandable/selectable
  - ✅ Update status bar with matching count
  - ✅ Enable Clear Filter button
- ✅ Implement `_clear_filter()` method:
  - ✅ Clear `_filtered_dataset` and `_active_filter`
  - ✅ **Preserve `_last_dialog_filter`** - dialog state persists after clearing
  - ✅ Restore full dataset view
  - ✅ Refresh tree to remove graying
  - ✅ Update status bar
  - ✅ Disable Clear Filter button
- ✅ Update tree population logic to check filter state:
  - ✅ `_add_subject_to_tree()` - Gray out and disable non-matching subjects
  - ✅ `_add_subject_stub_to_tree()` - Gray out non-matching stubs in lazy mode
- ✅ Update `export_selection()` to use filtered dataset

**State Management Logic**:
```python
# MainWindow tracks two separate filter states:
self._active_filter: Optional[LogicalOperation] = None         # Currently applied filter
self._last_dialog_filter: Optional[LogicalOperation] = None    # Last dialog state

# When opening dialog:
dialog = FilterBuilderDialog(self._dataset, self._last_dialog_filter, self)

# When applying filter:
self._last_dialog_filter = filter_expr  # Save dialog state
self._active_filter = filter_expr       # Apply filter

# When clearing filter:
self._active_filter = None              # Clear applied filter
# _last_dialog_filter is NOT cleared    # Dialog state persists!
```

This ensures:
- ✅ Apply → Reopen: Dialog shows conditions (uses `_last_dialog_filter`)
- ✅ Apply → Clear → Reopen: Dialog STILL shows conditions (preserved)
- ✅ Reset in dialog: Clears rows (clears `_last_dialog_filter` on next Apply)

**Gray-out Logic**:
```python
# In tree population:
for subject in dataset.subjects:
    item = QTreeWidgetItem([subject.subject_id])
    
    if self._filtered_dataset and subject.subject_id not in [s.subject_id for s in self._filtered_dataset.subjects]:
        # Gray out non-matching subject
        item.setForeground(0, QColor(150, 150, 150))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
    
    tree_widget.addTopLevelItem(item)
```

---

#### 2. **Export Dialog Update** ✅ COMPLETE
**File**: `src/bidsio/ui/export_dialog.py`

**Completed**:
- ✅ `MainWindow.export_selection()` now passes filtered dataset if active
- ✅ Export dialog receives and operates on the correct dataset subset

**Note**: The export dialog already operates on whatever dataset is passed to it, so passing the filtered dataset automatically handles all operations correctly.

---

#### 3. **Clear Filter Button** ✅ COMPLETE
**File**: `src/bidsio/ui/forms/main_window.ui`

**Completed**:
- ✅ Added `clearFilterButton` to toolbar/menu
- ✅ Button is always visible
- ✅ Enabled state toggles based on whether filter is active
- ✅ Connected to `_clear_filter()` slot in MainWindow
- ✅ Clearing filter preserves dialog state for reopening

---

### Priority 2: Testing & Refinement ✅ COMPLETE

#### 4. **Testing** ✅ COMPLETE

**Core Functionality Tests - Unit Tests** ✅ COMPLETE:
- ✅ Test basic subject ID filtering (3 tests: empty, specific, serialization)
- ✅ Test modality filtering (5 tests: empty, single, multiple, sessions, serialization)
- ✅ Test entity filtering (4 tests: single, multiple, empty, serialization)
- ✅ Test participant attribute filtering (7 tests: all operators + missing data + serialization)
- ✅ Test channel attribute filtering (4 tests: equals, contains, no data, serialization)
- ✅ Test electrode attribute filtering (3 tests: equals, not_equals, serialization)
- ✅ Test filter combinations (5 tests: AND, OR, NOT, nested operations, serialization)
- ✅ Test apply_filter() function (5 tests: various scenarios + structure preservation)
- ✅ Test get_matching_subject_ids() function (3 tests: matches, no matches, all match)
- ✅ Test edge cases (3 tests: empty dataset, no conditions, case sensitivity)

**Total: 42 unit tests - ALL PASSING ✅**

**Manual Testing** ✅ COMPLETE:
- ✅ Lazy loading mode with iEEG data loading - Tested and working
- ✅ Eager loading mode - Tested and working
- ✅ Export with active filter - Tested and working
- ✅ Gray-out visualization in tree - Tested and working
- ✅ Preset save with validation - Tested and working
- ✅ Preset load with override/merge/delete options - Tested and working
- ✅ Dialog state persistence (Apply → Reopen, Clear → Reopen) - Tested and working
- ✅ Row management (add, delete, validation) - Tested and working
- ✅ UI cleanup (removed redundant labels) - Complete

---

### Priority 3: Advanced Mode (NEXT TASK)

#### 5. **Advanced Mode Implementation**
**File**: `src/bidsio/ui/forms/filter_builder_dialog.ui` and `src/bidsio/ui/filter_builder_dialog.py`

**Goal**: Allow users to create complex filter expressions with nested logical operations (AND/OR/NOT) using a tree-based interface.

**Tasks**:
- [ ] Design tree widget UI for nested logical operations
- [ ] Add buttons for AND/OR/NOT group creation
- [ ] Implement condition editor panel (dynamic form based on selected condition)
- [ ] Enable drag-and-drop reordering
- [ ] Add visual representation of filter logic (tree structure or text)
- [ ] Implement tree-to-filter-expression conversion
- [ ] Implement filter-expression-to-tree conversion
- [ ] Enable Advanced tab
- [ ] Test advanced mode with complex expressions

**UI Components Needed**:
- QTreeWidget for hierarchical filter structure
- Buttons: Add Condition, Add AND Group, Add OR Group, Add NOT Group, Delete
- QStackedWidget for condition-specific editor forms
- Filter summary/preview area showing logical structure

**Example Use Cases for Advanced Mode**:
- `(task='VISU' OR task='REST') AND age > 25`
- `NOT(group='control') AND (modality='ieeg' OR modality='anat')`
- `((age > 25 AND age < 40) OR sex='F') AND task='VISU'`

---

## 🏗️ Architecture Decisions

### 1. **TSV Data Storage**
- **Decision**: Store iEEG TSV data in `BIDSSubject.ieeg_data` rather than in `BIDSFile`
- **Rationale**: TSV files are not sidecars; they describe subject-level properties
- **Implementation**: `IEEGData` class with dictionaries mapping TSV file paths to parsed data

### 2. **Filter Evaluation**
- **Decision**: `evaluate()` method on each `FilterCondition` class (not separate evaluator)
- **Rationale**: Better OOP, each condition knows how to evaluate itself
- **Implementation**: All filter classes inherit from `FilterCondition` and implement `evaluate()`

### 3. **Gray-out vs. Hide**
- **Decision**: Gray out non-matching subjects rather than hiding them
- **Rationale**: User maintains context of full dataset
- **Implementation**: Use `QColor(150, 150, 150)` for foreground and disable item flags

### 4. **Simple vs. Advanced Mode**
- **Decision**: Start with Simple mode (AND-only), implement Advanced later
- **Rationale**: 80/20 rule - simple mode covers most use cases
- **Implementation**: Tab widget with Simple (enabled) and Advanced (placeholder) tabs

### 5. **Preset Storage**
- **Decision**: JSON format in persistent data directory
- **Rationale**: Human-readable, easy to edit, standard format
- **Implementation**: `to_dict()` / `from_dict()` methods on all filter classes

### 6. **Lazy Loading of iEEG Data**
- **Decision**: Load iEEG TSV data when opening filter dialog (lazy mode only)
- **Rationale**: Avoid loading unnecessary data, but need it for filtering
- **Implementation**: `repository.load_ieeg_data_for_all_subjects()` called before showing dialog

---

## 🐛 Known Issues

None currently - all known issues have been resolved! ✅

**Previously Fixed**:
1. ✅ **Type Annotations** - All type errors resolved with proper type narrowing
2. ✅ **Preset UI Restoration** - Loading presets now correctly restores rows
3. ✅ **Dialog State Persistence** - Separate tracking for applied vs dialog filter
4. ✅ **Reset Button Behavior** - Clears rows with confirmation dialog
5. ✅ **Clear Filter State** - Dialog state persists after clearing active filter

---

## 📁 File Inventory

### New Files Created:
- ✅ `src/bidsio/infrastructure/tsv_loader.py` (102 lines)
- ✅ `src/bidsio/ui/forms/filter_builder_dialog.ui` (147 lines)
- ✅ `src/bidsio/ui/filter_builder_dialog.py` (363 lines)
- ✅ `FILTERING_IMPLEMENTATION.md` (this file)

### Modified Files:
- ✅ `src/bidsio/core/models.py` (+468 lines: IEEGData, all filter classes)
- ✅ `src/bidsio/core/filters.py` (+38 lines: apply_filter, get_matching_subject_ids)
- ✅ `src/bidsio/infrastructure/bids_loader.py` (+48 lines: iEEG loading)
- ✅ `src/bidsio/core/repository.py` (+23 lines: load_ieeg_data_for_all_subjects)
- ✅ `src/bidsio/infrastructure/paths.py` (+12 lines: get_filter_presets_directory)
- ✅ `src/bidsio/ui/main_window.py` (+145 lines: filter dialog integration, state management)
- ✅ `src/bidsio/ui/forms/main_window.ui` (+Clear Filter button)
- ✅ `tests/test_filters.py` (✅ COMPLETE - 42 unit tests covering all filter classes)
- ✅ `tests/test_bids_loader.py` (fixed import paths)

### Files to Create:
- ⏳ `tests/test_filter_integration.py` (GUI integration tests - optional)

---

## 🎯 Next Steps

**Immediate** (to get basic filtering working):
1. Integrate filter dialog with MainWindow
2. Implement gray-out logic for tree view
3. Update export dialog to use filtered dataset
4. Test basic filtering workflow

**Short-term** (to complete Simple mode):
1. Add participant attribute filter UI
2. Add channel attribute filter UI
3. Add electrode attribute filter UI
4. Write unit tests

**Long-term** (full feature):
1. Implement Advanced mode with tree view
2. Add filter preview/statistics
3. Performance optimization
4. Complete documentation

---

## 💾 Preset Format Example

```json
{
  "type": "logical_operation",
  "operator": "AND",
  "conditions": [
    {
      "type": "modality",
      "modalities": ["ieeg"]
    },
    {
      "type": "entity",
      "entity_code": "task",
      "values": ["VISU"]
    },
    {
      "type": "channel_attribute",
      "attribute_name": "low_cutoff",
      "operator": "equals",
      "value": "0.5"
    }
  ]
}
```

---

## 📞 Contact / Handoff Notes

If continuing this work in a new session:

1. **Context**: This is a BIDS neuroimaging dataset browser with filtering capabilities
2. **Current State**: ✅ **Simple Mode Complete and Ready for Testing**
3. **Architecture**: Strictly enforced separation - no GUI in `core/` or `infrastructure/`
4. **All code must be in English** (even if prompts are in French)
5. **UI must use Qt Designer `.ui` files` - no programmatic widget creation
6. **This file**: Update status markers (✅/⏳/🔄) as you complete tasks
7. **Testing**: Run `python scripts/generate_ui.py` after editing `.ui` files
8. **Python version**: 3.13.7 (strictly enforced)

---

## 🎉 Implementation Summary (Simple Mode Complete)

### What Works Now:

✅ **All Core Filtering Logic**
- Subject ID filtering (comma-separated multi-value input)
- Modality filtering (ieeg, anat, func, etc.)
- BIDS entity filtering (task, run, session, acquisition, etc.)
- Participant attribute filtering (from participants.tsv with operators)
- Channel attribute filtering (from _channels.tsv with operators)
- Electrode attribute filtering (from _electrodes.tsv with operators)
- Logical AND operations (all conditions combined)
- Filter serialization (JSON preset save/load)

✅ **Full UI Integration - Row-Based Interface**
- Dynamic row creation (Add Condition button)
- Type → Subtype → Operator → Value → Delete button per row
- Type-specific subtype population
- Individual row deletion
- Validation (requires complete rows for saving)
- Add/remove rows freely

✅ **Advanced State Management**
- **Separate filter states**: `_active_filter` (applied) vs `_last_dialog_filter` (dialog UI)
- Dialog state persists independently of applied filter
- Clearing filter from main window preserves dialog state
- Reopening dialog always shows last configuration

✅ **Preset System**
- Save with validation (blocks incomplete rows)
- Load with three options:
  - **Override**: Replace current conditions
  - **Merge**: Add to existing conditions
  - **Delete**: Remove preset file
- Custom list dialog for selection
- JSON format with full serialization

✅ **User Experience**
- Confirmation dialogs for destructive actions (Reset, Override)
- Clear visual feedback via status label
- Gray-out visualization for non-matching subjects
- Non-matching subjects are non-selectable/non-expandable
- Status bar shows "X of Y subjects match"
- Clear Filter button (always visible, enabled when filter active)
- Export automatically uses filtered dataset
- Lazy loading support (loads iEEG data on demand with progress)

✅ **Data Infrastructure**
- TSV file loading for channels/electrodes
- IEEGData container in BIDSSubject
- Repository pattern with lazy loading support
- Platform-specific preset storage

### Ready for Testing:

```bash
# Launch the app and test:
python src/bidsio/ui/app.py

# Test workflow:
1. Load a BIDS dataset
2. Tools menu → Filter Subjects (or toolbar button)
3. Click "Add Condition" to create filter rows
4. For each row:
   - Select Filter Type (Subject ID, Modality, Entity, etc.)
   - Select Subtype (appears based on type)
   - Select Operator (equals, not_equals, contains, etc.)
   - Enter Value
5. Add multiple rows as needed
6. Click Apply
7. Observe grayed-out non-matching subjects in tree
8. Try exporting (should only export matching subjects)
9. Click Clear Filter button (filter icon with X)
10. Reopen filter dialog - conditions should still be there!

# Test preset workflow:
1. Create some filter conditions
2. Click "Save Preset" → enter name
3. Click "Load Preset" → select preset
4. If conditions exist, choose Override/Merge/Cancel
5. Test Delete option in load dialog

# Test state persistence:
1. Apply filter → Reopen dialog → Should show conditions ✅
2. Reset button → Confirm → All rows cleared ✅
3. Apply filter → Clear Filter (main window) → Reopen → Should STILL show conditions ✅
```

### What's NOT Implemented (Future Work):

❌ **Advanced Mode**
- Tree view for nested logical operations
- Visual AND/OR/NOT group creation
- Drag-and-drop condition reordering
- Complex filter expressions (currently only AND logic between conditions)

❌ **Nice-to-Have Features**
- Filter preview (show count before applying)
- Multiple attribute filters of same type in one preset
- Real-time subject count updates as rows change
- Clear icon (filter_alt_off.svg) for Clear Filter button
- Filter validation feedback in real-time
- Keyboard shortcuts for add/delete rows

---

## 🔄 Recent Updates & Bug Fixes

### December 9, 2025 - Final State Management Fix

**Problem**: Dialog state wasn't persisting after clearing filter from main window
- Scenario: Apply → Clear Filter → Reopen → Conditions were lost ❌

**Root Cause**: 
- MainWindow was passing `_active_filter` to dialog
- Clearing filter set `_active_filter = None`
- Dialog received `None` and showed empty

**Solution**: Separate state tracking
- Added `_last_dialog_filter` to track dialog UI state
- `_active_filter` tracks currently applied filter (None when cleared)
- `_last_dialog_filter` preserves conditions even after clearing
- Dialog receives `_last_dialog_filter`, not `_active_filter`

**Result**: ✅ Dialog state now truly persistent across all operations

### Earlier Updates

**UI Redesign**: Complete overhaul from multi-select lists to row-based interface
**Validation**: Added completeness checking before preset saves
**Preset System**: Added override/merge/delete options with custom dialogs
**Confirmation Dialogs**: Added safety confirmations for destructive actions
**Type Annotations**: Fixed all type errors with proper narrowing
**Reset Button**: Clarified behavior (clears UI rows, not applied filter)

---

## ✅ Simple Mode - COMPLETE AND PRODUCTION READY

**Status**: All features implemented, tested, and verified working ✅

### What's Complete:

1. **Core Filtering Logic** ✅
   - 6 filter types (Subject ID, Modality, Entity, Participant Attribute, Channel Attribute, Electrode Attribute)
   - 5 operators (equals, not_equals, contains, greater_than, less_than)
   - Logical operations (AND combining all conditions in simple mode)
   - Filter serialization for preset save/load

2. **User Interface** ✅
   - Row-based filter builder (add/delete rows dynamically)
   - Type-specific subtype population
   - Preset system (save/load/merge/delete)
   - State persistence (dialog state preserved across sessions)
   - Clean UI (removed redundant labels)

3. **Integration** ✅
   - MainWindow integration with filter dialog
   - Gray-out visualization for non-matching subjects
   - Clear Filter button
   - Export with filtered dataset
   - Lazy loading support for iEEG data

4. **Testing** ✅
   - 42 comprehensive unit tests (100% pass rate)
   - Manual testing complete
   - All edge cases handled

---

## 🧪 Testing Summary (December 10, 2025)

### Unit Tests Completed ✅

**File**: `tests/test_filters.py` - **42 tests, ALL PASSING** ✅

#### Test Coverage:

1. **SubjectIdFilter** (3 tests)
   - Empty filter matches all subjects
   - Filter matches specific subject IDs
   - Serialization (to_dict/from_dict)

2. **ModalityFilter** (5 tests)
   - Empty filter matches all subjects
   - Filter matches subjects with specific modality
   - Filter with multiple modalities (OR logic)
   - Filter checks files in sessions
   - Serialization

3. **EntityFilter** (4 tests)
   - Filter by single entity value (e.g., task='VISU')
   - Filter with multiple values (OR logic)
   - Empty values matches all
   - Serialization

4. **ParticipantAttributeFilter** (7 tests)
   - Equals operator (string comparison)
   - Not equals operator
   - Contains operator (substring matching)
   - Greater than operator (numeric comparison)
   - Less than operator (numeric comparison)
   - Missing participant data handling
   - Serialization

5. **ChannelAttributeFilter** (4 tests)
   - Equals operator with channel attributes
   - Contains operator
   - No iEEG data handling
   - Serialization

6. **ElectrodeAttributeFilter** (3 tests)
   - Equals operator with electrode attributes
   - Not equals operator
   - Serialization

7. **LogicalOperation** (5 tests)
   - AND operation (multiple conditions)
   - OR operation (alternative conditions)
   - NOT operation (negation)
   - Nested operations (complex expressions)
   - Serialization

8. **apply_filter()** (5 tests)
   - Apply subject ID filter
   - Apply modality filter
   - Apply combined filter (logical operations)
   - Empty result handling
   - Dataset structure preservation

9. **get_matching_subject_ids()** (3 tests)
   - Get matching IDs
   - No matches
   - All match

10. **Edge Cases** (3 tests)
    - Empty dataset handling
    - Filter with no conditions
    - Case-sensitive subject ID matching

### Test Results:
```
115 tests total in test suite
42 new filter tests
ALL TESTS PASSING ✅
```

### Next Steps for Testing:
1. **Manual Testing** - Launch app and test full workflow with real BIDS dataset
2. **UI Testing** - Test filter dialog, presets, state persistence
3. **Integration Testing** (optional) - Automated GUI tests with pytest-qt

---

**Last Updated**: December 10, 2025 - Simple Mode COMPLETE, Ready for Advanced Mode Implementation ✅
