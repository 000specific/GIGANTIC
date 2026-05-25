# NextFlow 26.x Compatibility Changes — Handoff Spec

> Saved 2026-05-24. Generated during the trees_gene_groups STEP_1 fix session.
> Apply this pattern to any GIGANTIC subproject whose workflows still parse
> under NextFlow ≤ 25.x but fail under NextFlow 26.x strict mode.

## Context

NextFlow 26.x uses a **strict-mode parser** that rejects two patterns common
in older GIGANTIC workflows:

1. Groovy `import` statements at the top of `nextflow.config`
   (e.g. `import org.yaml.snakeyaml.Yaml`)
2. Top-level `workflow.onComplete { ... }` blocks at the bottom of `main.nf`

If either is present, NextFlow fails at parse time. Sample error for
`workflow.onComplete`:

```
ERROR ~ Script compilation errors:
- file: main.nf
  - cause: Statements cannot be mixed with script declarations
    @ line 848, column 1.
       workflow.onComplete {
       ^
```

We do **not** want to pin NextFlow to an older version. The goal is to
make the GIGANTIC workflows parse cleanly under NextFlow 26.x while
preserving all functional behavior.

---

## Change 1 — Remove `import org.yaml.snakeyaml.Yaml` from `nextflow.config`

### Before (broken under 26.x)

```groovy
// nextflow.config
import org.yaml.snakeyaml.Yaml

def yaml = new Yaml()
def cfg  = yaml.load( new File( "START_HERE-user_config.yaml" ).text )

params {
    gene_family         = cfg.gene_family
    blast_databases_dir = cfg.inputs.blast_databases_dir
    // ...
}
```

### After (works under 26.x)

`nextflow.config` keeps only a `params { ... }` block of defaults. User
config values flow in via `-params-file` (a flat JSON file the orchestrator
writes from the YAML).

```groovy
// nextflow.config
// Parameters: defaults; -params-file overrides at run time

params {
    gene_family         = null
    blast_databases_dir = null
    rgs_genomes_dir     = null
    // ... all params keep null / default values here
}
```

### Orchestrator change (`RUN-workflow.sh`)

Adds a Python heredoc that flattens YAML into a per-instance JSON file
`.params.json` placed inside each per-instance `workflow-RUN_NN-*` directory.
The NextFlow invocation becomes:

```bash
cd "${DEST}" && nextflow run ai/main.nf \
    ${RESUME_FLAG} \
    -c ai/nextflow.config \
    -params-file .params.json
```

