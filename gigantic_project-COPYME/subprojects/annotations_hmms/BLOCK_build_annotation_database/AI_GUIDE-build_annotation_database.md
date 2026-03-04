# AI_GUIDE-build_annotation_database.md (Level 2: Tool Project Guide)

**For AI Assistants**: Read `../AI_GUIDE-annotations_hmms.md` first for subproject overview and tool comparison. This guide covers the annotation database builder.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Annotations overview, tool comparison | `../AI_GUIDE-annotations_hmms.md` |
| Database builder concepts | This file |
| Running the workflow | `workflow-COPYME-build_annotation_database/ai/AI_GUIDE-build_annotation_database_workflow.md` |

## Database Builder Overview

The annotation database builder integrates outputs from all 5 annotation tool BLOCKs into a standardized database. It auto-discovers which tool outputs are available, parses each tool's native format, and produces a uniform 7-column TSV database with 24 subdirectories. It then generates statistics and 8 analytical reports.

**Key feature**: Auto-discovery of tool outputs. Users run whichever tool BLOCKs they want, and the database builder automatically detects and processes whatever is available (minimum 1 tool).

## Pipeline Scripts (16 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-discover_tool_outputs.py` | Auto-scan sibling BLOCKs for available results |
| 002 | `002_ai-python-download_go_ontology.py` | Download and cache GO ontology (go-basic.obo) |
| 003 | `003_ai-python-parse_interproscan.py` | Parse InterProScan into 19 component databases + GO |
| 004 | `004_ai-python-parse_deeploc.py` | Parse DeepLoc localization predictions |
| 005 | `005_ai-python-parse_signalp.py` | Parse SignalP signal peptide predictions |
| 006 | `006_ai-python-parse_tmbed.py` | Parse tmbed transmembrane topology |
| 007 | `007_ai-python-parse_metapredict.py` | Parse MetaPredict disorder regions |
| 008 | `008_ai-python-compile_annotation_statistics.py` | Database-wide statistics tables |
| 009 | `009_ai-python-analyze_cross_tool_consistency.py` | Cross-tool agreement analysis |
| 010 | `010_ai-python-analyze_annotation_quality.py` | Per-tool coverage and quality |
| 011 | `011_ai-python-analyze_protein_complexity.py` | Multi-domain and disorder analysis |
| 012 | `012_ai-python-analyze_functional_categories.py` | GO namespace and term analysis |
| 013 | `013_ai-python-analyze_domain_architecture.py` | TM topology and domain combinations |
| 014 | `014_ai-python-detect_annotation_outliers.py` | Statistical outlier detection |
| 015 | `015_ai-python-generate_visualization_data.py` | Heatmap and plot data |
| 016 | `016_ai-python-analyze_phylogenetic_patterns.py` | Configurable clade comparisons |

## Data Flow

```
001 discover → 002 download GO → 003-007 parse (parallel per tool)
                                       │
                                       ▼
                               008 compile statistics
                                       │
                         ┌─────────────┼──────────────┐
                         ▼             ▼              ▼
                    009-016 analyses (parallel)
```

## 24 Database Subdirectories

From InterProScan (19 + 2): pfam, gene3d, superfamily, smart, panther, cdd, prints, prositepatterns, prositeprofiles, hamap, sfld, funfam, ncbifam, pirsf, coils, mobidblite, antifam, interproscan, go

From other tools (3): deeploc, signalp, tmbed, metapredict

## Auto-Discovery Pattern

Script 001 scans `output_to_input/BLOCK_*/` (at subproject root) for available results:
- Reports which tools were found and which are missing
- Requires minimum 1 tool to proceed
- Creates a discovery manifest used by downstream scripts

## GO Ontology Auto-Download

Script 002 downloads GO from `http://purl.obolibrary.org/obo/go/go-basic.obo`:
- Caches locally for 30 days (configurable)
- Parses OBO format to create fast-lookup TSV (GO ID, name, namespace, is_obsolete)
- Used by script 003 to validate GO terms from InterProScan

## Unannotated Protein Identification

Parsers 003-007 can optionally identify proteins with zero annotations from each database and add unannotated entries to the output. This is required for downstream `annotations_X_ocl` analysis (which needs `zero` subtype annogroups).

**How it works**: Each parser compares the set of annotated proteins against the complete set of proteins from the proteome FASTA files. Proteins with no annotations get entries with the format:
- Domain_Start: `0`, Domain_Stop: `0`
- Annotation_Identifier: `unannotated_{database}-N` (global counter across all species)
- Annotation_Details: `no annotation`

**Configuration**: Set `proteomes_dir` in `nextflow.config` to enable. Set to empty string to disable.

## Configuration

Edit `workflow-COPYME-build_annotation_database/annotation_database_config.yaml`:
- `go_ontology_url`: GO OBO download URL
- `go_ontology_cache_days`: Days before re-downloading (default: 30)
- `clade_comparison`: Groups for phylogenetic pattern analysis
- `species_set_name`: Name of species set being analyzed
- `proteomes_dir`: Path to proteome FASTA directory for unannotated protein identification

Edit `workflow-COPYME-build_annotation_database/ai/nextflow.config`:
- `proteomes_dir`: Path to proteome FASTA directory (relative to workflow directory). Set to empty string to skip unannotated protein identification.
