# AI_GUIDE-deeploc.md (Level 2: Tool Project Guide)

**For AI Assistants**: Read `../AI_GUIDE-annotations_hmms.md` first for subproject overview and tool comparison. This guide covers DeepLoc-specific concepts.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Annotations overview, tool comparison | `../AI_GUIDE-annotations_hmms.md` |
| DeepLoc concepts | This file |
| Running the workflow | `workflow-COPYME-run_deeploc/ai/AI_GUIDE-deeploc_workflow.md` |

## DeepLoc 2.1 Overview

DeepLoc 2.1 predicts subcellular protein localization using protein language models. It classifies proteins into 10 cellular compartments (Nucleus, Cytoplasm, Extracellular, Mitochondrion, Cell membrane, Endoplasmic reticulum, Chloroplast, Golgi apparatus, Lysosome/Vacuole, Peroxisome) and predicts membrane association (Peripheral, Transmembrane, Lipid anchored, Soluble). Additionally predicts sorting signals that influence localization.

**Key feature**: Whole-protein prediction (no domain coordinates). Each protein gets localization assignment(s) with confidence scores.

**Two models available**:
- **Accurate**: ProtT5-XL-Uniref50 (3B parameters). Higher quality, slower. Needs ~32GB GPU memory.
- **Fast**: ESM1b (650M parameters). Slightly less accurate, much faster. Good for high-throughput.

**Publication**: Ødum et al. (2024) Nucleic Acids Research, gkae237

## Pipeline Scripts (2 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-validate_proteome_manifest.py` | Validate proteome manifest and file existence |
| 002 | `002_ai-bash-run_deeploc.sh` | Run DeepLoc 2.1 on each species proteome |

## DeepLoc Command

```bash
deeploc2 -f INPUT -o OUTPUT --model Fast --device cuda
```

**Device options**: `cuda` (NVIDIA GPU, recommended), `cpu` (very slow), `mps` (Apple Silicon)

## DeepLoc Output Format

CSV with columns: protein ID, localization(s), sorting signal(s), and probability scores for each of the 10 compartments. The database builder parses this into the standardized 7-column format with Start=NA, Stop=NA (whole-protein prediction).

## Configuration

Edit `workflow-COPYME-run_deeploc/START_HERE-user_config.yaml`:
- `model_type`: "Accurate" or "Fast" (default: Fast)
- `device`: "cuda", "cpu", or "mps" (default: cuda)
- `slurm_partition`: GPU partition name (default: hpg-turin)
- `slurm_gpu_type`: GPU type (default: l4)

## Resource Requirements

DeepLoc uses GPU acceleration:
- **GPU**: L4 (hpg-turin) or B200 (hpg-b200) on HiPerGator
- **CPU**: 4 cores
- **Memory**: 32 GB (Accurate model needs more GPU memory)
- **Time**: 96 hours for 70 species

## Installation

**Software location**: `BLOCK_deeploc/software/deeploc2_package/`
**License**: `BLOCK_deeploc/software/deeploc-2.1_license.txt`
**Conda environment**: `ai_gigantic_deeploc`

DeepLoc 2.1 requires:
- Academic license from DTU Health Tech: https://services.healthtech.dtu.dk/services/DeepLoc-2.1/
- Python 3.10
- PyTorch with CUDA support
- `setuptools<70` (for pkg_resources compatibility)
- `LD_LIBRARY_PATH` must include `$CONDA_PREFIX/lib` (for libstdc++ compatibility)

**Installation steps** (already completed):
1. Downloaded `deeploc-2.1.All.tar.gz` from DTU
2. Extracted to `software/deeploc2_package/`
3. `pip install .` inside `ai_gigantic_deeploc` conda env
4. `pip install "setuptools<70"` (DeepLoc uses deprecated pkg_resources)
5. RUN-workflow.sh sets `LD_LIBRARY_PATH` automatically

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `GLIBCXX_3.4.30 not found` | System libstdc++ too old | Ensure `LD_LIBRARY_PATH` includes `$CONDA_PREFIX/lib` (RUN-workflow.sh does this) |
| `No module named 'pkg_resources'` | setuptools >= 70 removed it | `pip install "setuptools<70"` |
| `invalid partition specified: gpu` | No "gpu" partition on HiPerGator | Use `hpg-turin` (L4) or `hpg-b200` (B200) |
| CUDA out of memory | Accurate model needs ~32GB VRAM | Switch to Fast model, or use B200 GPUs |
| Very slow runtime | Running on CPU instead of GPU | Set `device: "cuda"` and use GPU partition |
