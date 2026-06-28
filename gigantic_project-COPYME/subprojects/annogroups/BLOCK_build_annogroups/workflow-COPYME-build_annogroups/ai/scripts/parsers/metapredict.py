# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 28 | Purpose: annogroups source parser for MetaPredict (per-species intrinsically-disordered-region predictions)
# Human: Eric Edsinger

"""
annogroups source parser — metapredict.

Reads the per-species MetaPredict prediction files exposed by annotations_hmms at
  annotations_hmms/output_to_input/BLOCK_metapredict/<phyloname>_metapredict_predictions.tsv
and returns, per sequence, its intrinsically-disordered regions (IDRs).

MetaPredict detects POSITIONAL IDRs but assigns them NO sub-type — every IDR is
just an "intrinsically disordered region". So a single accession ('IDR') is used
for all of them. Consequences (user-accepted 2026-06-28, low-resolution but valid):
  - feature      : one annogroup_metapredict_IDR (every protein with >=1 IDR)
  - combination  : one combination annogroup ({IDR}) — same membership as feature
  - architecture : informative — groups proteins by IDR COUNT (the coord-free
                   ordered pattern is (IDR,), (IDR,IDR), ... so N-IDR proteins group)
  - absent       : proteins with no IDR

The IDR_Starts / IDR_Ends columns are comma-delimited residue lists (matched 1:1),
'None' when the protein has no IDR.

Caveat (shared with the other per-protein tools): proteins not scored by MetaPredict
(e.g. dropped upstream by the long-header filter) have no feature here and fall into
annogroup_metapredict_absent.

Parser-plugin contract (see utils_annogroups): expose SOURCE and
parse_source_features( workflow_root, config ) -> { sequence_id: [ Feature, ... ] }.
"""

import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent.parent ) )
import utils_annogroups as U

SOURCE = "metapredict"
RELATIVE_SUBPATH = "BLOCK_metapredict"

# MetaPredict IDRs carry no sub-type; a single accession labels every IDR.
ACCESSION = "IDR"


def _parse_coordinate_list( cell: str ):
    """Comma-delimited residue positions -> [int]; 'None'/'' -> []."""
    cell = cell.strip()
    if not cell or cell == "None":
        return []
    return [ int( token.strip() ) for token in cell.split( ',' ) if token.strip() != '' ]


def parse_source_features( workflow_root: Path, config: dict ) -> dict:
    """sequence_identifier -> [ Feature(accession='IDR', start, stop, is_positional=True) ]."""
    annotations_dir = U.resolve_input_path(
        workflow_root, config[ "inputs" ][ "annotations_hmms_dir" ]
    ) / RELATIVE_SUBPATH

    if not annotations_dir.is_dir():
        print( f"CRITICAL ERROR: metapredict annotation directory not found: {annotations_dir}", file = sys.stderr )
        print( "  Verify annotations_hmms exposed BLOCK_metapredict/ in output_to_input.", file = sys.stderr )
        sys.exit( 1 )

    metapredict_files = sorted( annotations_dir.glob( "*_metapredict_predictions.tsv" ) )
    if not metapredict_files:
        print( f"CRITICAL ERROR: no *_metapredict_predictions.tsv files in {annotations_dir}", file = sys.stderr )
        sys.exit( 1 )

    proteins___features = {}
    for metapredict_file in metapredict_files:
        with open( metapredict_file, 'r' ) as input_metapredict:
            # Protein_Identifier (...)\tSequence_Length (...)\tIDR_Count (...)\tIDR_Identifiers (...)\tIDR_Starts (...)\tIDR_Ends (...)
            header_ids___indices = U.build_header_index( input_metapredict.readline() )
            index_protein = header_ids___indices[ "Protein_Identifier" ]
            index_start = header_ids___indices[ "IDR_Starts" ]
            index_stop = header_ids___indices[ "IDR_Ends" ]
            for line in input_metapredict:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                protein = parts[ index_protein ]
                starts_cell = parts[ index_start ] if index_start < len( parts ) else "None"
                ends_cell = parts[ index_stop ] if index_stop < len( parts ) else "None"
                try:
                    starts = _parse_coordinate_list( starts_cell )
                    ends = _parse_coordinate_list( ends_cell )
                except ValueError:
                    print( f"CRITICAL ERROR: non-integer IDR coordinates in {metapredict_file.name}: {line[ :120 ]}", file = sys.stderr )
                    sys.exit( 1 )
                if len( starts ) != len( ends ):
                    print( f"CRITICAL ERROR: IDR start/end count mismatch in {metapredict_file.name}: {line[ :120 ]}", file = sys.stderr )
                    sys.exit( 1 )
                for ( start, stop ) in zip( starts, ends ):
                    proteins___features.setdefault( protein, [] ).append(
                        U.Feature( accession = ACCESSION, start = start, stop = stop, is_positional = True )
                    )

    return proteins___features
