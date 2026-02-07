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
NCBI taxonomy often has missing levels. For example, Monosiga brevicollis gets:
    Kingdom6555_Phylum6554_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1

But based on current literature, you might prefer:
    Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1

THE UNOFFICIAL SUFFIX:
When you provide custom clade names that don't exist in NCBI taxonomy, this
script automatically marks them with "UNOFFICIAL" to maintain transparency:
    Holozoa_ChoanozoaUNOFFICIAL_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1

This way, anyone looking at the phyloname knows:
- "Holozoa" IS in NCBI taxonomy (no suffix)
- "ChoanozoaUNOFFICIAL" is a USER-PROVIDED name not in NCBI

IMPORTANT CAVEAT - WHEN NUMBERED CLADES REMAIN:
Even after applying user phylonames, you may still see numbered clades like
"Family1426" in your final output. This happens when:

1. User phylonames weren't provided for that species
2. User phylonames were provided but didn't specify all levels
3. The species simply wasn't in your user phylonames file

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
from typing import Dict, List, Set, Tuple, Optional
import sys
import argparse
from datetime import datetime


# ================================================================================
# CONFIGURATION
# ================================================================================
# These paths are defaults; can be overridden via command line arguments

OUTPUT_DIR = Path( 'output/4-output' )
DEFAULT_MASTER_MAPPING = Path( 'output/2-output/map-phyloname_X_ncbi_taxonomy_info.tsv' )
DEFAULT_PROJECT_MAPPING = Path( 'output/3-output' )  # Will search for mapping file here


# ================================================================================
# NCBI VOCABULARY EXTRACTION
# ================================================================================
# This section extracts all valid NCBI clade names from the master mapping.
# These names will be used to detect which user-provided clades are "unofficial".

def extract_ncbi_clade_vocabulary( master_mapping_path: Path ) -> Dict[ str, Set[ str ] ]:
    """
    Extract all unique clade names at each taxonomic level from NCBI data.

    This function parses the master phyloname mapping and collects every unique
    clade name that appears at each taxonomic position (Kingdom, Phylum, etc.).

    The resulting vocabulary is used to detect which user-provided clade names
    are NOT in NCBI taxonomy (and therefore should be marked as UNOFFICIAL).

    IMPORTANT: Numbered clades (e.g., Kingdom6555) are EXCLUDED from the vocabulary
    because they represent missing data, not official NCBI names.

    Args:
        master_mapping_path: Path to the master phyloname mapping TSV

    Returns:
        Dictionary mapping taxonomic level -> set of valid NCBI clade names
        Example: { 'Kingdom': {'Metazoa', 'Holomycota', ...}, 'Phylum': {...}, ... }
    """

    print( "=" * 70 )
    print( "STEP 1: Extracting NCBI clade vocabulary" )
    print( "=" * 70 )
    print( f"  Source: {master_mapping_path}" )
    print( "" )

    # Initialize sets for each taxonomic level
    # Using sets for O(1) lookup when checking if a clade is official
    ncbi_clades___by_level = {
        'Kingdom': set(),
        'Phylum': set(),
        'Class': set(),
        'Order': set(),
        'Family': set(),
        'Genus': set()
    }

    # Pattern to detect numbered clades that should be excluded
    # These represent missing NCBI data, not official names
    import re
    numbered_clade_pattern = re.compile( r'^(Kingdom|Phylum|Class|Order|Family|Genus)\d+$' )

    entries_processed = 0

    # phyloname	phyloname_taxonid	genus_species	taxon_id	...
    # Kingdom_Phylum_Class_Order_Family_Genus_species	...	Genus_species	12345	...
    with open( master_mapping_path, 'r', encoding = 'utf-8' ) as input_file:
        # Skip header line
        header = input_file.readline()

        for line in input_file:
            line = line.strip()
            if not line:
                continue

            parts = line.split( '\t' )
            if len( parts ) < 1:
                continue

            phyloname = parts[ 0 ]

            # Split phyloname into clade components
            # Format: Kingdom_Phylum_Class_Order_Family_Genus_species
            parts_phyloname = phyloname.split( '_' )

            # Need at least 7 parts for valid phyloname
            if len( parts_phyloname ) < 7:
                continue

            # Extract each taxonomic level
            # Position 0 = Kingdom, 1 = Phylum, 2 = Class, 3 = Order, 4 = Family, 5 = Genus
            taxonomic_levels = [ 'Kingdom', 'Phylum', 'Class', 'Order', 'Family', 'Genus' ]

            for position, level_name in enumerate( taxonomic_levels ):
                clade_name = parts_phyloname[ position ]

                # Skip numbered clades (they represent missing data)
                # These should NOT be in the official vocabulary
                if numbered_clade_pattern.match( clade_name ):
                    continue

                # Skip "unclassified" placeholders from older format
                if 'unclassified' in clade_name.lower():
                    continue

                # Add to vocabulary for this level
                ncbi_clades___by_level[ level_name ].add( clade_name )

            entries_processed += 1

            # Progress indicator for large files
            if entries_processed % 500000 == 0:
                print( f"  Processed {entries_processed:,} entries..." )

    # Report vocabulary statistics
    print( "" )
    print( "  NCBI clade vocabulary extracted:" )
    for level_name, clade_set in ncbi_clades___by_level.items():
        print( f"    {level_name}: {len( clade_set ):,} unique official names" )
    print( "" )

    return ncbi_clades___by_level


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
    print( "STEP 2: Loading project mapping" )
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
    print( "STEP 3: Loading user-provided phylonames" )
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
# UNOFFICIAL CLADE DETECTION
# ================================================================================
# Mark clades that are not in NCBI taxonomy with "UNOFFICIAL" suffix.

