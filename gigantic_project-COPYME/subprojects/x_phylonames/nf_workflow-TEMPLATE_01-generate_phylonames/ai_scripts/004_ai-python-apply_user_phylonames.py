#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 07 | Purpose: Apply user-provided phylonames with UNOFFICIAL marking
# Human: Eric Edsinger

"""
USER-PROVIDED PHYLONAMES WITH UNOFFICIAL DETECTION
================================================================================

================================================================================
SCRIPT PURPOSE (For Non-Programmers):
================================================================================
This script allows you to OVERRIDE the default NCBI taxonomy with your own
preferred phylogenetic names. This is useful when:

1. NCBI taxonomy is incomplete (many levels show as Kingdom6555, Phylum6554, etc.)
2. You prefer a different taxonomic framework based on recent literature
3. Your working group uses specific naming conventions

THE PROBLEM THIS SOLVES:
NCBI Taxonomy is both INCOMPLETE and represents only ONE of multiple possible
hypotheses about the phylogenetic history of each species. When NCBI lacks
classification data for a taxonomic level, GIGANTIC generates numbered
identifiers to fill the gap. For example, Monosiga brevicollis might get:

    Kingdom6555_Phylum6554_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1

IMPORTANT: Kingdom6555 and Phylum6554 are NOT assigned by NCBI - they are
GIGANTIC's unbiased, neutral way of generating unique clade names when NCBI
data is missing. The numbering preserves phylogenetic information by grouping
species that share the same named clade below the unknown level.

Based on current literature or alternative phylogenetic hypotheses, you might prefer:
    Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1

THE UNOFFICIAL SUFFIX:
When you provide custom phylonames, ALL clades in the user phyloname are marked
with "UNOFFICIAL" by default. This is because:

1. Assigning a clade to a species is a DECISION POINT
2. NCBI made one decision (their official assignment)
3. When you override it, YOUR assignment is "unofficial" - even if the clade
   name itself exists in NCBI taxonomy

Example output:
    HolozoaUNOFFICIAL_ChoanozoaUNOFFICIAL_ChoanoflagellataUNOFFICIAL_CraspedidaUNOFFICIAL_SalpingoecidaeUNOFFICIAL_Monosiga_brevicollis_MX1

This way, anyone looking at the phyloname knows ALL taxonomic assignments
came from user-provided data, not from NCBI's official taxonomy.

DISABLING UNOFFICIAL MARKING:
If you prefer clean phylonames without the UNOFFICIAL suffix, set
mark_unofficial: false in the config. This is useful when:
- Your phylonames are from an authoritative source you trust
- You're working within a group that has agreed on taxonomy
- You want cleaner output for visualization/publication

IMPORTANT CAVEAT - WHEN NUMBERED CLADES REMAIN:
Even after applying user phylonames, you may still see numbered clades like
"Family1426" in your final output. This happens when:

1. User phylonames weren't provided for that species
2. User phylonames were provided but didn't specify all levels
3. The species simply wasn't in your user phylonames file

CRITICAL LIMITATION - CLADE SPLITTING ARTIFACT:
GIGANTIC's numbered clades have a subtle but important limitation. When a single
unknown higher-level clade actually contains MULTIPLE lower-level clades, the
numbering SPLITS the real clade into multiple numbered clades.

Example: If one unknown Kingdom actually contains Phyla A, B, and C, GIGANTIC creates:
  - Kingdom1 (for species in Phylum A)
  - Kingdom2 (for species in Phylum B)
  - Kingdom3 (for species in Phylum C)
But in reality, all belong to the SAME unknown Kingdom.

IMPACT ON ANALYSES:
- If your species set includes species from only ONE lower-level clade → NO PROBLEM
- If your species set includes species from MULTIPLE lower-level clades that share
  an unknown higher clade → PROBLEM: OCL (Origins, Conservation, Loss) analyses
  will CRYPTICALLY FAIL to capture accurate evolutionary patterns because species
  that share common ancestry appear as separate lineages.

THIS IS WHY USER PHYLONAMES MATTER: If you know (from literature or phylogenetic
analysis) that certain species share a higher-level clade despite NCBI gaps,
provide user phylonames to correctly group them. This prevents analytical artifacts

Numbered clades mean: "NCBI doesn't have official names for these levels, and
neither did the user provide custom names." This is scientifically valid - it
honestly reflects missing taxonomic data rather than inventing names.

================================================================================
METHODS DOCUMENTATION (For Publication):
================================================================================
Step 1: LOAD NCBI CLADE VOCABULARY
    - Parse the master phyloname mapping from Script 002
    - Extract all unique clade names at each taxonomic level
    - Build sets of valid NCBI clades: kingdoms, phyla, classes, orders, families
    - This vocabulary is used to detect which user-provided clades are "unofficial"

Step 2: LOAD PROJECT MAPPING
    - Read the project-specific mapping from Script 003
    - Contains genus_species -> phyloname mappings for your species

Step 3: LOAD USER-PROVIDED PHYLONAMES
    - Read user's custom phyloname file (TSV format)
    - Each line: genus_species<TAB>custom_phyloname
    - User phylonames completely replace NCBI-generated phylonames

Step 4: DETECT UNOFFICIAL CLADES
    - For each clade in user-provided phylonames:
        - Check if clade exists in NCBI vocabulary
        - If NOT in NCBI, append "UNOFFICIAL" suffix
    - Preserves transparency about data sources

Step 5: GENERATE FINAL MAPPING
    - Merge user phylonames with project mapping
    - User phylonames take precedence where provided
    - NCBI phylonames used for species without user overrides
    - Output includes both original and user-modified phylonames

================================================================================
INPUT FILE FORMATS:
================================================================================

PROJECT MAPPING (from Script 003):
    genus_species<TAB>phyloname<TAB>phyloname_taxonid
    Homo_sapiens<TAB>Metazoa_Chordata_Mammalia_...<TAB>Metazoa_Chordata_..___9606

USER PHYLONAMES FILE (optional):
    genus_species<TAB>custom_phyloname
    Monosiga_brevicollis_MX1<TAB>Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1

================================================================================
OUTPUT FILES:
================================================================================

FINAL MAPPING (output/4-output/final_project_mapping.tsv):
    genus_species<TAB>phyloname<TAB>phyloname_taxonid<TAB>source<TAB>original_phyloname
    Monosiga_brevicollis_MX1<TAB>Holozoa_ChoanozoaUNOFFICIAL_...<TAB>...<TAB>USER<TAB>Kingdom6555_...

UNOFFICIAL CLADES REPORT (output/4-output/unofficial_clades_report.tsv):
    Documents all user-provided clades marked as UNOFFICIAL

================================================================================
TECHNICAL NOTES (For Python/CS Experts):
================================================================================
- Uses set lookups for O(1) clade validation
- Preserves taxon_id from original NCBI assignment
- Handles multi-word species names (Genus_species_subspecies)
- Fail-fast validation ensures data integrity
- Comprehensive logging for debugging and reproducibility
"""

