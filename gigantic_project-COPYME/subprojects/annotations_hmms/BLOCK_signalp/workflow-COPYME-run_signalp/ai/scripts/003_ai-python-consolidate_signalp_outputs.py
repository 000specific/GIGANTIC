#!/usr/bin/env python3
# AI: Claude Code | Opus 4.7 | 2026 May 23 | Purpose: Consolidate per-species SignalP6 raw outputs into a single descriptive-header TSV per species
# Human: Eric Edsinger

"""
003_ai-python-consolidate_signalp_outputs.py

For one species: reads the canonical proteome FASTA plus the per-species
SignalP6 raw output directory ( signalp_raw_output_<phyloname>/ ) and
writes a single per-species consolidated TSV with the GIGANTIC self-
documenting header style. Output filename is mode-tagged so fast and slow
runs coexist in the same output_to_input/BLOCK_signalp/ directory:

    <phyloname>_signalp_FAST_predictions.tsv     ( --mode fast )
    <phyloname>_signalp_SLOW_predictions.tsv     ( --mode slow )

Output schema ( one row per protein in proteome FASTA ):
    Protein_Identifier
    Sequence_Length
    Signal_Peptide_Call    ( Sec/SPI | Sec/SPII | Tat/SPI | None )
                           ( None when SignalP6 called OTHER OR the protein
                             was never processed by SignalP6 )
    Signal_Peptide_Start   ( 1 if call != None, None otherwise )
    Signal_Peptide_End     ( cleavage site residue position; None otherwise )
    OTHER_Probability      ( float; None if protein not in prediction_results )
    SP_Probability         ( float; None if not in prediction_results )
    LIPO_Probability       ( float; None if not in prediction_results )
    TAT_Probability        ( float; None if not in prediction_results )
    Cleavage_Site_String   ( raw 'CS pos: X-Y. Pr: Z' string; None if no SP )

Raw input read:
    <raw-output-dir>/prediction_results.txt
        SignalP6 native format ( eukarya organism ):
            #  ID  Prediction  OTHER  SP(Sec/SPI)  LIPO(Sec/SPII)  TAT(Tat/SPI)  CS Position
        Prediction values: SP | LIPO | TAT | OTHER

Mapping ( per user spec ):
    Raw Prediction = SP    -> Signal_Peptide_Call = Sec/SPI
    Raw Prediction = LIPO  -> Signal_Peptide_Call = Sec/SPII
    Raw Prediction = TAT   -> Signal_Peptide_Call = Tat/SPI
    Raw Prediction = OTHER -> Signal_Peptide_Call = None
"""

import argparse
import logging
import re
import sys
from pathlib import Path


RAW_PREDICTION_TO_CALL = {
    "SP":    "Sec/SPI",
    "LIPO":  "Sec/SPII",
    "TAT":   "Tat/SPI",
    "OTHER": "None",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description = "Consolidate per-species SignalP6 raw outputs into one descriptive-header TSV ( mode-tagged filename )."
    )
    parser.add_argument(
        "--input-fasta",
        required = True,
        help = "Path to the proteome FASTA file used as SignalP6 input for this species ( canonical full set of proteins for this RUN )",
    )
    parser.add_argument(
        "--raw-output-dir",
        required = True,
        help = "Path to signalp_raw_output_<phyloname>/ directory containing prediction_results.txt",
    )
    parser.add_argument(
        "--output-dir",
        required = True,
        help = "Directory where <phyloname>_signalp_<MODE>_predictions.tsv + log are written",
    )
    parser.add_argument(
        "--phyloname",
        required = True,
        help = "GIGANTIC phyloname for the species ( used in output naming )",
    )
    parser.add_argument(
        "--mode",
        required = True,
        choices = [ "fast", "slow" ],
        help = "SignalP6 mode this RUN used; used to tag the output filename",
    )
    return parser.parse_args()


