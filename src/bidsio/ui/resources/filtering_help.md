# Filtering Subjects - User Guide

The Filter Subjects feature allows you to show only subjects that match specific criteria. Non-matching subjects are grayed out in the tree view.

---

## 🎯 Two Modes

### Simple Mode
- **Best for**: Straightforward filtering with multiple conditions combined with AND logic
- **All conditions must match** for a subject to be included

### Advanced Mode
- **Best for**: Complex filters with OR and NOT logic
- **Build nested expressions** with full logical control

💡 **Tip**: Start in Simple mode. Switch to Advanced when you need OR or NOT operations.

---

## 📝 Simple Mode

### How to Use

1. **Click "Add Condition"** to create a new filter row
2. **Select Filter Type** from the dropdown:
   - **Subject ID**: Filter by subject identifier (e.g., "01")
   - **Modality**: Filter by data type (e.g., ieeg, anat, func)
   - **Entity**: Filter by BIDS entities (task, run, session, etc.)
   - **Subject Attribute**: Filter by participant metadata (age, sex, group)
   - **Channel Attribute**: Filter by iEEG channel properties
   - **Electrode Attribute**: Filter by iEEG electrode properties
3. **Choose options** based on the filter type (subtype, operator, value)
4. **Add more rows** as needed - all conditions are ANDed together
5. **Click Apply** to filter the dataset

### Example: Show subjects with task='VISU' AND age > 25

1. Add row: **Entity** | task | equals | VISU
2. Add row: **Subject Attribute** | age | greater than | 25
3. Click **Apply**

### Operators

- **equals**: Exact match
- **not equals**: Does not match
- **contains**: Substring match (for text)
- **greater than**: Numeric comparison (for numbers)
- **less than**: Numeric comparison (for numbers)

### Tips

- **Delete rows** with the trash icon button
- **Reset** clears all rows (asks for confirmation)
- **Save Preset** to reuse filters later
- Clearing the filter in the main window **preserves your conditions** for next time

---

## 🌳 Advanced Mode

### How to Use

1. **Start with a logical group**:
   - Click **Add Group** → Choose **AND**, **OR**, or **NOT**
   - AND: All child conditions must match
   - OR: At least one child condition must match
   - NOT: Child condition must NOT match (max 1 child)

2. **Add conditions** to the group:
   - Select a group node
   - Click **Add Condition** → Choose filter type
   - The condition is added as a child

3. **Build complex expressions**:
   - Nest groups inside groups for complex logic
   - Mix AND, OR, and NOT operations
   - Use the editor panel to modify selected items

### Example: (task='VISU' OR task='REST') AND age > 25

1. Add Group: **AND** (root)
2. With AND selected, Add Group: **OR** (child of AND)
3. With OR selected, Add Condition: **Entity** | task | equals | VISU
4. With OR selected, Add Condition: **Entity** | task | equals | REST
5. With AND selected (root), Add Condition: **Subject Attribute** | age | greater than | 25
6. Click **Apply**

### Tree Operations

#### Toolbar
- **Add Condition** (Ctrl+N): Add a new filter condition
- **Add Group** (Ctrl+G): Add AND/OR/NOT logical group
- **Delete** (Delete key): Remove selected item
- **Move Up/Down** (Ctrl+↑/↓): Reorder within parent
- **Cut/Copy/Paste** (Ctrl+X/C/V): Clipboard operations
- **Duplicate** (Ctrl+D): Clone item and insert as sibling

#### Right-Click Menu
All toolbar operations are also available via right-click context menu.

### Editor Panel

When you select a tree item, the editor panel shows:
- **Logical Operation**: Radio buttons to change AND/OR/NOT
- **Condition Details**: Type-specific form to edit filter parameters

Changes update **immediately** - no Apply button needed in the editor.

### Tips

- **NOT groups accept only 1 child** - enforced automatically
- **Cut items** show in italic/gray until pasted elsewhere
- **Deep copy**: Paste copies entire subtrees with all children
- **Add to groups**: Select a logical operation to add children
- **Add as siblings**: Select a condition to add at same level

---

## 💾 Preset Management

### Save Preset

1. Configure your filter (Simple or Advanced mode)
2. Click **Save Preset**
3. Enter a name
4. Preset is saved with mode information

### Load Preset

