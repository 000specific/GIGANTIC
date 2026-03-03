#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Run SignalP 6 signal peptide prediction on a single species proteome
# Human: Eric Edsinger

# =============================================================================
# 002_ai-bash-run_signalp.sh
# =============================================================================
#
# Runs SignalP 6 signal peptide prediction on a single species proteome FASTA
# file. Parses the SignalP output to create a filtered TSV containing only
# proteins with predicted signal peptides, including cleavage site positions
# and probability scores.
#
# Input:
#   --input-fasta: Path to a single species proteome FASTA file (.aa)
#   --output-dir: Directory for output files
#   --phyloname: GIGANTIC phyloname for the species (used in output naming)
#   --organism-type: Organism group for SignalP (eukarya, gram_positive, gram_negative, archaea)
#   --mode: Prediction mode (slow for accuracy, fast for speed)
#
# Output:
#   {phyloname}_signalp_predictions.tsv - Filtered signal peptide predictions
#       Only includes proteins with predicted signal peptides (not OTHER)
#       Columns: Protein_Identifier, Prediction, Cleavage_Site_Position, SP_Probability
#   2_ai-log-run_signalp_{phyloname}.log - Execution log
#
# Prerequisites:
#   - SignalP 6 installed and available as signalp6
#   - conda environment ai_gigantic_signalp activated
#
# Usage:
#   bash 002_ai-bash-run_signalp.sh \
#       --input-fasta /path/to/species.aa \
#       --output-dir . \
#       --phyloname Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens \
#       --organism-type eukarya \
#       --mode slow
#
# =============================================================================

set -e  # Exit on error

# =============================================================================
# CONFIGURATION
# =============================================================================

# Default values
INPUT_FASTA=""
OUTPUT_DIR="."
PHYLONAME=""
ORGANISM_TYPE="eukarya"
MODE="slow"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input-fasta)
            INPUT_FASTA="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --phyloname)
            PHYLONAME="$2"
            shift 2
            ;;
        --organism-type)
            ORGANISM_TYPE="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# LOGGING SETUP
# =============================================================================

LOG_DIR="${OUTPUT_DIR}"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/2_ai-log-run_signalp_${PHYLONAME}.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# =============================================================================
# VALIDATE INPUTS
# =============================================================================

log_message "========================================================================"
log_message "Script 002: Run SignalP Signal Peptide Prediction"
log_message "========================================================================"

# Validate required arguments
if [ -z "${INPUT_FASTA}" ]; then
    log_message "CRITICAL ERROR: --input-fasta is required but not provided!"
    exit 1
fi

if [ -z "${PHYLONAME}" ]; then
    log_message "CRITICAL ERROR: --phyloname is required but not provided!"
    exit 1
fi

# Validate input file exists
if [ ! -f "${INPUT_FASTA}" ]; then
    log_message "CRITICAL ERROR: Input FASTA file does not exist!"
    log_message "Expected path: ${INPUT_FASTA}"
    log_message "Ensure the proteome file is accessible from the execution directory."
    exit 1
fi

# Validate input file is not empty
if [ ! -s "${INPUT_FASTA}" ]; then
    log_message "CRITICAL ERROR: Input FASTA file is empty!"
    log_message "Path: ${INPUT_FASTA}"
    exit 1
fi

# Check if signalp6 is available
if ! command -v signalp6 &> /dev/null; then
    log_message "CRITICAL ERROR: signalp6 command not found!"
    log_message "Ensure SignalP 6 is installed and the ai_gigantic_signalp conda environment is activated."
    log_message "SignalP 6 requires a license from DTU Health Tech: https://services.healthtech.dtu.dk/services/SignalP-6.0/"
    exit 1
fi

# Validate organism type
case "${ORGANISM_TYPE}" in
    eukarya|gram_positive|gram_negative|archaea)
        ;;
    *)
        log_message "CRITICAL ERROR: Invalid organism type '${ORGANISM_TYPE}'!"
        log_message "Valid options: eukarya, gram_positive, gram_negative, archaea"
        log_message "For GIGANTIC species (eukaryotic proteomes), use 'eukarya'."
        exit 1
        ;;
esac

# Validate mode
case "${MODE}" in
    slow|fast)
        ;;
    *)
        log_message "CRITICAL ERROR: Invalid mode '${MODE}'!"
        log_message "Valid options: slow (higher accuracy), fast (speed)"
        exit 1
        ;;
esac

log_message "Input FASTA: ${INPUT_FASTA}"
log_message "Output directory: ${OUTPUT_DIR}"
log_message "Phyloname: ${PHYLONAME}"
log_message "Organism type: ${ORGANISM_TYPE}"
log_message "Mode: ${MODE}"

# Count input sequences
SEQUENCE_COUNT=$(grep -c '^>' "${INPUT_FASTA}")
log_message "Input sequences: ${SEQUENCE_COUNT}"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# =============================================================================
# OUTPUT FILE PATHS
# =============================================================================

