# Contributing to GIGANTIC

Thank you for your interest in contributing to GIGANTIC! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [AI-Native Development](#ai-native-development)
- [Submitting Changes](#submitting-changes)
- [Issue Guidelines](#issue-guidelines)

---

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

---

## How Can I Contribute?

### Reporting Bugs

Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.yml) to report bugs. Include:
- Which subproject is affected
- Steps to reproduce
- Expected vs. actual behavior
- Error messages and logs
- Your environment (OS, Python version, NextFlow version)

### Suggesting Features

Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.yml) to suggest improvements. We especially welcome ideas that improve AI-assisted workflows.

### Proposing New Subprojects

Use the [Subproject Proposal template](.github/ISSUE_TEMPLATE/subproject_proposal.yml) to propose new analysis pipelines. Good proposals include:
- Clear biological purpose
- Input/output specifications
- Integration with existing subprojects
- Computational requirements

### Contributing Code

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following our [Coding Standards](#coding-standards)
4. Test your changes
5. Commit with clear messages
6. Push to your fork
7. Open a Pull Request

---

## Development Setup

### Prerequisites

- Python >= 3.9
- NextFlow >= 21.04
- Conda or Mamba
- Git

### Getting Started

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/GIGANTIC.git
cd GIGANTIC

# Create a test project
cp -r gigantic_project-COPYME ~/test_gigantic_project/
cd ~/test_gigantic_project/

# Set up environments
bash RUN-setup_environments.sh
```

### Testing Changes

Before submitting changes:

1. **Python syntax check**: `python -m py_compile your_script.py`
2. **Shell script check**: `shellcheck your_script.sh`
3. **YAML validation**: `yamllint config.yaml`
4. **Run affected workflow**: Test with demo data if available

---

## Coding Standards

### Python Style

GIGANTIC uses a custom Python style optimized for readability in scientific contexts:

```python
# AI: Claude Code | Opus 4.5 | YYYY Month DD | Purpose: Brief description
# Human: Your Name

# Spacing inside brackets (intentionally differs from PEP 8)
species_list = [ 'Human', 'Mouse', 'Zebrafish' ]
genome_sizes = { 'Human': 3000000000, 'Mouse': 2800000000 }

# Input/output variable naming
input_proteome_fasta = open( 'proteome.fasta', 'r' )
output_annotation_results = open( 'annotations.tsv', 'w' )

# Dictionary naming convention: plural_keys___plural_values
species_names___genome_sizes = {}

# Output formatting before writing
output = species_name + '\t' + str( genome_size ) + '\n'
output_file.write( output )
```

### Key Conventions

1. **No abbreviations**: Use `calculate_sequence_similarity`, not `calc_seq_sim`
2. **AI attribution header**: Every script starts with model, date, purpose
3. **Spaces inside brackets**: `[ item ]` not `[item]`
4. **Input/output prefixes**: Variables reading/writing files use `input_` or `output_`
5. **Self-documenting headers**: Table columns include calculation methods in parentheses

### Shell Script Style

```bash
#!/bin/bash
# AI: Claude Code | Opus 4.5 | YYYY Month DD | Purpose: Brief description
# Human: Your Name

# Clear variable names
SPECIES_COUNT=67
INPUT_DIRECTORY="INPUT_user"

# Quoted variables
echo "Processing ${SPECIES_COUNT} species from ${INPUT_DIRECTORY}"
```

### NextFlow Style

```groovy
// Clear process names
process generate_phylonames {
    // Never use optional: true for required outputs
    output:
        path "phylonames.tsv", emit: phylonames  // Required output

    // Fail fast on errors
    errorStrategy 'terminate'
}
```

---

## AI-Native Development

GIGANTIC is developed using AI pair programming. When contributing:

### AI Attribution

Every AI-generated or AI-assisted script must include an attribution header:

```python
# AI: Claude Code | Opus 4.5 | 2026 February 12 | Purpose: Generate phylonames from NCBI taxonomy
# Human: Eric Edsinger
```

If you're not using AI assistance, you can omit the AI line:
```python
# Human: Your Name
# Purpose: Generate phylonames from NCBI taxonomy
```

### AI_GUIDE Files

When adding or modifying functionality:

1. **Update relevant AI_GUIDE**: Help AI assistants understand changes
2. **Document edge cases**: AI assistants need to know what can go wrong
3. **Include examples**: Concrete examples help both humans and AIs

### Session Provenance

If you're using Claude Code, you can record your development sessions:

```bash
bash RUN-record_project.sh
```

This creates documentation in `research_notebook/research_ai/` that helps future contributors understand how code was developed.

---

## Submitting Changes

### Commit Messages

Write clear, descriptive commit messages:

```
Add phyloname validation to prevent duplicate entries

- Check for duplicate genus_species in input
- Log warnings for potential typos
- Add validation to AI_GUIDE troubleshooting section

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

If AI-assisted, include the `Co-Authored-By` line.

### Pull Request Guidelines

1. **Title**: Clear, concise description (e.g., "Add NCBI update checker to phylonames")
2. **Description**: Explain what changes and why
3. **Testing**: Describe how you tested the changes
4. **Documentation**: Note any AI_GUIDE or README updates
5. **Breaking changes**: Clearly flag any breaking changes

### Review Process

1. Maintainers will review your PR
2. CI checks must pass
3. Changes may be requested
4. Once approved, maintainers will merge

---

## Issue Guidelines

### Before Opening an Issue

1. Search existing issues to avoid duplicates
2. Check the documentation
3. Try the latest version

### Good Issue Reports

- **Specific**: One issue per report
- **Reproducible**: Include steps to reproduce
- **Complete**: Include all relevant context
- **Respectful**: Maintain a collaborative tone

---

## Questions?

- Open a [Discussion](https://github.com/000specific/GIGANTIC/discussions)
- Review the [Documentation](docs/)
- Check the [AI_GUIDE files](gigantic_project-COPYME/AI_GUIDE-project.md)

---

Thank you for contributing to GIGANTIC! Your contributions help make comparative genomics more accessible to researchers everywhere.
