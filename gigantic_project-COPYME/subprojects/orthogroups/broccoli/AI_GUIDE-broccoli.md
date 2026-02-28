# AI Guide: Broccoli Tool

**For AI Assistants**: Read `../AI_GUIDE-orthogroups.md` first for orthogroups overview and concepts. This guide covers Broccoli-specific usage.

**Location**: `gigantic_project-COPYME/subprojects/orthogroups/broccoli/`

**Status**: Skeleton - workflow pending implementation.

---

## CRITICAL: Surface Discrepancies - No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| Orthogroups concepts | `../AI_GUIDE-orthogroups.md` |
| Running Broccoli workflow | `workflow-COPYME-*/ai/AI_GUIDE-broccoli_workflow.md` (pending) |

---

## What Broccoli Does

**Purpose**: Infer orthologous groups using a mixed phylogeny-network approach. Broccoli combines ultra-fast phylogenetic analyses with network-based label propagation to identify orthogroups. It also detects chimeric proteins from gene-fusion events.

**Input**: Directory of proteome FASTA files from genomesDB

**Output**:
- `orthologous_groups.txt` - Orthogroup assignments (OG ID + member proteins)
- `table_OGs_protein_counts.txt` - Species-by-orthogroup count matrix
- `table_OGs_protein_names.txt` - Species-by-orthogroup name matrix
- `chimeric_proteins.txt` - Gene-fusion detection results
- `orthologous_pairs.txt` - Pairwise ortholog relationships

**When to use**: When you want phylogeny-aware orthology that also detects chimeric/fusion proteins. Faster than full phylogenetic methods but more sensitive than pure sequence-similarity approaches.

---

## Broccoli Pipeline Steps

| Step | Directory | Description |
|------|-----------|-------------|
| 1 | `dir_step1/` | Kmer clustering of proteome sequences |
| 2 | `dir_step2/` | Diamond similarity search + phylogenetic tree construction (NJ/ME/ML) |
| 3 | `dir_step3/` | Network analysis: orthogroup identification via label propagation |
| 4 | `dir_step4/` | Pairwise ortholog relationship extraction |

Main results are in `dir_step3/` (orthogroups) and `dir_step4/` (ortholog pairs).

---

## Key Command-Line Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-dir` | (required) | Input directory of proteome FASTA files |
| `-ext` | `.fasta` | Extension of proteome files |
| `-threads` | 1 | Number of threads |
| `-e_value` | 0.001 | E-value for Diamond similarity search |
| `-nb_hits` | 6 | Max hits per species in Diamond search |
| `-phylogenies` | `nj` | Tree method: `nj` (neighbor joining), `me` (minimum evolution), `ml` (maximum likelihood) |
| `-steps` | `1,2,3,4` | Which steps to run (comma-separated) |

---

## Dependencies

- **Python 3.6+**
- **ete3** library (phylogenetic tree toolkit)
- **Diamond** 0.9.30+ (sequence similarity search)
- **FastTree** 2.1.11+ (**single-thread version only**)

**Important**: Broccoli requires the single-thread version of FastTree, not the OpenMP multi-threaded version.

---

## Directory Structure

```
broccoli/
├── README.md                    # Human documentation
├── AI_GUIDE-broccoli.md         # THIS FILE
│
├── user_research/               # Personal workspace
│
├── output_to_input/             # Outputs for downstream subprojects
│
├── upload_to_server/            # Server sharing
│
└── workflow-COPYME-run_broccoli/  # Workflow template (pending implementation)
    ├── INPUT_user/
    ├── OUTPUT_pipeline/
    └── ai/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/broccoli_config.yaml` | Configuration (pending) | **YES** |
| `workflow-*/RUN-broccoli.sbatch` | SLURM account/qos (pending) | **YES** (SLURM) |
| `workflow-*/INPUT_user/` | Proteome FASTAs | **YES** |
| `output_to_input/` | Output for downstream | No |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "ete3 not found" | Library not installed | Install ete3 in conda environment |
| "diamond not found" | Diamond not in PATH | Set `-path_diamond` or add to PATH |
| "fasttree not found" | FastTree not in PATH | Set `-path_fasttree` or add to PATH |
| Wrong FastTree version | Using OpenMP version | Install single-thread FastTree |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting fresh | "Which species set are you using (e.g., species71)?" |
| Choosing tool | "Do you need chimeric protein detection? (Broccoli unique feature)" |
| Performance | "How many threads should Broccoli use?" |
| Tree method | "NJ (fast, default), ME, or ML for phylogenetic step?" |

---

## Implementation Notes

When implementing the Broccoli workflow, consider:

1. **File extension**: GIGANTIC proteomes use `.aa` extension, so `-ext .aa` will be needed
2. **Header format**: Broccoli may need short headers (like OrthoHMM) - verify with test run
3. **Output integration**: Map Broccoli orthogroup IDs back to GIGANTIC identifiers
4. **dir_step1-4 directories**: Broccoli creates these in the working directory; the workflow should manage their placement in OUTPUT_pipeline/