1. Click **Load Preset**
2. Select from list
3. Choose action:
   - **Override**: Replace current filter
   - **Merge**: Add to existing filter
   - **Cancel**: Don't load
4. Can also **Delete** presets from this dialog

### Preset Storage

Presets are stored on your computer:
- **Windows**: `%APPDATA%/LocalLow/bidsio/presets`
- **macOS**: `~/Library/Application Support/bidsio/presets`
- **Linux**: `~/.config/bidsio/presets`

You can share preset files (`.json`) with teammates!

---

## 🔄 Mode Switching

### Simple → Advanced
- **Always allowed**
- Converts flat AND list to tree structure
- No data loss

### Advanced → Simple
- **Requires simple structure**:
  - Single AND group at root
  - No OR or NOT operations
  - No nested groups
- Warning shown if conversion would lose logic
- **Tip**: Simplify in Advanced mode first if needed

---

## 🎨 Visual Feedback

### In the Main Window
- **Grayed out subjects**: Don't match the filter
- **Normal subjects**: Match the filter
- **Status bar**: Shows "X of Y subjects match"

### Clear Filter Button
- **Toolbar button** (filter icon with X)
- Always visible
- Enabled when filter is active
- **Clearing preserves your filter** - reopen dialog to see conditions!

---

## 📤 Export Integration

When you **Export** with an active filter:
- Only **matching subjects** are exported
- Grayed out subjects are excluded
- Export dialog operates on filtered dataset

---

## 🧪 Filter Examples

### Simple Mode Examples

**Example 1**: iEEG subjects only
- Modality | ieeg

**Example 2**: Female subjects in patient group
- Subject Attribute | sex | equals | F
- Subject Attribute | group | equals | patient

**Example 3**: Task with specific channel properties
- Entity | task | equals | VISU
- Channel Attribute | low_cutoff | equals | 0.5Hz

### Advanced Mode Examples

**Example 1**: Multiple tasks (OR logic)
```
OR
├─ Entity | task | equals | VISU
└─ Entity | task | equals | REST
```

**Example 2**: Age range with NOT
```
AND
├─ Subject Attribute | age | greater than | 25
├─ Subject Attribute | age | less than | 40
└─ NOT
   └─ Subject Attribute | group | equals | control
```

**Example 3**: Complex nested expression
```
AND
├─ OR
│  ├─ Modality | ieeg
│  └─ Modality | anat
├─ Entity | task | equals | VISU
└─ Subject Attribute | age | greater than | 30
```

---

## 💡 Tips & Tricks

1. **Start Simple**: Use Simple mode for most filters
2. **Preview First**: Check subject count in status bar before exporting
3. **Save Often**: Save useful filters as presets
4. **Share Presets**: JSON files can be shared with colleagues
5. **Keyboard Shortcuts**: Master Ctrl+N, Ctrl+G, Delete, Ctrl+C/V/X in Advanced mode
6. **Clear, Don't Reset**: Clearing from main window preserves dialog state
7. **iEEG Data**: First filter opening loads iEEG TSV data (may take a moment)

---

## ❓ FAQ

**Q: What's the difference between Clear and Reset?**
- **Clear** (main window): Removes active filter, shows all subjects, **preserves dialog state**
- **Reset** (dialog): Clears dialog rows/tree, **doesn't affect applied filter**

**Q: Can I combine multiple Subject IDs?**
- **Simple mode**: No, single value per row. Use multiple rows with different filters.
- **Advanced mode**: Yes! Use OR group with multiple Subject ID conditions.

**Q: Why can't I switch to Simple mode?**
- Your Advanced filter uses OR, NOT, or nested groups
- Solution: Simplify in Advanced mode or stay in Advanced mode

**Q: Do presets work across modes?**
- Yes! Presets remember their mode
- Loading switches dialog to correct mode automatically
- Advanced presets can't be loaded in Simple mode if complex

**Q: Where are my presets stored?**
- See "Preset Storage" section above
- Platform-specific persistent location
- JSON format, human-readable

---

## 🐛 Known Limitations

1. **Simple mode**: Cannot express OR or NOT logic
2. **NOT groups**: Limited to 1 child (by design)
3. **Large datasets**: Filtering >1000 subjects may take a moment
4. **iEEG TSV loading**: First filter dialog opening in lazy mode loads all iEEG data

---

**Need more help?** Check the project documentation or contact support.