SIGNALP_RAW_DIR="${OUTPUT_DIR}/signalp_raw_output_${PHYLONAME}"
OUTPUT_PREDICTIONS="${OUTPUT_DIR}/${PHYLONAME}_signalp_predictions.tsv"

# =============================================================================
# RUN SIGNALP 6
# =============================================================================

log_message ""
log_message "Running SignalP 6 signal peptide prediction..."
log_message "This predicts signal peptides and cleavage sites for each protein."
log_message ""

mkdir -p "${SIGNALP_RAW_DIR}"

signalp6 \
    --fastafile "${INPUT_FASTA}" \
    --output_dir "${SIGNALP_RAW_DIR}" \
    --mode "${MODE}" \
    --organism "${ORGANISM_TYPE}" \
    --format txt \
    2>&1 | tee -a "${LOG_FILE}"

SIGNALP_EXIT_CODE=${PIPESTATUS[0]}

if [ ${SIGNALP_EXIT_CODE} -ne 0 ]; then
    log_message "CRITICAL ERROR: SignalP 6 failed with exit code ${SIGNALP_EXIT_CODE}!"
    log_message "Check the log above for specific error messages."
    log_message "Common issues:"
    log_message "  - License not found or expired"
    log_message "  - Invalid FASTA format"
    log_message "  - Insufficient memory"
    exit 1
fi

log_message "SignalP 6 raw output written to: ${SIGNALP_RAW_DIR}"

# =============================================================================
# LOCATE SIGNALP OUTPUT FILE
# =============================================================================
# SignalP 6 writes a summary file (prediction_results.txt or output.txt)
# in the output directory. We need to find and parse it.
# =============================================================================

SIGNALP_RESULTS_FILE=""

# Check common SignalP 6 output filenames
for candidate_filename in "prediction_results.txt" "output.txt" "processed_entries.txt"; do
    if [ -f "${SIGNALP_RAW_DIR}/${candidate_filename}" ]; then
        SIGNALP_RESULTS_FILE="${SIGNALP_RAW_DIR}/${candidate_filename}"
        break
    fi
done

# If no standard filename found, look for any .txt file with results
if [ -z "${SIGNALP_RESULTS_FILE}" ]; then
    SIGNALP_RESULTS_FILE=$(find "${SIGNALP_RAW_DIR}" -maxdepth 1 -name "*.txt" -type f | head -1)
fi

if [ -z "${SIGNALP_RESULTS_FILE}" ] || [ ! -f "${SIGNALP_RESULTS_FILE}" ]; then
    log_message "CRITICAL ERROR: Could not locate SignalP output file!"
    log_message "Expected results in: ${SIGNALP_RAW_DIR}"
    log_message "Directory contents:"
    ls -la "${SIGNALP_RAW_DIR}" 2>&1 | tee -a "${LOG_FILE}"
    exit 1
fi

log_message "Parsing SignalP results from: ${SIGNALP_RESULTS_FILE}"

# =============================================================================
# PARSE SIGNALP OUTPUT AND CREATE FILTERED TSV
# =============================================================================
# SignalP 6 output format (tab-separated, with header lines starting with #):
#   Column 0: ID (protein identifier)
#   Column 1: Prediction (SP type: Sec/SPI, Sec/SPII, Tat/SPI, or OTHER)
#   Column 2+: Probability columns (varies by version)
#
# We extract: protein ID, prediction type, cleavage site position, and SP probability.
# Only proteins with predicted signal peptides (prediction != OTHER) are included.
# =============================================================================

python3 << PYTHON_PARSE_SCRIPT
import sys
from pathlib import Path

input_signalp_results_path = Path( "${SIGNALP_RESULTS_FILE}" )
output_predictions_path = Path( "${OUTPUT_PREDICTIONS}" )

total_protein_count = 0
signal_peptide_count = 0

