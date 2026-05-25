#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 25 | Purpose: Retroactively symlink existing per-gene-group STEP_1 AGS files into output_to_input/
# Human: Eric Edsinger

# =============================================================================
# Retroactive publish: STEP_1 OUTPUT_pipeline → output_to_input/
# =============================================================================
# The STEP_1 orchestrator now publishes each gene group's AGS to
#   ../output_to_input/gene_groups-<INSTANCE>/STEP_1-homolog_discovery/gene_group-<gg>/
# at the end of its per-gene-group nextflow run. For runs that completed
# BEFORE the publish hook was added (i.e., the SLURM jobs that were already
# in-flight at the time of the orchestrator update), the symlinks were never
# created — but the AGS files are still present at
#   gene_group-<gg>/workflow-RUN_01-rbh_rbf_homologs/OUTPUT_pipeline/16-output/16_ai-ags-*.aa
#
# This one-off script walks every gene_group-* dir, looks for completed AGS
# files, and creates the missing symlinks. Safe to re-run (uses ln -sf which
# replaces existing symlinks; mkdir -p is idempotent).
#
# Invoke from STEP_1-homolog_discovery/:
#     bash RUN-publish_existing_to_output_to_input.sh
# =============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
STEP1_DIR="${SCRIPT_DIR}"
cd "${STEP1_DIR}"

INSTANCE_NAME="$( basename "$( dirname "${STEP1_DIR}" )" )"
OTI_INSTANCE_DIR="$( cd "${STEP1_DIR}/../../output_to_input" 2>/dev/null && pwd )/${INSTANCE_NAME}"
if [ -z "$( cd "${STEP1_DIR}/../../output_to_input" 2>/dev/null && pwd )" ]; then
    OTI_INSTANCE_DIR="$( realpath -m "${STEP1_DIR}/../../output_to_input/${INSTANCE_NAME}" )"
fi

echo "================================================================================"
echo "Retroactive publish: STEP_1 AGS → output_to_input/"
echo "================================================================================"
echo "Instance:               ${INSTANCE_NAME}"
echo "STEP_1 dir:             ${STEP1_DIR}"
echo "Publishing to:          ${OTI_INSTANCE_DIR}/STEP_1-homolog_discovery/"
echo ""

published=0
missing_ags=0
already_done=0
total=0

for gg_dir in "${STEP1_DIR}"/gene_group-*; do
    [ -d "${gg_dir}" ] || continue
    total=$((total + 1))
    gg="$( basename "${gg_dir}" | sed 's/^gene_group-//' )"

    ags_glob=( "${gg_dir}/workflow-RUN_01-rbh_rbf_homologs/OUTPUT_pipeline/16-output/"16_ai-ags-*.aa )
    if [ ! -f "${ags_glob[0]}" ]; then
        missing_ags=$((missing_ags + 1))
        continue
    fi

    target="${OTI_INSTANCE_DIR}/STEP_1-homolog_discovery/gene_group-${gg}"
    if [ -L "${target}/$( basename "${ags_glob[0]}" )" ]; then
        already_done=$((already_done + 1))
        continue
    fi

    mkdir -p "${target}"
    for f in "${ags_glob[@]}"; do
        [ -f "$f" ] && ln -sf "$( realpath "$f" )" "${target}/$( basename "$f" )"
    done
    published=$((published + 1))
done

echo "Summary:"
echo "  Total gene_group dirs:    ${total}"
echo "  Published (new symlinks): ${published}"
echo "  Already had symlinks:     ${already_done}"
echo "  Missing AGS (STEP_1 not finished yet for this gene group): ${missing_ags}"
echo ""
echo "================================================================================"
echo "Done: $( date )"
echo "================================================================================"
