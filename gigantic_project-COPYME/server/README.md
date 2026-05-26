<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26
Human:   Eric Edsinger
Purpose: User-facing quick start for the GIGANTIC data server (start it,
         publish data to it, reach it from a browser).
History:
  2026-05-26  Updated for unified RUN-start_server.sh driver per §29.
              Dropped references to the now-consolidated AI_GUIDE-server.md
              and AI_GUIDE-publishing.md. Fixed stale "hard copies" wording.
============================================================================ -->

# GIGANTIC Data Server

Centralized web server for sharing GIGANTIC project data with
collaborators. Serves files **via symlinks** from each subproject's
`upload_to_server/` directory through a brutalist-design web interface.
No data copying or syncing — the server follows symlinks transparently.

For full operational + publishing guidance (including the canonical-RUN
gotcha and the manifest format), see [`AI_GUIDE.md`](AI_GUIDE.md) in this
directory.

## Quick Start

### 1. Configure

Edit [`START_HERE-server_config.yaml`](START_HERE-server_config.yaml):

- `execution_mode:` — `"local"` for your laptop, `"slurm"` for an HPC
  cluster
- `port:` — server port (default 9456)
- `subproject_order:` — list of subprojects to display, in order
- For SLURM mode: also fill in `slurm.account` and `slurm.qos` (other
  `slurm.*` defaults are usually fine)

### 2. Prepare subproject data

Each subproject you want to serve must have run its
`RUN-update_upload_to_server.sh` to populate `upload_to_server/` with
symlinks. Example:

```bash
cd ../subprojects/annotations_hmms
bash RUN-update_upload_to_server.sh
```

### 3. Start the server

One canonical command — local or SLURM, driven by `execution_mode` in
the YAML:

```bash
bash RUN-start_server.sh
```

Override at the command line for one-off runs:

```bash
bash RUN-start_server.sh --execution slurm    # force slurm
bash RUN-start_server.sh --port 8888          # override port (local mode)
```

### 4. Reach the server

**Local mode**: open `http://localhost:9456/` in your browser.

**SLURM mode**: set up an SSH tunnel from your laptop to the compute
node first. Find the compute node from the SLURM log
(`logs/slurm_server_<jobid>.log`, line starting with `Node:`):

```bash
ssh -L 9456:c0700a-s2:9456 YOURLOGIN@hpg.rc.ufl.edu
# Then open http://localhost:9456/
```

Your AI assistant can construct the exact tunnel command for you after
the server starts — just ask.

## Data flow

```
Workflow outputs (OUTPUT_pipeline/) inside workflow-RUN_N-*
        |
        | step 1: subproject's RUN-update_upload_to_server.sh
        v
upload_to_server/ (symlinks to output files)
        |
        | step 2: gigantic_server.py follows the symlinks at request time
        v
Web browser
```

## Managing the server

### Check SLURM status

```bash
squeue -u $USER | grep gigantic_server
```

### Stop

- Local mode: `Ctrl+C` in the running shell
- SLURM mode: `scancel <job-id>`

### Update served data

When subproject outputs change:

1. Re-run the subproject's `RUN-update_upload_to_server.sh`
2. The server auto-refreshes its file listing every
   `refresh_interval_seconds` (default 300s) — no restart needed

### Change port

Edit `port:` in `START_HERE-server_config.yaml`, then restart. For a
one-off in local mode: `bash RUN-start_server.sh --port 8888`.

## Directory structure

```
server/
├── README.md                       # This file
├── AI_GUIDE.md                     # AI guide: operation + publishing workflow
├── START_HERE-server_config.yaml   # All config (server + slurm)
├── RUN-start_server.sh             # Unified driver (local or slurm)
├── .gitignore                      # Ignores logs/ and __pycache__/
├── ai/                             # Server code (don't touch)
│   ├── gigantic_server.py          # The server
│   ├── update_upload_to_server.py  # Shared publisher helper
│   └── static/icons/               # UI icons
└── logs/                           # SLURM logs + one-shot sbatch wrappers
```

## Configuration reference

See [`START_HERE-server_config.yaml`](START_HERE-server_config.yaml) for
all options with inline documentation. Key settings:

| Key | Purpose |
|---|---|
| `execution_mode` | `local` or `slurm` |
| `project_name` | Title shown in the web UI |
| `port` | Server port (default: 9456) |
| `refresh_interval_seconds` | How often the server re-scans `upload_to_server/` |
| `subproject_order` | Explicit allowlist + display order of subprojects |
| `show_empty_subprojects` | Whether to display listed-but-empty subprojects |
| `display_names` | Custom display names per subproject (optional) |
| `exclude_file_patterns` | Hide filenames matching these substrings |
| `slurm.account` / `slurm.qos` | Required when `execution_mode: "slurm"` |
| `slurm.partition` / `slurm.time_hours` / `slurm.memory_gb` / `slurm.cpus` | SLURM resources for the server job |
