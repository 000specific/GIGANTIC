# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 28 | Purpose: annogroups source parser for TMBed (per-species transmembrane-topology predictions)
# Human: Eric Edsinger

"""
annogroups source parser — tmbed.

Reads the per-species TMBed prediction files exposed by annotations_hmms at
  annotations_hmms/output_to_input/BLOCK_tmbed/<phyloname>_tmbed_predictions.tsv
and returns, per sequence, its membrane-topology segments.

TMBed detects three POSITIONAL segment classes, each with residue coordinates:
  - TM_helix       (alpha-helix transmembrane regions)
  - beta_barrel    (beta-barrel transmembrane regions)
  - signal_peptide (signal-peptide regions)
A protein can have many segments. Each segment becomes one Feature whose accession
is its CLASS name, with the segment's residue coordinates. Because the segments are
positional, tmbed yields all FOUR annogroup types — feature, combination,
architecture, absent — and the ARCHITECTURE is the N->C membrane topology (e.g. all
7-TM-helix receptors share the architecture (TM_helix x7); a signal_peptide then
several TM_helix groups secreted multi-pass proteins).

Within each class TMBed segments carry no sub-type, so the class name is the
accession (clean already: TM_helix / beta_barrel / signal_peptide). The columns are
per-class Starts / Ends comma-delimited lists (matched 1:1), 'None' when the class
has no segment.

Caveat (shared with the other per-protein tools): proteins not scored by TMBed
(e.g. dropped upstream by the long-header filter) have no feature here and fall into
annogroup_tmbed_absent.

Parser-plugin contract (see utils_annogroups): expose SOURCE and
parse_source_features( workflow_root, config ) -> { sequence_id: [ Feature, ... ] }.
"""

import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent.parent ) )
import utils_annogroups as U

SOURCE = "tmbed"
RELATIVE_SUBPATH = "BLOCK_tmbed"

# ( accession/class name, Starts header_id, Ends header_id )
SEGMENT_CLASSES = [
    ( "TM_helix",       "TM_Helix_Starts",       "TM_Helix_Ends" ),
    ( "beta_barrel",    "Beta_Barrel_Starts",    "Beta_Barrel_Ends" ),
    ( "signal_peptide", "Signal_Peptide_Starts", "Signal_Peptide_Ends" ),
]


def _parse_coordinate_list( cell: str ):
    """Comma-delimited residue positions -> [int]; 'None'/'' -> []."""
    cell = cell.strip()
    if not cell or cell == "None":
        return []
    return [ int( token.strip() ) for token in cell.split( ',' ) if token.strip() != '' ]


def parse_source_features( workflow_root: Path, config: dict ) -> dict:
    """sequence_identifier -> [ Feature(accession=segment_class, start, stop, is_positional=True) ]."""
    annotations_dir = U.resolve_input_path(
        workflow_root, config[ "inputs" ][ "annotations_hmms_dir" ]
    ) / RELATIVE_SUBPATH

    if not annotations_dir.is_dir():
        print( f"CRITICAL ERROR: tmbed annotation directory not found: {annotations_dir}", file = sys.stderr )
        print( "  Verify annotations_hmms exposed BLOCK_tmbed/ in output_to_input.", file = sys.stderr )
        sys.exit( 1 )

    tmbed_files = sorted( annotations_dir.glob( "*_tmbed_predictions.tsv" ) )
    if not tmbed_files:
        print( f"CRITICAL ERROR: no *_tmbed_predictions.tsv files in {annotations_dir}", file = sys.stderr )
        sys.exit( 1 )

    proteins___features = {}
    for tmbed_file in tmbed_files:
        with open( tmbed_file, 'r' ) as input_tmbed:
            # Protein_Identifier (...)\t...\tTM_Helix_Starts (...)\tTM_Helix_Ends (...)\t...
            header_ids___indices = U.build_header_index( input_tmbed.readline() )
            index_protein = header_ids___indices[ "Protein_Identifier" ]
            class_specs = [ ( accession,
                              header_ids___indices[ starts_id ],
                              header_ids___indices[ ends_id ] )
                            for ( accession, starts_id, ends_id ) in SEGMENT_CLASSES ]
            for line in input_tmbed:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                protein = parts[ index_protein ]
                for ( accession, index_start, index_stop ) in class_specs:
                    starts_cell = parts[ index_start ] if index_start < len( parts ) else "None"
                    ends_cell = parts[ index_stop ] if index_stop < len( parts ) else "None"
                    try:
                        starts = _parse_coordinate_list( starts_cell )
                        ends = _parse_coordinate_list( ends_cell )
                    except ValueError:
                        print( f"CRITICAL ERROR: non-integer {accession} coordinates in {tmbed_file.name}: {line[ :120 ]}", file = sys.stderr )
                        sys.exit( 1 )
                    if len( starts ) != len( ends ):
                        print( f"CRITICAL ERROR: {accession} start/end count mismatch in {tmbed_file.name}: {line[ :120 ]}", file = sys.stderr )
                        sys.exit( 1 )
                    for ( start, stop ) in zip( starts, ends ):
                        proteins___features.setdefault( protein, [] ).append(
                            U.Feature( accession = accession, start = start, stop = stop, is_positional = True )
                        )

    return proteins___features
