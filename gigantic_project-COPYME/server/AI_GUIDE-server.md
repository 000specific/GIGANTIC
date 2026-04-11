# AI_GUIDE - GIGANTIC Data Server

**For AI Assistants**: Read `../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers server-specific setup and operation.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../AI_GUIDE-project.md` |
| Server setup, configuration, operation | This file |
| Subproject data preparation | Subproject's `AI_GUIDE-*.md` |

## Purpose

The GIGANTIC data server provides HTTP access to selected pipeline outputs for collaborators. It reads from `server_data/` which contains hard copies of files from subproject `upload_to_server/` directories.

## Architecture

### Data Flow (2 Steps)

1. **Subproject manifest** (`upload_to_server/upload_manifest.tsv`) controls which outputs are shared
2. **Subproject symlinks** (`RUN-update_upload_to_server.sh`) creates symlinks in `upload_to_server/`
3. **Server** (`ai/gigantic_server.py`) reads directly from `upload_to_server/` directories

No data copying or syncing is needed. The server follows symlinks transparently.

### Key Files

| File | User Edits? | Purpose |
|------|-------------|---------|
| `START_HERE-server_config.yaml` | Yes | All server configuration |
| `RUN-start_server.sh` | No | Starts server locally |
| `RUN-start_server.sbatch` | Yes (SBATCH headers) | Starts server via SLURM |
| `ai/gigantic_server.py` | No | Server implementation |

### Configuration Parsing

The server uses a built-in YAML parser (no PyYAML dependency). It supports:
- Scalar values (`key: value`)
- Lists (`- item`)
- One-level maps (`key:\n  subkey: value`)

It does NOT support: nested maps beyond one level, multi-line strings, anchors/aliases.

## Common Operations

### Adding a New Subproject to the Server

1. Create `upload_manifest.tsv` in the subproject's `upload_to_server/` directory
2. Run the subproject's `RUN-update_upload_to_server.sh`
3. Server auto-discovers new data within 5 minutes (or restart server)

### Updating Served Data

When pipeline outputs change:
```bash
# In the subproject directory:
bash RUN-update_upload_to_server.sh
# Server auto-refreshes every 5 minutes
```

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Config file not found" | Wrong working directory | Run from `server/` directory |
| "Subprojects directory does not exist" | Wrong path | Check --subprojects-dir or directory layout |
| Empty landing page | No data in upload_to_server/ | Check subproject manifests, run their RUN-update_upload_to_server.sh |
| "Address already in use" | Port conflict | Change port in config or use `--port` |
| Files not updating | Stale symlinks | Re-run subproject's `RUN-update_upload_to_server.sh` |
| Subproject not appearing | Empty upload_to_server/ | Run subproject's `RUN-update_upload_to_server.sh` |
| SLURM job dies | Time/memory limit | Increase limits in sbatch file |

## Questions to Ask User

| Situation | Ask |
|-----------|-----|
| Setting up server for first time | "Which subprojects should be served?" |
| Adding new subproject | "Does upload_manifest.tsv exist in that subproject?" |
| Port conflict | "What port would you like to use?" |
| SLURM setup | "What are your SLURM account and QOS?" |
| Large data sync | "Some files are very large. Sync all or select specific blocks?" |

## For AI Assistants: Honesty About Mistakes

**Do not whitewash mistakes.**

When you make an error:
- Say "I was **incorrect**" or "I was **wrong**" - not "that was confusing"
- Acknowledge the actual mistake clearly
- Correct it without minimizing language

This builds trust with users who rely on accurate information.