def read_proteome_protein_ids_and_lengths( input_fasta_path, logger ):
    """
    Walk the proteome FASTA and return ordered list of ( protein_identifier, sequence_length ).
    """
    protein_ids_with_lengths = []
    current_identifier = None
    current_sequence_parts = []

    input_fasta = open( input_fasta_path, "r" )
    for line in input_fasta:
        line = line.rstrip( "\n" )
        if not line:
            continue
        if line.startswith( ">" ):
            if current_identifier is not None:
                sequence_length = sum( len( part ) for part in current_sequence_parts )
                protein_ids_with_lengths.append( ( current_identifier, sequence_length ) )
            current_identifier = line[ 1: ].split()[ 0 ]
            current_sequence_parts = []
        else:
            current_sequence_parts.append( line )
    if current_identifier is not None:
        sequence_length = sum( len( part ) for part in current_sequence_parts )
        protein_ids_with_lengths.append( ( current_identifier, sequence_length ) )
    input_fasta.close()

    logger.info( f"Proteome FASTA: read {len( protein_ids_with_lengths )} proteins" )
    return protein_ids_with_lengths


def parse_cleavage_site_position( cs_position_string ):
    """
    Extract the cleavage residue position ( int ) from SignalP6's CS Position string.
        'CS pos: 23-24. Pr: 0.985'  -> 23
        'CS pos. 23-24 ...'          -> 23
    Returns None if string is empty / parse fails.
    """
    if not cs_position_string or cs_position_string.strip() in ( "", "-" ):
        return None
    match = re.search( r"CS pos[:.\s]+(\d+)\s*-", cs_position_string )
    if match:
        try:
            return int( match.group( 1 ) )
        except ValueError:
            return None
    return None


def read_prediction_results( prediction_results_path, logger ):
    """
    Parse SignalP6 prediction_results.txt.

    SignalP6's column layout depends on the --organism flag used at run time:
        eukarya:                  ID  Prediction  OTHER  SP                CS_Position   ( 5 cols )
        other / gram_* / archaea: ID  Prediction  OTHER  SP  LIPO  TAT    CS_Position   ( 7 cols )
    LIPO + TAT are NOT predicted for eukarya ( only Sec/SPI is biologically possible ),
    so those probabilities are recorded as None for eukarya-mode runs.

    Returns dict: protein_id -> dict with keys:
        prediction          ( raw: SP | LIPO | TAT | OTHER )
        other_probability   ( float )
        sp_probability      ( float )
        lipo_probability    ( float OR None for eukarya )
        tat_probability     ( float OR None for eukarya )
        cs_position_string  ( last column value; '' if empty )
    """
    protein_ids___prediction_records = {}

    if not prediction_results_path.exists():
        logger.error( f"CRITICAL ERROR: prediction_results.txt not found at {prediction_results_path}" )
        sys.exit( 1 )

    input_prediction_results = open( prediction_results_path, "r" )
    for line in input_prediction_results:
        line = line.rstrip( "\n" )
        if not line or line.startswith( "#" ):
            continue
        parts = line.split( "\t" )
        n_fields = len( parts )

        if n_fields == 5:
            # Eukarya layout: only OTHER + SP probabilities exist.
            try:
                other_probability = float( parts[ 2 ] )
                sp_probability    = float( parts[ 3 ] )
            except ValueError:
                logger.error( f"CRITICAL ERROR: could not parse eukarya probability columns from line: {line[ :200 ]}" )
                logger.error( f"  source: {prediction_results_path}" )
                sys.exit( 1 )
            lipo_probability = None
            tat_probability  = None
            cs_position_string = parts[ 4 ].strip()
        elif n_fields >= 7:
            # Other / gram_* / archaea layout: all 4 probabilities present.
            try:
                other_probability = float( parts[ 2 ] )
                sp_probability    = float( parts[ 3 ] )
                lipo_probability  = float( parts[ 4 ] )
                tat_probability   = float( parts[ 5 ] )
            except ValueError:
                logger.error( f"CRITICAL ERROR: could not parse non-eukarya probability columns from line: {line[ :200 ]}" )
                logger.error( f"  source: {prediction_results_path}" )
                sys.exit( 1 )
            cs_position_string = parts[ 6 ].strip()
        else:
            logger.error( f"CRITICAL ERROR: unexpected prediction_results column count {n_fields}; expected 5 (eukarya) or 7 (other/gram/archaea)" )
            logger.error( f"  line: {line[ :200 ]}" )
            logger.error( f"  source: {prediction_results_path}" )
            sys.exit( 1 )

        protein_identifier = parts[ 0 ].strip()
        prediction = parts[ 1 ].strip()

        protein_ids___prediction_records[ protein_identifier ] = {
            "prediction":         prediction,
            "other_probability":  other_probability,
            "sp_probability":     sp_probability,
            "lipo_probability":   lipo_probability,
            "tat_probability":    tat_probability,
            "cs_position_string": cs_position_string,
        }
    input_prediction_results.close()

    logger.info( f"prediction_results.txt: read {len( protein_ids___prediction_records )} protein rows" )
    return protein_ids___prediction_records


