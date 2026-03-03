# Build Annotation Database Workflow

Builds a standardized, integrated annotation database from all completed tool BLOCK outputs. Parses raw outputs from InterProScan, DeepLoc, SignalP, tmbed, and MetaPredict into a unified per-protein annotation format with summary statistics and comparative analyses.

## Prerequisites

- At least one tool BLOCK completed (InterProScan, DeepLoc, SignalP, tmbed, or MetaPredict)
- Tool outputs available in their respective `BLOCK_*/output_to_input/` directories
- `ai_annotation_database` conda environment created
- GO term OBO file will be downloaded automatically during pipeline

## Usage

```bash
vi build_annotation_database_config.yaml
bash RUN-workflow.sh         # Local
sbatch RUN-workflow.sbatch   # SLURM
```

## Pipeline

16 steps: discover available tool outputs, download GO term ontology, parse InterProScan results, parse DeepLoc results, parse SignalP results, parse tmbed results, parse MetaPredict results, compute per-protein statistics, compute per-species statistics, build integrated annotation table, cross-tool consistency checks, domain architecture analysis, localization summary analysis, disorder-transmembrane overlap analysis, generate annotation database files, publish to output_to_input.

## Outputs

- Integrated per-protein annotation database (TSV)
- Per-species summary statistics
- Cross-tool analysis reports
- Results published to `OUTPUT_pipeline/` and `ai/output_to_input/`
