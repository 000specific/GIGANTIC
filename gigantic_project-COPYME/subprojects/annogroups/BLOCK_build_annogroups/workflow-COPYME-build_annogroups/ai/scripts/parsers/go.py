# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 28 | Purpose: annogroups source parser for Gene Ontology (GO) terms from the RAW per-species InterProScan results
# Human: Eric Edsinger

"""
annogroups source parser — go (Gene Ontology).

GO is NOT a standalone InterProScan member database — GO terms are emitted in the
GO_Terms column of the RAW per-species InterProScan results, tagged with the tool
that contributed them, e.g.:

    GO:0002764(PANTHER)
    GO:0002020(PANTHER)|GO:0005975(InterPro)|GO:0016758(InterPro)

Two contributing origins occur in this dataset:
  - (InterPro) : GO assigned via the curated InterPro2GO mapping of the InterPro
                 ENTRY a member-database match maps to. Already a curated,
                 cross-database consolidation (Pfam/SMART/CDD/... -> InterPro entry
                 -> GO). High precision.
  - (PANTHER)  : GO assigned directly by PANTHER (largely phylogenetically
                 inferred, GO PAINT/IBA). Higher recall, an inference layer.

Which origins to include is an EXPLICIT, documented user decision (config key
`go_term_origins`; default = both, i.e. the union across tools) per the project's
"explicit decisions are required" rule. See START_HERE-user_config.yaml.

GO terms are WHOLE-PROTEIN functional labels (molecular function / biological
process / cellular component), not sub-protein domains: even though each rides on
a positional match in the raw file, GO carries no meaningful sub-protein
arrangement. So GO features are NON-positional (is_positional = False) and GO
yields THREE annogroup types — feature, combination, absent — with NO architecture
(combination = whole-protein set of GO terms; architecture needs sub-protein
coordinates this source does not provide). This mirrors the deeploc whole-protein
label category.

Source-of-truth: the RAW results (BLOCK_interproscan/), per the user's decision —
not the per-database parsed views (BLOCK_interproscan_parsed/<db>/).

Parser-plugin contract (see utils_annogroups): expose SOURCE and
parse_source_features( workflow_root, config ) -> { sequence_id: [ Feature, ... ] }.

GO term NAMES: the raw results carry GO IDs but not names. parse_source_definitions
attaches human-readable names by reading the GO_ID -> name mapping that
annotations_hmms exposes (generated from the canonical go-basic.obo), so the
annogroup map's Annotation_Definitions read e.g. 'immune response-regulating
signaling pathway ==GO:0002764'. The mapping path is config['inputs']['go_names_map'].
"""

import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent.parent ) )
import utils_annogroups as U

SOURCE = "go"

# Path to the RAW InterProScan results, relative to the workflow root. The config
# exposes the annotations_hmms output_to_input root; this parser appends the raw
# InterProScan BLOCK subpath (NOT the per-database parsed views).
RELATIVE_SUBPATH = "BLOCK_interproscan"

# The raw InterProScan results files have NO header row; their columns are the
# fixed InterProScan TSV output order. 0-based positions used here:
INDEX_PROTEIN = 0     # full GIGANTIC protein identifier
INDEX_GO_TERMS = 13   # pipe-delimited 'GO:NNNNNNN(ORIGIN)' tokens, '-' if none
MINIMUM_COLUMNS = INDEX_GO_TERMS + 1   # a data row must reach at least the GO column

# Default origins to include when the config does not specify `go_term_origins`:
# the union across contributing tools (user decision 2026-06-28).
DEFAULT_GO_TERM_ORIGINS = [ "InterPro", "PANTHER" ]

# The three major GO categories (aspects / namespaces), in the conventional
# molecular-function / biological-process / cellular-component order. Declaring
# CATEGORIES (+ parse_source_categories below) makes the shared map builder emit
# two split columns per category (<label>_Identifiers, <label>_Definitions), so a
# GO annogroup's terms are broken out by aspect. ( namespace_in_obo, column_label ).
CATEGORIES = [
    ( "molecular_function", "GO_Molecular_Function" ),
    ( "biological_process", "GO_Biological_Process" ),
    ( "cellular_component", "GO_Cellular_Component" ),
]


