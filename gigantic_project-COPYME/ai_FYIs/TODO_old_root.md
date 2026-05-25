# GIGANTIC - TODO

**AI**: Claude Code | Opus 4.7 | 2026 May 04
**Human**: Eric Edsinger

---

## NextFlow 26 strict-DSL surprises (must address before next BLOCK build)

**Context**: Discovered 2026-05-04 while building `subprojects/hotspots/BLOCK_self_blast/`
on a fresh `ai_gigantic_hotspots` conda env. NextFlow 26.04 (the version
bioconda installs as of May 2026) enforces a much stricter config DSL than
the version the existing GIGANTIC BLOCKs were written against. None of the
existing patterns from `orthogroups/BLOCK_orthohmm_GIGANTIC/` or
`gene_sizes/BLOCK_analyze_gene_sizes/` parse cleanly under NextFlow 26.

HiPerGator is going down for maintenance on **2026-05-06**. After the
restart, all GIGANTIC subprojects that use NextFlow should be audited and
updated for NextFlow 26 compatibility.

### The five incompatibilities

1. **Top-level `import` rejected**
   - ❌ `import org.yaml.snakeyaml.Yaml` at top of `nextflow.config`
   - ✅ Use fully qualified inline: `new org.yaml.snakeyaml.Yaml().load(...)`

2. **No `def` function definitions in `nextflow.config`**
   - ❌ `def loadConfig() { ... }` and similar function definitions
   - Error: `Variable declarations cannot be mixed with config statements`
   - ✅ Inline yaml-loading via `System.getenv()` or `-params-file <yaml>`,
     where the surrounding `RUN-workflow.sh` parses the yaml and exports
     env vars consumed by `nextflow.config`.

3. **`executor.$slurm.queueSize` per-executor scoping removed**
   - ❌ `executor { $slurm { queueSize = 200 } }` (warning: "Unrecognized config option")
   - ✅ Flat: `executor { name = '...'; queueSize = 200 }`

4. **`array = 1` directive rejected; only valid for grid executors**
   - ❌ `withLabel: 'foo' { array = isSlurm ? 100 : 1 }`
   - Error: `Process directive 'array' should be greater than 1`
   - ✅ Move `array` into `profiles.slurm.process.withLabel.foo` block;
     `RUN-workflow.sh` adds `-profile slurm` only when execution_mode == slurm.

5. **`workflow.onComplete { ... }` no longer accepted**
   - ❌ Top-level `workflow.onComplete { ... }` (DSL1 carryover)
   - ❌ Inline `onComplete { ... }` inside `workflow { ... }` block
     (NextFlow 26 strict DSL does not recognize this either)
   - ✅ Drop in-pipeline completion handler entirely; have
     `RUN-workflow.sh` print success/failure summary based on the
     NextFlow exit code.

### Working pattern (use as template for future BLOCKs)

The fully-debugged reference is:
```
subprojects/hotspots/BLOCK_self_blast/workflow-COPYME-self_blast/
├── START_HERE-user_config.yaml      (yaml is the user-facing contract)
├── RUN-workflow.sh                  (parses yaml → env vars; runs nextflow with -params-file + -profile)
├── RUN-workflow.sbatch              (SLURM wrapper around RUN-workflow.sh)
└── ai/
    ├── nextflow.config              (strict DSL — env vars + profiles only; no def/import/onComplete)
    └── main.nf                      (params from -params-file; processes use task.cpus etc.)
```

Key contract:
- **Per-run params** (paths, evalue, etc.) flow via `-params-file START_HERE-user_config.yaml`
- **Executor / resource decisions** flow via `System.getenv('GIGANTIC_*')` set in `RUN-workflow.sh`
- **SLURM-only directives** (e.g., `array = 100`) live in `profiles.slurm`

### Action items

- [ ] **Audit existing BLOCKs** for NextFlow 26 compatibility:
  - [ ] `subprojects/orthogroups/BLOCK_orthohmm/`
  - [ ] `subprojects/orthogroups/BLOCK_orthohmm_GIGANTIC/`
  - [ ] `subprojects/orthogroups/BLOCK_orthofinder/`
  - [ ] `subprojects/orthogroups/BLOCK_orthofinder_array/`
  - [ ] `subprojects/orthogroups/BLOCK_broccoli/`
  - [ ] `subprojects/gene_sizes/BLOCK_analyze_gene_sizes/`
  - [ ] Any other workflow with `nextflow.config` + `import` / `def` / `$slurm` / `onComplete` patterns
- [ ] **Decide policy**: pin NextFlow version per BLOCK (in conda env recipe),
      OR migrate all BLOCKs to NextFlow 26 patterns. Pinning is simpler short-term;
      migrating prevents future drift.
- [ ] **Document the working pattern** in a top-level `AI_GUIDE-nextflow_26_pattern.md`
      so future BLOCK authors don't re-discover the same five incompatibilities.

### Reference

Full conversation log and debugging trail: see Claude Code session notes from
2026-05-04 (hotspots subproject construction). The
`hotspots/BLOCK_self_blast/workflow-COPYME-self_blast/ai/nextflow.config`
file contains inline comments explaining each strict-DSL workaround.