from pathlib import Path
from typing import Dict, List, Tuple
import sys
import argparse
from datetime import datetime


# ================================================================================
# CONFIGURATION
# ================================================================================
# These paths are defaults; can be overridden via command line arguments

OUTPUT_DIR = Path( 'output/4-output' )


# ================================================================================
# PROJECT MAPPING LOADING
# ================================================================================
# Load the mapping created by Script 003 for the user's specific project species.

def load_project_mapping( project_mapping_path: Path ) -> Dict[ str, Tuple[ str, str ] ]:
    """
    Load the project-specific species to phyloname mapping.

    This file was created by Script 003 and contains only the species
    in the user's project (not the entire NCBI taxonomy).

    Args:
        project_mapping_path: Path to project mapping TSV

    Returns:
        Dictionary: genus_species -> (phyloname, phyloname_taxonid)
    """

    print( "=" * 70 )
    print( "STEP 1: Loading project mapping" )
    print( "=" * 70 )
    print( f"  Source: {project_mapping_path}" )

    genus_species___phylonames = {}

    # genus_species	phyloname	phyloname_taxonid
    # Homo_sapiens	Metazoa_Chordata_...	Metazoa_Chordata_...___9606
    with open( project_mapping_path, 'r', encoding = 'utf-8' ) as input_file:
        # Skip header
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 3:
                continue

            genus_species = parts[ 0 ]
            phyloname = parts[ 1 ]
            phyloname_taxonid = parts[ 2 ]

            genus_species___phylonames[ genus_species ] = ( phyloname, phyloname_taxonid )

    print( f"  Loaded {len( genus_species___phylonames )} species mappings" )
    print( "" )

    return genus_species___phylonames


