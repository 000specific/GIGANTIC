# upload_to_server - Shared Data for GIGANTIC Server

This directory contains symlinks to files that should be shared with collaborators via the GIGANTIC server.

## How It Works

1. **Edit the manifest**: `upload_manifest.tsv` controls what gets shared
2. **Run the update script**: `bash ../RUN-update_upload_to_server.sh`
3. **Symlinks are created**: Files listed as "yes" in the manifest get symlinked here
4. **Server scans this folder**: The GIGANTIC server periodically syncs this directory

## Quick Start

```bash
# Preview what would be done
bash ../RUN-update_upload_to_server.sh --dry-run

# Create/update symlinks
bash ../RUN-update_upload_to_server.sh

# Clean and recreate all symlinks
bash ../RUN-update_upload_to_server.sh --clean
```

## Manifest Format

Edit `upload_manifest.tsv`:

```tsv
# source_path<TAB>include
nf_workflow-COPYME_01-*/OUTPUT_pipeline/3-output/*.tsv    yes
# Commented lines are ignored
```

- Lines starting with `#` are comments
- `source_path` is relative to the subproject root
- Glob patterns are supported (e.g., `*.tsv`, `*`)
- Set `include` to `yes` to share the file

## Why Symlinks?

- **Single source of truth**: Original files stay in workflow output directories
- **No duplication**: Symlinks don't copy data
- **Clear provenance**: Symlinks point back to the source
- **Easy to archive**: Use `cp -L` to dereference symlinks when archiving

## Archiving for Transfer

When you need to share files outside the server (email, download, etc.):

```bash
# Copy with dereferenced symlinks
cp -rL upload_to_server/ my_archive/

# Or use rsync
rsync -avL upload_to_server/ my_archive/
```
