# Xenologs vs Artifacts

**Status**: Structural (planned)

## Overview

Post-orthogroup analysis to distinguish true xenologs (genes acquired through horizontal gene transfer) from artifacts (contamination, assembly errors, annotation errors).

## Purpose

After orthogroup analysis, some genes appear in unexpected lineages. This subproject provides tools to:

1. **Identify candidates** - Genes with unusual phylogenetic distributions
2. **Evaluate evidence** - Distinguish biological signal from technical artifacts
3. **Classify outcomes** - Xenolog, contamination, assembly error, or annotation error

## Upstream Dependencies

- `orthogroups/` - Orthogroup assignments
- `trees_gene_families/` - Gene family phylogenies
- `trees_species/` - Species tree for expected distributions

## Directory Structure

```
xenologs_vs_artifacts/
├── README.md                    # This file
├── AI_GUIDE-xenologs.md         # AI assistant guidance
├── user_research/               # Personal workspace
├── output_to_input/             # Outputs for downstream subprojects
└── nf_workflow-TEMPLATE_01-*/   # NextFlow workflow (when implemented)
```

---

## Quick Start

*Coming soon - this subproject is currently structural.*

---

## Notes

- Xenologs are homologs acquired through horizontal gene transfer (HGT)
- Common in prokaryotes, less common but documented in eukaryotes
- Key challenge: distinguishing real HGT from technical artifacts
