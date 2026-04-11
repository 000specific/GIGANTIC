# GIGANTIC Data Server

Centralized web server for sharing GIGANTIC project data with collaborators. Serves files directly from subproject `upload_to_server/` directories via a brutalist-design web interface.

## Quick Start

### 1. Configure

Edit `START_HERE-server_config.yaml`:
- Set which subprojects to serve (or leave as `"all"`)
- Set the port number
- For SLURM: update account, QOS, and partition in `RUN-start_server.sbatch`

### 2. Prepare Subproject Data

Each subproject you want to serve must have:
1. An `upload_manifest.tsv` in its `upload_to_server/` directory
2. Symlinks created by running its `RUN-update_upload_to_server.sh`

Example (for annotations_hmms):
```bash
cd ../subprojects/annotations_hmms
bash RUN-update_upload_to_server.sh
```

### 3. Start the Server

**Local:**
```bash
bash RUN-start_server.sh
```

**SLURM (HPC):**
```bash
# Edit SBATCH headers in RUN-start_server.sbatch first
sbatch RUN-start_server.sbatch
```

### 4. Access

**Local:** Open `http://localhost:9456/` in your browser.

**SLURM:** Set up an SSH tunnel first:
```bash
# Check which node the job is on (from SLURM log)
ssh -L 9456:NODE_NAME:9456 your_username@your.hpc.server
# Then open http://localhost:9456/
```

## Data Flow

```
Workflow outputs (OUTPUT_pipeline/)
        |
        | (subproject's RUN-update_upload_to_server.sh)
        v
upload_to_server/ (symlinks to output files)
        |
        | (gigantic_server.py reads directly)
        v
Web browser
```

## Managing the Server

### Check Status (SLURM)
```bash
squeue -u $USER | grep gigantic
```

### Stop (SLURM)
```bash
scancel JOB_ID
```

### Update Data
When subproject outputs change:
1. Re-run the subproject's `RUN-update_upload_to_server.sh`
2. The server auto-refreshes its file listing every 5 minutes (configurable)

### Change Port
Edit `START_HERE-server_config.yaml` or use:
```bash
bash RUN-start_server.sh --port 8888
```

## Directory Structure

```
server/
├── START_HERE-server_config.yaml   # Configuration
├── RUN-start_server.sh             # Start locally
├── RUN-start_server.sbatch         # Start via SLURM
├── README.md                       # This file
├── AI_GUIDE-server.md              # AI assistant guidance
├── .gitignore                      # Ignores logs/
├── ai/                             # Server code
│   ├── gigantic_server.py          # Main server
│   └── static/icons/               # UI icons
└── logs/                           # Runtime logs
```

## Configuration Reference

See `START_HERE-server_config.yaml` for all options with inline documentation.

Key settings:
- `project_name` - Title shown in the web UI
- `port` - Server port (default: 9456)
- `subprojects` - `"all"` or explicit list of subproject names
- `display_names` - Custom display names for subprojects
- `exclude_from_display` - Hide subprojects from the UI
- `exclude_file_patterns` - Hide files matching patterns
- `slurm` - SLURM job settings (account, QOS, time, memory)