def resolve_allowed_origins( config: dict ) -> set:
    """
    The set of GO contribution origins (lowercased) to include, from
    config['go_term_origins']. Defaults to the union across tools. Fail-fast if the
    key is present but resolves to an empty list (that would silently drop ALL GO
    terms, leaving the source with no features).
    """
    requested = config.get( "go_term_origins", DEFAULT_GO_TERM_ORIGINS )
    if isinstance( requested, str ):
        requested = [ requested ]
    allowed = { origin.strip().lower() for origin in requested if origin and origin.strip() }
    if not allowed:
        print( "CRITICAL ERROR: config 'go_term_origins' resolved to an empty set; "
               f"set it to a non-empty subset of {DEFAULT_GO_TERM_ORIGINS} (or remove it for the default union)", file = sys.stderr )
        sys.exit( 1 )
    return allowed


def parse_go_cell( go_cell: str, allowed_origins: set, source_file_name: str, raw_line: str ) -> set:
    """
    Parse one GO_Terms cell into the set of GO IDs whose contributing origin is in
    allowed_origins. '-' means no GO. Each token is 'GO:NNNNNNN(ORIGIN)'; a token
    that does not match that shape is a genuine upstream format problem -> fail
    fast (§36), never a silent skip.
    """
    go_ids = set()
    if go_cell == '-' or not go_cell:
        return go_ids
    for token in go_cell.split( '|' ):
        token = token.strip()
        if not token:
            continue
        if not token.startswith( "GO:" ) or '(' not in token or not token.endswith( ')' ):
            print( f"CRITICAL ERROR: malformed GO token '{token}' in {source_file_name}: {raw_line[ :160 ]}", file = sys.stderr )
            sys.exit( 1 )
        go_id = token[ : token.index( '(' ) ].strip()
        origin = token[ token.index( '(' ) + 1 : -1 ].strip().lower()
        if origin in allowed_origins:
            go_ids.add( go_id )
    return go_ids


def parse_source_features( workflow_root: Path, config: dict ) -> dict:
    """sequence_identifier -> [ Feature(accession=GO_ID, start=None, stop=None, is_positional=False) ]."""
    allowed_origins = resolve_allowed_origins( config )

    results_dir = U.resolve_input_path(
        workflow_root, config[ "inputs" ][ "annotations_hmms_dir" ]
    ) / RELATIVE_SUBPATH

    if not results_dir.is_dir():
        print( f"CRITICAL ERROR: raw InterProScan results directory not found: {results_dir}", file = sys.stderr )
        print( "  Verify annotations_hmms exposed BLOCK_interproscan/ in output_to_input.", file = sys.stderr )
        sys.exit( 1 )

    results_files = sorted( results_dir.glob( "*_interproscan_results.tsv" ) )
    if not results_files:
        print( f"CRITICAL ERROR: no *_interproscan_results.tsv files in {results_dir}", file = sys.stderr )
        sys.exit( 1 )

    print( f"[parser go] including GO origins: {', '.join( sorted( allowed_origins ) )}", file = sys.stderr )

    # Collect distinct GO IDs per protein (set), then materialize Features. Many
    # raw rows (different matches) of one protein can repeat the same GO ID; the
    # whole-protein GO feature set is the union of distinct IDs.
    proteins___go_ids = {}
    for results_file in results_files:
        with open( results_file, 'r' ) as input_results:
            # RAW InterProScan results — NO header row; fixed column order.
            # g_..._n_<phyloname>\t<md5>\t<len>\t<analysis>\t<accession>\t...\tGO_Terms\tPathways
            for line in input_results:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                if len( parts ) < MINIMUM_COLUMNS:
                    # Fixed-format raw IPS rows are uniformly 15 columns; a short
                    # row means the format assumption broke -> fail fast (§36).
                    print( f"CRITICAL ERROR: raw InterProScan row has {len( parts )} columns "
                           f"(need >= {MINIMUM_COLUMNS}) in {results_file.name}: {line[ :160 ]}", file = sys.stderr )
                    sys.exit( 1 )
                go_ids = parse_go_cell( parts[ INDEX_GO_TERMS ], allowed_origins, results_file.name, line )
                if not go_ids:
                    continue
                protein = parts[ INDEX_PROTEIN ]
                proteins___go_ids.setdefault( protein, set() ).update( go_ids )

    proteins___features = {}
    for protein, go_ids in proteins___go_ids.items():
        proteins___features[ protein ] = [
            U.Feature( accession = go_id, start = None, stop = None, is_positional = False )
            for go_id in sorted( go_ids )
        ]

    return proteins___features