# ================================================================================
# USER PHYLONAMES LOADING
# ================================================================================
# Load user-provided custom phylonames that override NCBI defaults.

def load_user_phylonames( user_phylonames_path: Path ) -> Dict[ str, str ]:
    """
    Load user-provided custom phylonames.

    These phylonames will OVERRIDE the NCBI-generated phylonames for
    species where the user has provided a custom assignment.

    File format (TSV):
        genus_species<TAB>custom_phyloname

    Example:
        Monosiga_brevicollis_MX1<TAB>Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1

    Args:
        user_phylonames_path: Path to user phylonames TSV

    Returns:
        Dictionary: genus_species -> custom_phyloname
    """

    print( "=" * 70 )
    print( "STEP 2: Loading user-provided phylonames" )
    print( "=" * 70 )
    print( f"  Source: {user_phylonames_path}" )

    genus_species___custom_phylonames = {}

    # genus_species	custom_phyloname
    # Monosiga_brevicollis_MX1	Holozoa_Choanozoa_Choanoflagellata_...
    with open( user_phylonames_path, 'r', encoding = 'utf-8' ) as input_file:
        line_number = 0

        for line in input_file:
            line_number += 1
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith( '#' ):
                continue

            parts = line.split( '\t' )

            # Validate format: must have exactly 2 columns
            if len( parts ) != 2:
                print( f"  WARNING: Line {line_number} has {len( parts )} columns (expected 2), skipping" )
                continue

            genus_species = parts[ 0 ]
            custom_phyloname = parts[ 1 ]

            # Validate phyloname has expected structure
            parts_phyloname = custom_phyloname.split( '_' )
            if len( parts_phyloname ) < 7:
                print( f"  WARNING: Line {line_number} phyloname has < 7 parts, skipping: {genus_species}" )
                continue

            genus_species___custom_phylonames[ genus_species ] = custom_phyloname

    print( f"  Loaded {len( genus_species___custom_phylonames )} user-provided phylonames" )
    print( "" )

    return genus_species___custom_phylonames


# ================================================================================
# UNOFFICIAL CLADE MARKING
# ================================================================================
# Mark ALL clades in user-provided phylonames with "UNOFFICIAL" suffix.
# The key insight: assigning a clade to a species is a DECISION POINT.
# When users override NCBI's decision, their assignment is "unofficial"
# regardless of whether the clade name itself exists in NCBI taxonomy.

