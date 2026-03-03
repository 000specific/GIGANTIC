# GIGANTIC Conventions

This document describes the coding style and file format standards used throughout GIGANTIC.

---

## File Naming

### Scripts

AI-generated scripts follow this format:

```
NNN_ai-TOOL-detail_1-detail_2.ext
```

Examples:
- `001_ai-python-parse_sequences.py`
- `002_ai-bash-run_blast.sh`

### Output Files

```
N_ai-description.ext
```

Where N is the script number (without leading zeros in output names).

## Directory Structure

Each subproject follows a standard layout:

```
subproject/
├── user_research/               # Personal workspace
├── BLOCK_X/ or STEP_X-name/     # One or more workflow containers
│   └── workflow-COPYME-*/       # NextFlow template
│       ├── ai/                  # Internal (scripts, NextFlow pipeline)
│       │   └── scripts/         # Pipeline scripts
│       ├── INPUT_user/          # User inputs
│       └── OUTPUT_pipeline/     # Workflow outputs (N-output/ per script)
├── output_to_input/             # Single location for downstream sharing
│   └── BLOCK_X/ or STEP_X/     # Subdirectories per BLOCK/STEP
└── upload_to_server/            # External access

# AI documentation stored centrally in:
# research_notebook/research_ai/subproject-[name]/
```

## Python Code Style

### Variable Naming

- Input variables: `input_X` or `input_X_X_X`
- Output variables: `output_X` or `output_X_X_X`
- Dictionaries: `Xs___Ys` (plural keys, three underscores, plural values)
- Lists: Plural names (`sequences`, `identifiers`)

### Example

```python
input_fasta = open('sequences.fasta', 'r')
output_results = open('results.tsv', 'w')

identifiers___sequences = {}
for identifier in identifiers___sequences:
    sequence = identifiers___sequences[identifier]
```

### Spacing

Spaces inside brackets (intentionally differs from PEP 8 for readability):

```python
# GIGANTIC style
species_list = [ 'Octopus', 'Aplysia', 'Homo' ]
genome_data = { 'species': 'Octopus', 'size': 2700000000 }

# NOT standard PEP 8
species_list = ['Octopus', 'Aplysia', 'Homo']
```

## Table Formats

### Self-Documenting Headers

Column headers include descriptions:

```
Orthogroup_ID (identifier from clustering)	Conservation_Rate_Percent (conserved divided by total times 100)
```

### Delimiters

- **Between columns**: Tab (`\t`)
- **Within columns**: Comma (`,`) for lists

## NextFlow Conventions

### Template Versioning

```
workflow-COPYME-[name]/
workflow-RUN_XX-[name]/
```

### Error Handling

- Never use `optional: true` for critical outputs
- Use `errorStrategy = 'terminate'` for failures
- Scripts must `sys.exit(1)` on critical errors

## AI Attribution

Every script includes:

```python
# AI: Claude Code | Model | YYYY Month DD HH:MM | Purpose: Description
# Human: Eric Edsinger
```

---

*Documentation under development. Check back for updates.*