def mark_unofficial_clades(
    phyloname: str,
    ncbi_clades___by_level: Dict[ str, Set[ str ] ]
) -> Tuple[ str, List[ str ] ]:
    """
    Check each clade in a phyloname and mark unofficial ones.

    For each taxonomic level (Kingdom, Phylum, Class, Order, Family):
    - If the clade name exists in NCBI vocabulary: keep as-is
    - If the clade name does NOT exist in NCBI: append "UNOFFICIAL"

    This preserves transparency about which names come from NCBI versus
    user-provided custom assignments.

    NOTE: Genus and species are NOT checked - users are expected to provide
    valid genus/species combinations, and these may legitimately differ
    from NCBI (e.g., subspecies, strains).

    Args:
        phyloname: The phyloname to check (Kingdom_Phylum_Class_Order_Family_Genus_species)
        ncbi_clades___by_level: Dictionary of NCBI vocabulary sets

    Returns:
        Tuple of:
        - Modified phyloname with UNOFFICIAL suffixes added
        - List of clades that were marked as unofficial
    """

    # Split phyloname into components
    parts_phyloname = phyloname.split( '_' )

    # Need at least 7 parts for valid phyloname
    if len( parts_phyloname ) < 7:
        return phyloname, []

    # Track which clades we mark as unofficial
    unofficial_clades = []

    # Check each taxonomic level (positions 0-4: Kingdom through Family)
    # We do NOT check Genus (position 5) or species (position 6+)
    taxonomic_levels = [ 'Kingdom', 'Phylum', 'Class', 'Order', 'Family' ]

    for position, level_name in enumerate( taxonomic_levels ):
        clade_name = parts_phyloname[ position ]

        # Skip if already marked unofficial (don't double-mark)
        if clade_name.endswith( 'UNOFFICIAL' ):
            unofficial_clades.append( clade_name )
            continue

        # Skip numbered clades - these are from NCBI's numbered unknown system
        # They indicate missing data but are technically "official" (from our processing)
        import re
        if re.match( r'^(Kingdom|Phylum|Class|Order|Family)\d+$', clade_name ):
            continue

        # Check if clade exists in NCBI vocabulary
        ncbi_clades_for_level = ncbi_clades___by_level.get( level_name, set() )

        if clade_name not in ncbi_clades_for_level:
            # Mark as unofficial by appending suffix
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
    ncbi_clades___by_level: Dict[ str, Set[ str ] ],
    output_dir: Path
) -> Dict[ str, Tuple[ str, str, str, str ] ]:
    """
    Generate the final mapping by merging project and user phylonames.

    For each species in the project:
    - If user provided a custom phyloname: use it (with UNOFFICIAL marking)
    - Otherwise: use the NCBI-generated phyloname

    This function also:
    - Generates the taxon_id version of the final phyloname
    - Tracks data source (NCBI vs USER)
    - Records original phyloname for reference

    Args:
        genus_species___project_phylonames: From Script 003
        genus_species___user_phylonames: User-provided overrides
        ncbi_clades___by_level: NCBI vocabulary for unofficial detection
        output_dir: Directory for output files

    Returns:
        Dictionary: genus_species -> (final_phyloname, phyloname_taxonid, source, original_phyloname)
    """

    print( "=" * 70 )
    print( "STEP 4: Generating final mapping with UNOFFICIAL detection" )
    print( "=" * 70 )

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

            # Mark unofficial clades
            marked_phyloname, unofficial_clades = mark_unofficial_clades(
                phyloname = user_phyloname,
                ncbi_clades___by_level = ncbi_clades___by_level
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
        '--master-mapping',
        type = str,
        default = str( DEFAULT_MASTER_MAPPING ),
        help = f'Path to master phyloname mapping (default: {DEFAULT_MASTER_MAPPING})'
    )

    parser.add_argument(
        '--output-dir',
        type = str,
        default = str( OUTPUT_DIR ),
        help = f'Output directory (default: {OUTPUT_DIR})'
    )

    args = parser.parse_args()

    # Convert to Path objects
    project_mapping_path = Path( args.project_mapping )
    user_phylonames_path = Path( args.user_phylonames )
    master_mapping_path = Path( args.master_mapping )
    output_dir = Path( args.output_dir )

    # ============================================================
    # STARTUP BANNER
    # ============================================================

    start_time = datetime.now()

    print( "" )
    print( "=" * 70 )
    print( "GIGANTIC User Phylonames Application" )
    print( "Script 004: Apply user-provided phylonames with UNOFFICIAL detection" )
    print( "=" * 70 )
    print( f"Started: {start_time.strftime( '%Y-%m-%d %H:%M:%S' )}" )
    print( "" )

    # ============================================================
    # INPUT VALIDATION
    # ============================================================

    print( "Input files:" )
    print( f"  Project mapping: {project_mapping_path}" )
    print( f"  User phylonames: {user_phylonames_path}" )
    print( f"  Master mapping:  {master_mapping_path}" )
    print( f"  Output directory: {output_dir}" )
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

    if not master_mapping_path.exists():
        print( f"ERROR: Master mapping file not found: {master_mapping_path}" )
        print( "Run Script 002 first to generate master phyloname mapping." )
        sys.exit( 1 )

    # ============================================================
    # MAIN PROCESSING
    # ============================================================

    # Step 1: Extract NCBI vocabulary for unofficial detection
    ncbi_clades___by_level = extract_ncbi_clade_vocabulary( master_mapping_path )

    # Step 2: Load project mapping
    genus_species___project_phylonames = load_project_mapping( project_mapping_path )

    # Step 3: Load user phylonames
    genus_species___user_phylonames = load_user_phylonames( user_phylonames_path )

    # Step 4: Generate final mapping
    genus_species___final = generate_final_mapping(
        genus_species___project_phylonames = genus_species___project_phylonames,
        genus_species___user_phylonames = genus_species___user_phylonames,
        ncbi_clades___by_level = ncbi_clades___by_level,
        output_dir = output_dir
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