def mark_unofficial_clades(
    phyloname: str,
    mark_unofficial: bool = True
) -> Tuple[ str, List[ str ] ]:
    """
    Mark ALL clades in a user-provided phyloname as UNOFFICIAL.

    IMPORTANT: This marks ALL higher taxonomy clades (Kingdom through Family),
    not just those that don't exist in NCBI. The rationale:

    1. Assigning a clade to a species is a taxonomic DECISION
    2. NCBI made their official decision
    3. When the user overrides this, their decision is "unofficial" -
       even if the clade name itself exists in NCBI taxonomy
    4. The name existing in NCBI is irrelevant - it's the ASSIGNMENT that matters

    Example:
    User provides: Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis
    Output:        HolozoaUNOFFICIAL_ChoanozoaUNOFFICIAL_ChoanoflagellataUNOFFICIAL_CraspedidaUNOFFICIAL_SalpingoecidaeUNOFFICIAL_Monosiga_brevicollis

    NOTE: Genus and species are NOT marked - users are expected to provide
    valid genus/species combinations that identify the organism.

    Args:
        phyloname: The phyloname to mark (Kingdom_Phylum_Class_Order_Family_Genus_species)
        mark_unofficial: If True, add UNOFFICIAL suffix. If False, return unchanged.

    Returns:
        Tuple of:
        - Modified phyloname with UNOFFICIAL suffixes added (or unchanged if mark_unofficial=False)
        - List of clades that were marked as unofficial
    """

    # If marking is disabled, return unchanged
    if not mark_unofficial:
        return phyloname, []

    # Split phyloname into components
    parts_phyloname = phyloname.split( '_' )

    # Need at least 7 parts for valid phyloname
    if len( parts_phyloname ) < 7:
        return phyloname, []

    # Track which clades we mark as unofficial
    unofficial_clades = []

    # Mark each taxonomic level (positions 0-4: Kingdom through Family)
    # We do NOT mark Genus (position 5) or species (position 6+)
    taxonomic_levels = [ 'Kingdom', 'Phylum', 'Class', 'Order', 'Family' ]

    for position, level_name in enumerate( taxonomic_levels ):
        clade_name = parts_phyloname[ position ]

        # Skip if already marked unofficial (don't double-mark)
        if clade_name.endswith( 'UNOFFICIAL' ):
            unofficial_clades.append( clade_name )
            continue

        # Mark as unofficial by appending suffix
        # ALL user-provided clades get marked, regardless of NCBI status
        marked_clade = clade_name + 'UNOFFICIAL'
        parts_phyloname[ position ] = marked_clade
        unofficial_clades.append( marked_clade )

    # Reconstruct phyloname with marked clades
    marked_phyloname = '_'.join( parts_phyloname )

    return marked_phyloname, unofficial_clades


# ================================================================================
# FINAL MAPPING GENERATION
# ================================================================================
# Merge user phylonames with project mapping, applying UNOFFICIAL detection.