def main():
    args = parse_args()

    output_dir = Path( args.output_dir ).resolve()
    output_dir.mkdir( parents = True, exist_ok = True )

    log_path = output_dir / f"3_ai-log-consolidate_signalp_outputs_{args.phyloname}.log"
    logging.basicConfig(
        level = logging.INFO,
        format = "%(asctime)s - %(levelname)s - %(message)s",
        handlers = [
            logging.FileHandler( log_path ),
            logging.StreamHandler( sys.stdout ),
        ],
    )
    logger = logging.getLogger( __name__ )

    mode_tag = args.mode.upper()   # 'FAST' or 'SLOW'
    consolidated_path = output_dir / f"{args.phyloname}_signalp_{mode_tag}_predictions.tsv"

    logger.info( "=" * 70 )
    logger.info( "Script 003: Consolidate SignalP6 raw outputs (per species)" )
    logger.info( "=" * 70 )
    logger.info( f"Phyloname: {args.phyloname}" )
    logger.info( f"Mode: {args.mode} ( filename tag: {mode_tag} )" )
    logger.info( f"Input FASTA: {args.input_fasta}" )
    logger.info( f"Raw output dir: {args.raw_output_dir}" )
    logger.info( f"Output dir: {output_dir}" )

    # --- Read proteome FASTA -------------------------------------------------
    protein_ids_with_lengths = read_proteome_protein_ids_and_lengths(
        Path( args.input_fasta ), logger,
    )
    if len( protein_ids_with_lengths ) == 0:
        logger.error( f"CRITICAL ERROR: proteome FASTA contained 0 proteins: {args.input_fasta}" )
        sys.exit( 1 )

    # --- Read prediction_results.txt -----------------------------------------
    raw_output_dir = Path( args.raw_output_dir )
    prediction_results_path = raw_output_dir / "prediction_results.txt"
    protein_ids___prediction_records = read_prediction_results( prediction_results_path, logger )

    # --- Cross-check: any prediction_results protein NOT in proteome FASTA? --
    proteome_protein_id_set = set( pid for ( pid, _ ) in protein_ids_with_lengths )
    foreign_protein_ids = [
        pid for pid in protein_ids___prediction_records.keys()
        if pid not in proteome_protein_id_set
    ]
    if len( foreign_protein_ids ) > 0:
        logger.error( "CRITICAL ERROR: prediction_results.txt contains protein IDs that are NOT in the proteome FASTA!" )
        logger.error( f"  count: {len( foreign_protein_ids )}" )
        logger.error( f"  first few: {foreign_protein_ids[ :5 ]}" )
        logger.error( f"  proteome FASTA: {args.input_fasta}" )
        logger.error( f"  prediction_results.txt: {prediction_results_path}" )
        sys.exit( 1 )

    # --- Write consolidated TSV ---------------------------------------------
    output_consolidated = open( consolidated_path, "w" )

    header = (
        "Protein_Identifier (canonical FASTA header from proteome)" + "\t"
        + "Sequence_Length (residue count from proteome FASTA)" + "\t"
        + "Signal_Peptide_Call (signal peptide type: Sec/SPI standard or Sec/SPII lipoprotein or Tat/SPI twin arginine; None when SignalP6 called OTHER or the protein was not annotated)" + "\t"
        + "Signal_Peptide_Start (residue start of signal peptide region; None if no call)" + "\t"
        + "Signal_Peptide_End (residue end of signal peptide region equal to cleavage site position; None if no call)" + "\t"
        + "OTHER_Probability (SignalP6 probability of no signal peptide; None if protein was not annotated by SignalP6)" + "\t"
        + "SP_Probability (SignalP6 probability of Sec/SPI standard signal peptide; None if not annotated)" + "\t"
        + "LIPO_Probability (SignalP6 probability of Sec/SPII lipoprotein signal peptide; None if not annotated)" + "\t"
        + "TAT_Probability (SignalP6 probability of Tat/SPI twin arginine signal peptide; None if not annotated)" + "\t"
        + "Cleavage_Site_String (raw SignalP6 CS pos string of the form 'CS pos: X-Y. Pr: Z'; None if no signal peptide)" + "\n"
    )
    output_consolidated.write( header )

    annotated_count = 0
    unannotated_count = 0
    call_counts = { "Sec/SPI": 0, "Sec/SPII": 0, "Tat/SPI": 0, "None": 0 }

    for ( protein_identifier, sequence_length ) in protein_ids_with_lengths:
        prediction_record = protein_ids___prediction_records.get( protein_identifier )

        if prediction_record is None:
            # Tool did not annotate this protein at all - everything None
            signal_peptide_call    = "None"
            signal_peptide_start   = "None"
            signal_peptide_end     = "None"
            other_probability_str  = "None"
            sp_probability_str     = "None"
            lipo_probability_str   = "None"
            tat_probability_str    = "None"
            cleavage_site_string   = "None"
            unannotated_count += 1
        else:
            raw_prediction = prediction_record[ "prediction" ]
            if raw_prediction not in RAW_PREDICTION_TO_CALL:
                logger.error( f"CRITICAL ERROR: unknown SignalP6 Prediction value: '{raw_prediction}' for {protein_identifier}" )
                logger.error( f"  expected one of: {sorted( RAW_PREDICTION_TO_CALL.keys() )}" )
                sys.exit( 1 )
            signal_peptide_call = RAW_PREDICTION_TO_CALL[ raw_prediction ]

            if signal_peptide_call == "None":
                # Prediction was OTHER. No SP region; probabilities still kept.
                signal_peptide_start = "None"
                signal_peptide_end   = "None"
                cleavage_site_string = "None"
            else:
                signal_peptide_start = "1"
                cleavage_position = parse_cleavage_site_position( prediction_record[ "cs_position_string" ] )
                signal_peptide_end = str( cleavage_position ) if cleavage_position is not None else "None"
                cleavage_site_string = prediction_record[ "cs_position_string" ] or "None"

            other_probability_str = str( prediction_record[ "other_probability" ] )
            sp_probability_str    = str( prediction_record[ "sp_probability" ] )
            lipo_probability_str  = str( prediction_record[ "lipo_probability" ] )
            tat_probability_str   = str( prediction_record[ "tat_probability" ] )
            annotated_count += 1
            call_counts[ signal_peptide_call ] += 1

        output = (
            protein_identifier + "\t"
            + str( sequence_length ) + "\t"
            + signal_peptide_call + "\t"
            + signal_peptide_start + "\t"
            + signal_peptide_end + "\t"
            + other_probability_str + "\t"
            + sp_probability_str + "\t"
            + lipo_probability_str + "\t"
            + tat_probability_str + "\t"
            + cleavage_site_string + "\n"
        )
        output_consolidated.write( output )

    output_consolidated.close()

    logger.info( "" )
    logger.info( "=" * 70 )
    logger.info( "SUMMARY" )
    logger.info( "=" * 70 )
    logger.info( f"Total proteins in consolidated TSV: {len( protein_ids_with_lengths )}" )
    logger.info( f"  SignalP6-annotated:     {annotated_count}" )
    logger.info( f"  not annotated by tool:  {unannotated_count}" )
    logger.info( f"Per-call counts ( among annotated ):" )
    for call_name in [ "Sec/SPI", "Sec/SPII", "Tat/SPI", "None" ]:
        logger.info( f"  {call_name:>10s}: {call_counts[ call_name ]}" )
    logger.info( f"Consolidated TSV: {consolidated_path}" )


if __name__ == "__main__":
    main()