with open( input_signalp_results_path, 'r' ) as input_signalp_results, \
     open( output_predictions_path, 'w' ) as output_predictions:

    # Write self-documenting header
    header = 'Protein_Identifier (protein sequence identifier from FASTA header)' + '\t'
    header += 'Prediction (SignalP prediction type: Sec/SPI for standard signal peptide or Sec/SPII for lipoprotein or Tat/SPI for twin arginine)' + '\t'
    header += 'Cleavage_Site_Position (amino acid position of signal peptide cleavage site predicted by SignalP)' + '\t'
    header += 'SP_Probability (probability score for signal peptide prediction from SignalP ranging 0 to 1)' + '\n'
    output_predictions.write( header )

    for line in input_signalp_results:
        line = line.strip()

        # Skip empty lines and comment/header lines
        if not line or line.startswith( '#' ):
            continue

        parts = line.split( '\t' )

        # Need at least protein ID and prediction columns
        if len( parts ) < 2:
            continue

        protein_identifier = parts[ 0 ].strip()
        prediction = parts[ 1 ].strip()

        total_protein_count += 1

        # Only include proteins WITH predicted signal peptides
        if prediction == 'OTHER':
            continue

        signal_peptide_count += 1

        # =====================================================================
        # Extract cleavage site position and SP probability
        # =====================================================================
        # SignalP 6 output varies slightly, but generally:
        #   - The CS (cleavage site) position is embedded in one of the columns
        #     as "CS pos: X-Y" where X is the last residue of the signal peptide
        #   - SP probability is in one of the numeric columns
        #
        # We parse all remaining columns to find these values.
        # =====================================================================

        cleavage_site_position = 'NA'
        signal_peptide_probability = 'NA'

        # Search through columns for cleavage site information
        for part_index in range( 2, len( parts ) ):
            column_value = parts[ part_index ].strip()

            # Look for cleavage site position pattern: "CS pos: X-Y"
            if 'CS pos:' in column_value or 'CS pos.' in column_value:
                # Extract the position number
                # Format examples: "CS pos: 20-21. ..." or "CS pos: 20-21"
                try:
                    position_text = column_value.split( 'CS pos' )[ 1 ]
                    # Remove punctuation after "CS pos" (colon, period, etc.)
                    position_text = position_text.lstrip( ':. ' )
                    # Get the cleavage position (the number before the dash)
                    parts_position = position_text.split( '-' )
                    if len( parts_position ) >= 1:
                        cleavage_site_position = parts_position[ 0 ].strip().split()[ 0 ].strip( '.' )
                except ( IndexError, ValueError ):
                    pass

        # Look for SP probability in the columns
        # SignalP 6 typically has probability columns with float values
        # The SP probability is usually the highest non-OTHER probability
        for part_index in range( 2, len( parts ) ):
            column_value = parts[ part_index ].strip()
            try:
                probability_value = float( column_value )
                # Signal peptide probabilities are between 0 and 1
                if 0.0 <= probability_value <= 1.0:
                    # Take the first valid probability (typically the SP probability)
                    if signal_peptide_probability == 'NA':
                        signal_peptide_probability = str( round( probability_value, 4 ) )
            except ValueError:
                pass

        output = protein_identifier + '\t'
        output += prediction + '\t'
        output += str( cleavage_site_position ) + '\t'
        output += str( signal_peptide_probability ) + '\n'
        output_predictions.write( output )

print( f"Parsed {total_protein_count} total proteins" )
print( f"Found {signal_peptide_count} proteins with predicted signal peptides" )
print( f"Filtered output written to: {output_predictions_path}" )

if total_protein_count == 0:
    print( "CRITICAL ERROR: No proteins found in SignalP output!", file = sys.stderr )
    print( f"Check SignalP results file: {input_signalp_results_path}", file = sys.stderr )
    sys.exit( 1 )
PYTHON_PARSE_SCRIPT

PARSE_EXIT_CODE=$?

if [ ${PARSE_EXIT_CODE} -ne 0 ]; then
    log_message "CRITICAL ERROR: Failed to parse SignalP output!"
    log_message "Parse script exited with code ${PARSE_EXIT_CODE}"
    exit 1
fi

log_message "Parsed SignalP output to: ${OUTPUT_PREDICTIONS}"

# =============================================================================
# CLEAN UP RAW OUTPUT
# =============================================================================
# Remove the raw SignalP output directory to save disk space.
# The parsed TSV contains all needed information.
# =============================================================================

rm -rf "${SIGNALP_RAW_DIR}"
log_message "Cleaned up raw SignalP output directory"

# =============================================================================
# VALIDATE OUTPUTS
# =============================================================================

log_message ""
log_message "Validating outputs..."

# Check predictions output exists
if [ ! -f "${OUTPUT_PREDICTIONS}" ]; then
    log_message "CRITICAL ERROR: Predictions output file was not created!"
    log_message "Expected: ${OUTPUT_PREDICTIONS}"
    exit 1
fi

PREDICTIONS_LINE_COUNT=$(wc -l < "${OUTPUT_PREDICTIONS}")
log_message "Predictions output: ${PREDICTIONS_LINE_COUNT} lines (including header)"

# The file should have at least the header line
if [ "${PREDICTIONS_LINE_COUNT}" -lt 1 ]; then
    log_message "CRITICAL ERROR: Predictions output file is empty!"
    exit 1
fi

# Report count of proteins with signal peptides (data lines = total - 1 header)
SIGNAL_PEPTIDE_COUNT=$((PREDICTIONS_LINE_COUNT - 1))
log_message "Proteins with predicted signal peptides: ${SIGNAL_PEPTIDE_COUNT}"
log_message "Total proteins in input: ${SEQUENCE_COUNT}"

if [ "${SIGNAL_PEPTIDE_COUNT}" -ge 0 ]; then
    log_message "Signal peptide detection rate: approximately $(echo "scale=1; ${SIGNAL_PEPTIDE_COUNT} * 100 / ${SEQUENCE_COUNT}" | bc 2>/dev/null || echo "N/A")%"
fi

# =============================================================================
# COMPLETION
# =============================================================================

log_message ""
log_message "========================================================================"
log_message "Script 002 completed successfully for: ${PHYLONAME}"
log_message "========================================================================"
log_message "Predictions output: ${OUTPUT_PREDICTIONS}"
log_message "Log file: ${LOG_FILE}"