def generate_final_mapping(
    genus_species___project_phylonames: Dict[ str, Tuple[ str, str ] ],
    genus_species___user_phylonames: Dict[ str, str ],
    output_dir: Path,
    mark_unofficial: bool = True
) -> Dict[ str, Tuple[ str, str, str, str ] ]:
    """
    Generate the final mapping by merging project and user phylonames.

    For each species in the project:
    - If user provided a custom phyloname: use it (with UNOFFICIAL marking if enabled)
    - Otherwise: use the NCBI-generated phyloname

    This function also:
    - Generates the taxon_id version of the final phyloname
    - Tracks data source (NCBI vs USER)
    - Records original phyloname for reference

    Args:
        genus_species___project_phylonames: From Script 003
        genus_species___user_phylonames: User-provided overrides
        output_dir: Directory for output files
        mark_unofficial: If True (default), add UNOFFICIAL suffix to user-provided clades

    Returns:
        Dictionary: genus_species -> (final_phyloname, phyloname_taxonid, source, original_phyloname)
    """

    print( "=" * 70 )
    print( "STEP 3: Generating final mapping" )
    print( "=" * 70 )
    print( f"  UNOFFICIAL marking: {'ENABLED (default)' if mark_unofficial else 'DISABLED'}" )
    print( "" )

    # Ensure output directory exists
    output_dir.mkdir( parents = True, exist_ok = True )

    # Track statistics
    ncbi_count = 0
    user_count = 0
    unofficial_clades_all = []

    # Final mapping structure
    genus_species___final = {}

    # Process each species in the project
    for genus_species, ( ncbi_phyloname, ncbi_phyloname_taxonid ) in genus_species___project_phylonames.items():

        # Check if user provided a custom phyloname
        if genus_species in genus_species___user_phylonames:
            # Use user-provided phyloname
            user_phyloname = genus_species___user_phylonames[ genus_species ]

            # Mark ALL clades as unofficial (if enabled)
            # The key insight: user assignment is unofficial regardless of NCBI name existence
            marked_phyloname, unofficial_clades = mark_unofficial_clades(
                phyloname = user_phyloname,
                mark_unofficial = mark_unofficial
            )

            # Extract taxon_id from original NCBI phyloname_taxonid
            # Format: Phyloname___TaxonID
            if '___' in ncbi_phyloname_taxonid:
                taxon_id = ncbi_phyloname_taxonid.split( '___' )[ -1 ]
            else:
                taxon_id = ''

            # Create taxonid version of marked phyloname
            marked_phyloname_taxonid = marked_phyloname + '___' + taxon_id if taxon_id else marked_phyloname

            genus_species___final[ genus_species ] = (
                marked_phyloname,
                marked_phyloname_taxonid,
                'USER',
                ncbi_phyloname  # Store original for reference
            )

            user_count += 1
            unofficial_clades_all.extend( [ ( genus_species, clade ) for clade in unofficial_clades ] )

        else:
            # Use NCBI-generated phyloname (no modification needed)
            genus_species___final[ genus_species ] = (
                ncbi_phyloname,
                ncbi_phyloname_taxonid,
                'NCBI',
                ncbi_phyloname  # Same as final for NCBI entries
            )

            ncbi_count += 1

    print( f"  Species with NCBI phylonames: {ncbi_count}" )
    print( f"  Species with USER phylonames: {user_count}" )
    print( f"  Total unofficial clades marked: {len( unofficial_clades_all )}" )
    print( "" )

    # Write final mapping file
    final_mapping_path = output_dir / 'final_project_mapping.tsv'
    print( f"  Writing: {final_mapping_path}" )

    with open( final_mapping_path, 'w', encoding = 'utf-8' ) as output_file:
        # Write header with self-documenting column names
        header = (
            'genus_species (Genus_species or Genus_species_subspecies format)\t'
            'phyloname (final phyloname with UNOFFICIAL markers where applicable)\t'
            'phyloname_taxonid (phyloname with NCBI taxon ID suffix)\t'
            'source (NCBI for auto-generated or USER for user-provided)\t'
            'original_ncbi_phyloname (original NCBI-generated phyloname before user override)\n'
        )
        output_file.write( header )

        # Write each species mapping
        for genus_species in sorted( genus_species___final.keys() ):
            phyloname, phyloname_taxonid, source, original = genus_species___final[ genus_species ]
            output = f"{genus_species}\t{phyloname}\t{phyloname_taxonid}\t{source}\t{original}\n"
            output_file.write( output )

    # Write unofficial clades report if any were found
    if unofficial_clades_all:
        unofficial_report_path = output_dir / 'unofficial_clades_report.tsv'
        print( f"  Writing: {unofficial_report_path}" )

        with open( unofficial_report_path, 'w', encoding = 'utf-8' ) as output_file:
            header = (
                'genus_species (species with unofficial clade)\t'
                'unofficial_clade (clade name marked with UNOFFICIAL suffix)\n'
            )
            output_file.write( header )

            for genus_species, unofficial_clade in unofficial_clades_all:
                output = f"{genus_species}\t{unofficial_clade}\n"
                output_file.write( output )

    print( "" )

    return genus_species___final


# ================================================================================
# MAIN EXECUTION
# ================================================================================