def parse_source_definitions( workflow_root: Path, config: dict ) -> dict:
    """
    accession (GO ID) -> human-readable GO term name, from the GO_ID -> name mapping
    that annotations_hmms exposes (generated from go-basic.obo; see
    annotations_hmms/reference_go/). The mapping path is config['inputs']['go_names_map'].

    Optional half of the parser contract: with it, the annogroup map's
    Annotation_Definitions read 'GO term name ==GO:ID'. If the key is absent the
    builder emits bare ==GO:ID; if the key is set but the file is missing, fail fast
    (§36) — a misconfigured names map must not silently degrade to nameless GO.
    """
    go_names_map_relative = config.get( "inputs", {} ).get( "go_names_map" )
    if not go_names_map_relative:
        print( "[parser go] WARNING: inputs.go_names_map not configured; GO annogroup "
               "definitions will be bare ==GO:ID (no term names)", file = sys.stderr )
        return {}

    go_names_map_path = U.resolve_input_path( workflow_root, go_names_map_relative )
    if not go_names_map_path.is_file():
        print( f"CRITICAL ERROR: GO names map not found: {go_names_map_path}", file = sys.stderr )
        print( "  Generate it: annotations_hmms/reference_go/generate_go_id_to_name.py, then expose it "
               "at output_to_input/GO_reference/go_id_to_name.tsv (or unset inputs.go_names_map).", file = sys.stderr )
        sys.exit( 1 )

    accessions___definitions = {}
    with open( go_names_map_path, 'r' ) as input_map:
        # GO_ID (...)\tGO_Name (...)\tGO_Namespace (...)\tIs_Obsolete (...)\tIs_Primary_ID (...)
        # GO:0000001\tmitochondrion inheritance\tbiological_process\tFalse\tTrue
        header_ids___indices = U.build_header_index( input_map.readline() )
        index_go_id = header_ids___indices[ "GO_ID" ]
        index_go_name = header_ids___indices[ "GO_Name" ]
        for line in input_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            go_id = parts[ index_go_id ]
            go_name = U.sanitize_annotation_text( parts[ index_go_name ] ) if index_go_name < len( parts ) else ''
            if go_name and go_id not in accessions___definitions:
                accessions___definitions[ go_id ] = go_name

    return accessions___definitions


def parse_source_categories( workflow_root: Path, config: dict ) -> dict:
    """
    accession (GO ID) -> GO aspect / namespace (molecular_function,
    biological_process, or cellular_component), from the same GO_ID -> name mapping
    (its GO_Namespace column). Drives the per-aspect split columns (see CATEGORIES).

    Returns {} if inputs.go_names_map is unset (no aspect split); fail-fast (§36) if
    it is set but missing — a misconfigured map must not silently drop the split.
    """
    go_names_map_relative = config.get( "inputs", {} ).get( "go_names_map" )
    if not go_names_map_relative:
        return {}

    go_names_map_path = U.resolve_input_path( workflow_root, go_names_map_relative )
    if not go_names_map_path.is_file():
        print( f"CRITICAL ERROR: GO names map not found: {go_names_map_path}", file = sys.stderr )
        sys.exit( 1 )

    accessions___categories = {}
    with open( go_names_map_path, 'r' ) as input_map:
        # GO_ID (...)\tGO_Name (...)\tGO_Namespace (...)\tIs_Obsolete (...)\tIs_Primary_ID (...)
        # GO:0000001\tmitochondrion inheritance\tbiological_process\tFalse\tTrue
        header_ids___indices = U.build_header_index( input_map.readline() )
        index_go_id = header_ids___indices[ "GO_ID" ]
        index_namespace = header_ids___indices[ "GO_Namespace" ]
        for line in input_map:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            go_id = parts[ index_go_id ]
            namespace = parts[ index_namespace ] if index_namespace < len( parts ) else ''
            if namespace and go_id not in accessions___categories:
                accessions___categories[ go_id ] = namespace

    return accessions___categories
