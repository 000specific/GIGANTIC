# TODO - one_direction_homologs

## Setup
- [ ] Create NCBI nr DIAMOND database on HPC
- [ ] Configure diamond_ncbi_nr_config.yaml with database path
- [ ] Set SLURM account/qos in RUN-workflow.sbatch
- [ ] Add DIAMOND to conda environment and test

## Testing
- [ ] Test pipeline with a small subset (2-3 species) before full run
- [ ] Verify DIAMOND output format matches expected 15-column layout
- [ ] Validate self/non-self hit identification logic
- [ ] Compare results with previous ncbi_nr_top_hits-AI output (if available)

## Production Run
- [ ] Run full pipeline with all species
- [ ] Review per-species statistics for anomalies
- [ ] Populate output_to_input/ with final results
- [ ] Update upload_to_server manifest if sharing data

## Documentation
- [ ] Record successful run parameters in user_research/