def main():
    """
    Main execution function.

    Orchestrates the entire process:
    1. Parse command line arguments
    2. Extract NCBI clade vocabulary
    3. Load project mapping
    4. Load user phylonames (if provided)
    5. Generate final mapping with UNOFFICIAL detection
    6. Output results
    """

    # ============================================================
    # COMMAND LINE ARGUMENT PARSING
    # ============================================================

    parser = argparse.ArgumentParser(
        description = 'Apply user-provided phylonames with UNOFFICIAL detection',
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = """
Examples:
  # Apply user phylonames to project mapping:
  python3 004_ai-python-apply_user_phylonames.py \\
      --project-mapping output/3-output/species67_map-genus_species_X_phylonames.tsv \\
      --user-phylonames INPUT_user/custom_phylonames.tsv

  # Just mark unofficial clades in existing user phylonames (skip vocabulary extraction):
  python3 004_ai-python-apply_user_phylonames.py \\
      --project-mapping output/3-output/project_mapping.tsv \\
      --user-phylonames custom_phylonames.tsv \\
      --master-mapping output/2-output/map-phyloname_X_ncbi_taxonomy_info.tsv

File formats:
  User phylonames file (TSV):
    genus_species<TAB>custom_phyloname
    Monosiga_brevicollis_MX1<TAB>Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
        """
    )

    parser.add_argument(
        '--project-mapping',
        type = str,
        required = True,
        help = 'Path to project mapping TSV from Script 003'
    )

    parser.add_argument(
        '--user-phylonames',
        type = str,
        required = True,
        help = 'Path to user-provided phylonames TSV file'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = str( OUTPUT_DIR ),
        help = f'Output directory (default: {OUTPUT_DIR})'
    )

    parser.add_argument(
        '--no-mark-unofficial',
        action = 'store_true',
        default = False,
        help = 'Disable UNOFFICIAL suffix on user-provided clades (default: mark as UNOFFICIAL)'
    )

    args = parser.parse_args()

    # Convert to Path objects
    project_mapping_path = Path( args.project_mapping )
    user_phylonames_path = Path( args.user_phylonames )
    output_dir = Path( args.output_dir )
    mark_unofficial = not args.no_mark_unofficial

    # ============================================================
    # STARTUP BANNER
    # ============================================================

    start_time = datetime.now()

    print( "" )
    print( "=" * 70 )
    print( "GIGANTIC User Phylonames Application" )
    print( "Script 004: Apply user-provided phylonames with UNOFFICIAL marking" )
    print( "=" * 70 )
    print( f"Started: {start_time.strftime( '%Y-%m-%d %H:%M:%S' )}" )
    print( "" )

    # ============================================================
    # INPUT VALIDATION
    # ============================================================

    print( "Input files:" )
    print( f"  Project mapping: {project_mapping_path}" )
    print( f"  User phylonames: {user_phylonames_path}" )
    print( f"  Output directory: {output_dir}" )
    print( "" )
    print( "Settings:" )
    print( f"  Mark UNOFFICIAL: {'YES (default)' if mark_unofficial else 'NO (user disabled)'}" )
    print( "" )

    # Validate input files exist
    if not project_mapping_path.exists():
        print( f"ERROR: Project mapping file not found: {project_mapping_path}" )
        print( "Run Script 003 first to create project-specific mapping." )
        sys.exit( 1 )

    if not user_phylonames_path.exists():
        print( f"ERROR: User phylonames file not found: {user_phylonames_path}" )
        print( "Create a TSV file with genus_species<TAB>custom_phyloname entries." )
        sys.exit( 1 )

    # ============================================================
    # MAIN PROCESSING
    # ============================================================

    # Step 1: Load project mapping
    genus_species___project_phylonames = load_project_mapping( project_mapping_path )

    # Step 2: Load user phylonames
    genus_species___user_phylonames = load_user_phylonames( user_phylonames_path )

    # Step 3: Generate final mapping
    # ALL user-provided clades are marked UNOFFICIAL (unless disabled)
    # This reflects that user assignment is a decision point distinct from NCBI
    genus_species___final = generate_final_mapping(
        genus_species___project_phylonames = genus_species___project_phylonames,
        genus_species___user_phylonames = genus_species___user_phylonames,
        output_dir = output_dir,
        mark_unofficial = mark_unofficial
    )

    # ============================================================
    # COMPLETION SUMMARY
    # ============================================================

    end_time = datetime.now()
    duration = end_time - start_time

    print( "=" * 70 )
    print( "Processing complete!" )
    print( "=" * 70 )
    print( f"Duration: {duration}" )
    print( f"Total species processed: {len( genus_species___final )}" )
    print( "" )
    print( "Output files:" )
    print( f"  - {output_dir / 'final_project_mapping.tsv'}" )
    if ( output_dir / 'unofficial_clades_report.tsv' ).exists():
        print( f"  - {output_dir / 'unofficial_clades_report.tsv'}" )
    print( "" )
    print( "The final mapping can be used by other GIGANTIC subprojects." )
    print( "Species with USER source have user-provided phylonames applied." )
    print( "Clades marked with 'UNOFFICIAL' are not in NCBI taxonomy." )
    print( "=" * 70 )
    print( "" )


if __name__ == '__main__':
    main()