Python flatten pattern (called inside the orchestrator's per-instance setup):

```bash
python3 <<'PYTHON_FLATTEN'
import yaml, json
with open( 'START_HERE-user_config.yaml' ) as f:
    cfg = yaml.safe_load( f )

# Flatten nested keys (e.g. inputs.blast_databases_dir → blast_databases_dir)
flat = {}
for k, v in cfg.items():
    if isinstance( v, dict ):
        for sk, sv in v.items():
            flat[ sk ] = sv
    else:
        flat[ k ] = v

with open( '.params.json', 'w' ) as f:
    json.dump( flat, f, indent=2 )
PYTHON_FLATTEN
```

---

## Change 2 — Delete top-level `workflow.onComplete { ... }` from `main.nf`

### Before (broken under 26.x)

```groovy
// main.nf bottom

workflow {
    // ... pipeline definition ...
}

workflow.onComplete {
    println ""
    println "===================================="
    println "Pipeline Complete!"
    println "Status: ${workflow.success ? 'SUCCESS' : 'FAILED'}"
    println "Duration: ${workflow.duration}"
    // ... more println summary ...
}
```

### After (works under 26.x)

Delete the entire `workflow.onComplete { ... }` block. Replace with a
short comment placeholder:

```groovy
// main.nf bottom

workflow {
    // ... pipeline definition ...
}

// Completion summary handled by RUN-workflow.sh wrap script (orchestrator-level).
// NextFlow 26.x strict-mode parser rejects top-level workflow.onComplete blocks.
```

### Why this is safe

The `workflow.onComplete` blocks in our trees_gene_groups workflows were
**purely cosmetic** — they printed SUCCESS/FAILED status, duration, and a
directory-listing summary. The orchestrator's wrap script already:

- Captures NextFlow's exit code
- Prints SUCCESS or FAILED per instance
- Writes per-run log files to `ai/logs/`

So the println summary inside the block was redundant. If a future
workflow needs real completion logic (e.g. publishing files, sending
notifications), it should be implemented as a `process` invoked at the
end of the `workflow { ... }` block — not as a top-level
`workflow.onComplete`.

---

## Scope — Where to apply across a subproject

A GIGANTIC subproject has a tree like:

```
subprojects/<subproject>/
├── <master_COPYME>/                          ← master template
│   ├── STEP_1-*/workflow-COPYME-*/ai/{main.nf, nextflow.config}
│   ├── STEP_2-*/workflow-COPYME-*/ai/{main.nf, nextflow.config}
│   └── STEP_3-*/workflow-COPYME-*/ai/...
├── <instance_1>/                             ← per-source instance
│   ├── STEP_0-*/workflow-COPYME-*/ai/...
│   ├── STEP_1-*/workflow-COPYME-*/ai/...
│   └── STEP_2-*/workflow-COPYME-*/ai/...
└── <instance_2>/                             ← another instance
    └── ...
```

**Canonical sources** = every `workflow-COPYME-*` directory. Apply
Changes 1 and 2 to the `ai/main.nf` and `ai/nextflow.config` inside each.
Then refresh every per-source instance from its master.

**Stale state**: If the subproject was already mid-run when the old
workflows broke, you will see:

- `STEP_N/<instance>/workflow-RUN_NN-*` per-instance run dirs
- `STEP_N/slurm_logs/` from failed batches
- Possibly non-canonical `workflow-RUN_N-*` leftovers at unexpected depths

These must be deleted so the orchestrator regenerates them from the fixed
master. The orchestrator skips dirs that already exist (it does not
overwrite), so cleanup is mandatory before re-dispatch.

---

## Audit command — run before and after the fix

```bash
SUBPROJ=gigantic_project-COPYME/subprojects/<subproject>

# Find every canonical workflow source
find "$SUBPROJ" -maxdepth 4 -type d -name "workflow-COPYME-*"

# Per-source check for the two broken patterns
for D in $( find "$SUBPROJ" -maxdepth 4 -type d -name "workflow-COPYME-*" ); do
    bad=$( grep -lE "^workflow\.onComplete|^import org\.yaml|^import groovy\.yaml|new Yaml\(\)" \
                "$D"/ai/main.nf "$D"/ai/nextflow.config 2>/dev/null )
    if [ -n "$bad" ]; then
        echo "BROKEN: $D"
        echo "$bad" | sed 's/^/  /'
    else
        echo "CLEAN:  $D"
    fi
done
```

A clean subproject reports `CLEAN:` for every `workflow-COPYME-*`.

---

## Cleanup of stale RUN dirs (subproject-specific)

Example for trees_gene_groups/gene_groups-hugo_hgnc — had 2060 stale
`gene_group-*` dirs:

```bash
cd <subproject>/<instance>/STEP_1-*/

# Delete stale per-instance RUN_NN dirs (each contained broken main.nf)
ls -d gene_group-* 2>/dev/null | xargs -P 4 -I {} rm -rf {}

# Delete stale slurm_logs from failed runs
rm -rf slurm_logs

# Delete any non-canonical workflow-RUN_N-* siblings — VERIFY first they
# have no real output before deleting:
#   ls workflow-RUN_1-*/OUTPUT_pipeline workflow-RUN_1-*/work workflow-RUN_1-*/.nextflow*
# rm -rf workflow-RUN_1-*    # only if all those are empty/missing
```

---

## Refresh instance COPYMEs from master

```bash
SUBPROJ=gigantic_project-COPYME/subprojects/<subproject>

# Refresh STEP_1 main.nf + nextflow.config from master to instance
cp "$SUBPROJ/<master>/STEP_1-*/workflow-COPYME-*/ai/main.nf" \
   "$SUBPROJ/<instance>/STEP_1-*/workflow-COPYME-*/ai/main.nf"
cp "$SUBPROJ/<master>/STEP_1-*/workflow-COPYME-*/ai/nextflow.config" \
   "$SUBPROJ/<instance>/STEP_1-*/workflow-COPYME-*/ai/nextflow.config"

# Repeat for STEP_2, STEP_3, etc.
```

---

## Verification before re-dispatch

1. Re-run the audit command above — every `workflow-COPYME-*` must report `CLEAN:`.
2. Confirm SLURM queue has no leftover jobs from the broken run:
   `squeue -u $USER | grep <prefix>`
3. Confirm the orchestrator's per-instance setup will re-run
   (i.e., no leftover `gene_group-*` / `workflow-RUN_NN-*` dirs).
4. Smoke test on one instance before dispatching the full set,
   if time permits.

---

## Concrete files changed in trees_gene_groups (reference example)

- `gene_groups_COPYME/STEP_1-homolog_discovery/workflow-COPYME-rbh_rbf_homologs/ai/main.nf` — deleted lines 848–883 (`workflow.onComplete` block)
- `gene_groups_COPYME/STEP_2-phylogenetic_analysis/workflow-COPYME-phylogenetic_analysis/ai/main.nf` — deleted lines 428–441
- `gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/workflow-COPYME-hgnc_gene_groups/ai/main.nf` — deleted lines 172–193
- `gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/workflow-RUN_1-hgnc_gene_groups/ai/main.nf` — synced from fixed COPYME
- `gene_groups-hugo_hgnc/STEP_1-homolog_discovery/workflow-COPYME-rbh_rbf_homologs/ai/{main.nf,nextflow.config}` — refreshed from master
- `gene_groups-hugo_hgnc/STEP_2-phylogenetic_analysis/workflow-COPYME-phylogenetic_analysis/ai/{main.nf,nextflow.config}` — refreshed from master

All `nextflow.config` files in trees_gene_groups were already free of
`import org.yaml...` from earlier work, so only Change 2
(`workflow.onComplete` removal) was needed for that particular subproject.

**Other subprojects may still have Change 1 outstanding** — run the audit
there too.
