# Build Annotation Database Workflow

Builds a standardized, integrated annotation database from all completed tool BLOCK outputs. Parses raw outputs from InterProScan, DeepLoc, SignalP, tmbed, and MetaPredict into a unified per-protein annotation format with summary statistics and comparative analyses.

## Prerequisites

- At least one tool BLOCK completed (InterProScan, DeepLoc, SignalP, tmbed, or MetaPredict)
- Tool outputs available in `output_to_input/BLOCK_*/` directories (at subproject root)
- `ai_annotation_database` conda environment created
- GO term OBO file will be downloaded automatically during pipeline

## Usage

```bash
vi build_annotation_database_config.yaml
bash RUN-workflow.sh         # Local
sbatch RUN-workflow.sbatch   # SLURM
```

## Pipeline

16 steps: discover available tool outputs, download GO term ontology, parse InterProScan results, parse DeepLoc results, parse SignalP results, parse tmbed results, parse MetaPredict results, compile annotation statistics, analyze cross-tool consistency, analyze annotation quality, analyze protein complexity, analyze functional categories, analyze domain architecture, detect annotation outliers, generate visualization data, analyze phylogenetic patterns.

## Outputs

- Integrated per-protein annotation database (TSV)
- Per-species summary statistics
- Cross-tool analysis reports
- Results published to `OUTPUT_pipeline/` and symlinked to `output_to_input/BLOCK_build_annotation_database/`
