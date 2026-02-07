#!/usr/bin/env python3
# AI: Claude Code | Opus 4.5 | 2026 February 05 | Purpose: Parse NCBI taxonomy to generate standardized phylonames
# Human: Eric Edsinger

"""
PHYLONAME GENERATOR FROM NCBI TAXONOMY

================================================================================
SCRIPT PURPOSE (For Non-Programmers):
================================================================================
This script reads the NCBI taxonomy database and creates standardized
"phylonames" - consistent naming identifiers for every species that include
their complete taxonomic lineage.

WHAT ARE PHYLONAMES?
GIGANTIC uses two phyloname formats:

1. phyloname (standard format):
   Kingdom_Phylum_Class_Order_Family_Genus_species
   Example: Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens

2. phyloname_taxonid (extended format):
   Kingdom_Phylum_Class_Order_Family_Genus_species___taxonID
   Example: Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens___9606

WHY DO THIS?
- Makes species names self-documenting (you can see the full classification)
- Ensures unique identifiers (no ambiguity between species)
- Enables systematic file organization across thousands of genomes
- phyloname_taxonid guarantees uniqueness even for species with identical names

THE PROCESS:
1. Reads NCBI's rankedlineage.dmp file (contains all species classifications)
2. For each species, extracts: Kingdom, Phylum, Class, Order, Family, Genus, Species
3. Cleans up special characters that cause problems in filenames
4. For missing taxonomy levels, GIGANTIC assigns numbered identifiers (e.g., Family1426)
   based on the first named clade below - this groups related species together
5. Creates both phyloname and phyloname_taxonid formats
6. Outputs multiple files for different use cases including a reference table

IMPORTANT CONCEPTUAL NOTES:
- NCBI Taxonomy is INCOMPLETE: Many species lack classifications at certain levels
- NCBI Taxonomy is ONE HYPOTHESIS: It represents one view of phylogenetic history,
  not absolute truth. Alternative phylogenetic frameworks exist.
- NUMBERED CLADES (e.g., Kingdom6555, Family1426) are GIGANTIC's solution to gaps
  in NCBI data - they are NOT assigned by NCBI. These provide an unbiased, neutral
  way to fill gaps while preserving phylogenetic information based on shared
  ancestry of all species within a given clade below an unknown clade.
- Users can provide their own phylonames via Script 004 to use alternative
  taxonomy based on current literature or different phylogenetic hypotheses.

INPUT FORMAT (from NCBI):
The rankedlineage.dmp file has pipe-delimited fields:
taxon_id | species_name | species | genus | family | order | class | phylum | kingdom | superkingdom |

================================================================================
TECHNICAL NOTES (For Python/CS Experts):
================================================================================
MODERNIZATIONS APPLIED:
- pathlib for file handling
- f-strings for string formatting
- Type hints for documentation
- Context managers for file handling
- Extracted character cleaning into reusable function
- Comprehensive error handling
- Constants for magic numbers/strings
- Both phyloname formats generated in single pass
"""

from pathlib import Path
from typing import List, Optional, Tuple
import sys
import os
from datetime import datetime

# Find the database directory (latest or specified)
def find_database_directory() -> Path:
    """
    Find the NCBI taxonomy database directory.

    Looks for:
    1. database-ncbi_taxonomy_latest symlink (preferred)
    2. Most recent database-ncbi_taxonomy_* directory

    Returns:
        Path to database directory

    Raises:
        SystemExit if no database found
    """
    # Check for symlink first
    symlink_path = Path( 'database-ncbi_taxonomy_latest' )
    if symlink_path.exists():
        return symlink_path

    # Look for versioned directories
    database_dirs = sorted( Path( '.' ).glob( 'database-ncbi_taxonomy_*' ), reverse = True )
    if database_dirs:
        return database_dirs[ 0 ]

    # No database found
    print( "ERROR: No NCBI taxonomy database found!" )
    print( "Expected: database-ncbi_taxonomy_latest symlink" )
    print( "      or: database-ncbi_taxonomy_YYYYMMDD_HHMMSS/ directory" )
    print( "" )
    print( "Run 001_ai-bash-download_ncbi_taxonomy.sh first to download the database." )
    sys.exit( 1 )


# Configuration
DATABASE_DIR = find_database_directory()
DATABASE_PATH = DATABASE_DIR / 'rankedlineage.dmp'
OUTPUT_DIR = Path( 'output/2-output' )

# Output files
PHYLONAMES_FILE = OUTPUT_DIR / 'phylonames'
PHYLONAMES_TAXONID_FILE = OUTPUT_DIR / 'phylonames_taxonid'
MAP_FILE = OUTPUT_DIR / 'map-phyloname_X_ncbi_taxonomy_info.tsv'
FAILED_FILE = OUTPUT_DIR / 'failed-entries.txt'
METADATA_FILE = OUTPUT_DIR / 'generation_metadata.txt'
UNKNOWN_CLADE_REFERENCE_FILE = OUTPUT_DIR / 'map-numbered_clades_X_defining_clades.tsv'

# Global tracking for numbered unknown clades
# Key: (clade_type, first_named_clade_below)
# Value: assigned number
unknown_clade_assignments___numbers = {}
unknown_clade_counter = 0

# Characters that need to be removed or replaced in phylonames
# These can cause problems in filenames or downstream processing
PROBLEMATIC_CHARS = [ '(', ')', '[', ']', '/', '.', "'", ':', '-' ]


def get_numbered_unknown_clade( clade_type: str, first_named_clade_below: str ) -> str:
    """
    Get or assign a numbered identifier for an unknown clade.

    When a taxonomy level is missing (e.g., no Kingdom in NCBI), we assign a
    unique number based on the first named clade BELOW it. This ensures that
    species sharing the same lower clade get the same unknown clade number,
    grouping related species together despite missing higher taxonomy.

    Format: CladeTypeNumber (e.g., Kingdom42, Family1426)
    No underscore between type and number to keep it compact.

    Args:
        clade_type: The taxonomy level (Kingdom, Phylum, Class, Order, Family)
        first_named_clade_below: The first named clade below this unknown level

    Returns:
        Numbered clade identifier (e.g., "Kingdom42")
    """
    global unknown_clade_counter

    # Create lookup key
    lookup_key = ( clade_type, first_named_clade_below )

    # Check if we've already assigned a number for this combination
    if lookup_key in unknown_clade_assignments___numbers:
        assigned_number = unknown_clade_assignments___numbers[ lookup_key ]
    else:
        # Assign next number
        unknown_clade_counter += 1
        assigned_number = unknown_clade_counter
        unknown_clade_assignments___numbers[ lookup_key ] = assigned_number

    # Return compact format: CladeTypeNumber (no underscore)
    numbered_clade = f"{clade_type}{assigned_number}"
    return numbered_clade


def clean_word( word: str ) -> str:
    """
    Remove problematic characters from a word for use in phylonames.

    Characters like parentheses, brackets, slashes, etc. can cause issues in:
    - File system paths
    - Command line arguments
    - Database queries

    Strategy: Split on each character, keep non-empty parts, join with underscore

    Args:
        word: String to clean

    Returns:
        Cleaned string with problematic characters replaced by underscores
    """
    for char in PROBLEMATIC_CHARS:
        # Split on problematic character and filter out empty strings
        parts = [ part for part in word.split( char ) if part ]
        # Join parts with underscore
        word = '_'.join( parts )
    return word


def process_species_name( species_raw: str ) -> str:
    """
    Process the species name field from NCBI taxonomy.

    NCBI species names can have various formats:
    - "Homo sapiens" (normal)
    - "unclassified Bacteria" (needs special handling)
    - "Escherichia coli K-12" (has strain info)
    - Single word (actually genus name, not species)

    Args:
        species_raw: Raw species name from NCBI

    Returns:
        Cleaned species name suitable for phyloname
    """
    species_words = species_raw.split( ' ' )

    # Single word means no real species name provided
    if len( species_words ) <= 1:
        return 'species_unclassified'

    # "unclassified" in first position indicates unknown species
    if species_words[ 0 ] == 'unclassified':
        return 'species_unclassified'

    # Normal case: take everything after genus name (first word)
    # Join multiple words (handles subspecies, strains, etc.)
    species_parts = species_words[ 1: ]
    cleaned_parts = [ clean_word( word ) for word in species_parts ]
    return '_'.join( cleaned_parts )


def generate_phyloname(
    kingdom: str,
    phylum: str,
    class_name: str,
    order: str,
    family: str,
    genus: str,
    species: str
) -> str:
    """
    Generate a phyloname (standard format, no taxon ID).

    Format: Kingdom_Phylum_Class_Order_Family_Genus_species

    Args:
        kingdom: Kingdom name (e.g., Metazoa)
        phylum: Phylum name (e.g., Chordata)
        class_name: Class name (e.g., Mammalia)
        order: Order name (e.g., Primates)
        family: Family name (e.g., Hominidae)
        genus: Genus name (e.g., Homo)
        species: Species name (e.g., sapiens)

    Returns:
        Phyloname string
    """
    phyloname = f"{kingdom}_{phylum}_{class_name}_{order}_{family}_{genus}_{species}"
    return phyloname


def generate_phyloname_taxonid( phyloname: str, taxon_id: str ) -> str:
    """
    Generate a phyloname_taxonid (extended format with taxon ID).

    Format: Kingdom_Phylum_Class_Order_Family_Genus_species___taxonID

    Args:
        phyloname: Standard phyloname
        taxon_id: NCBI taxon ID

    Returns:
        Phyloname with taxon ID appended
    """
    phyloname_taxonid = f"{phyloname}___{taxon_id}"
    return phyloname_taxonid


def main():
    """Main execution function."""

    print( "=" * 70 )
    print( "GIGANTIC Phyloname Generator" )
    print( "=" * 70 )
    print( "" )

    # Verify database exists
    if not DATABASE_PATH.exists():
        print( f"ERROR: rankedlineage.dmp not found at: {DATABASE_PATH}" )
        print( "Run 001_ai-bash-download_ncbi_taxonomy.sh first." )
        sys.exit( 1 )

    # Ensure output directory exists
    OUTPUT_DIR.mkdir( parents = True, exist_ok = True )

    print( f"Reading NCBI taxonomy from: {DATABASE_PATH}" )
    print( f"Output directory: {OUTPUT_DIR}" )
    print( "" )

    # Record generation start time
    start_time = datetime.now()

    # Statistics counters
    processed_count = 0
    failed_count = 0

    # Open all files using context managers (automatic cleanup)
    with open( DATABASE_PATH, 'r', encoding = 'utf-8' ) as input_file, \
         open( PHYLONAMES_FILE, 'w', encoding = 'utf-8' ) as phylonames_output, \
         open( PHYLONAMES_TAXONID_FILE, 'w', encoding = 'utf-8' ) as phylonames_taxonid_output, \
         open( MAP_FILE, 'w', encoding = 'utf-8' ) as map_output, \
         open( FAILED_FILE, 'w', encoding = 'utf-8' ) as failed_output:

        # Write header for map file
        header = '\t'.join( [
            'phyloname',
            'phyloname_taxonid',
            'genus_species',
            'taxon_id',
            'ncbi_taxon_name',
            'ncbi_species',
            'ncbi_genus',
            'ncbi_family',
            'ncbi_order',
            'ncbi_class',
            'ncbi_phylum',
            'ncbi_kingdom',
            'ncbi_superkingdom'
        ] )
        output = header + '\n'
        map_output.write( output )

        # Process each line in the NCBI taxonomy dump
        # taxon_id | taxon_name | species | genus | family | order | class | phylum | kingdom | superkingdom |
        # 9606 | Homo sapiens | Homo sapiens | Homo | Hominidae | Primates | Mammalia | Chordata | Metazoa | Eukaryota |
        for line_number, line in enumerate( input_file, 1 ):

            try:
                # Parse the pipe-delimited line
                line = line.strip()
                parts = [ field.strip() for field in line.split( '|' ) ]

                if len( parts ) < 10:
                    # Malformed line, skip it
                    output = line + '\n'
                    failed_output.write( output )
                    failed_count += 1
                    continue

                # Extract taxonomy fields (indices match NCBI format)
                taxon_id = parts[ 0 ]
                taxon_name = parts[ 1 ]
                species_raw = parts[ 2 ]
                genus_raw = parts[ 3 ]
                family_raw = parts[ 4 ]
                order_raw = parts[ 5 ]
                class_raw = parts[ 6 ]
                phylum_raw = parts[ 7 ]
                kingdom_raw = parts[ 8 ]
                superkingdom_raw = parts[ 9 ]

                # Handle species extraction
                # NCBI format has two relevant fields:
                # - taxon_name (field [1]): Full name including strain/subspecies (e.g., "Monosiga brevicollis MX1")
                # - species_raw (field [2]): Parent species only (e.g., "Monosiga brevicollis")
                #
                # We prefer taxon_name because it preserves strain/subspecies info
                # This allows users to look up "Monosiga_brevicollis_MX1" and get the correct taxon ID
                if taxon_name:
                    # Use full taxon name to preserve strain/subspecies info
                    species = process_species_name( taxon_name )
                elif species_raw:
                    # Fallback to species field if taxon_name is empty
                    species = process_species_name( species_raw )
                else:
                    # No species information at all - skip
                    output = line + '\n'
                    failed_output.write( output )
                    failed_count += 1
                    continue

                # Process genus
                # If genus field is empty, try to extract from taxon_name
                if genus_raw:
                    genus = genus_raw.replace( '-', '_' )
                else:
                    # First word of taxon_name is usually genus
                    name_for_genus = taxon_name if taxon_name else species_raw
                    if name_for_genus:
                        genus_candidate = name_for_genus.split( ' ' )[ 0 ]
                        genus = 'Genus_unclassified' if genus_candidate == 'unclassified' else genus_candidate
                    else:
                        genus = 'Genus_unclassified'

                # Process higher taxonomy levels with numbered unknown clades
                # Work upward from genus, using the first named clade below each unknown level
                # This groups related species together despite missing higher taxonomy

                # Family: if unknown, genus is the first named clade below
                if family_raw:
                    family = family_raw
                else:
                    family = get_numbered_unknown_clade( 'Family', genus )

                # Order: if unknown, use family (or genus if family was also unknown)
                if order_raw:
                    order = order_raw
                else:
                    first_named_below = family_raw if family_raw else genus
                    order = get_numbered_unknown_clade( 'Order', first_named_below )

                # Class: if unknown, use order (or next named below)
                if class_raw:
                    class_name = class_raw
                else:
                    first_named_below = order_raw if order_raw else ( family_raw if family_raw else genus )
                    class_name = get_numbered_unknown_clade( 'Class', first_named_below )

                # Phylum: if unknown, use class (or next named below)
                if phylum_raw:
                    phylum = phylum_raw
                else:
                    first_named_below = class_raw if class_raw else ( order_raw if order_raw else ( family_raw if family_raw else genus ) )
                    phylum = get_numbered_unknown_clade( 'Phylum', first_named_below )

                # Kingdom: if unknown, use phylum (or next named below)
                if kingdom_raw:
                    kingdom = kingdom_raw
                else:
                    first_named_below = phylum_raw if phylum_raw else ( class_raw if class_raw else ( order_raw if order_raw else ( family_raw if family_raw else genus ) ) )
                    kingdom = get_numbered_unknown_clade( 'Kingdom', first_named_below )

                # Generate phyloname (standard format)
                phyloname = generate_phyloname(
                    kingdom = kingdom,
                    phylum = phylum,
                    class_name = class_name,
                    order = order,
                    family = family,
                    genus = genus,
                    species = species
                )

                # Generate phyloname_taxonid (extended format)
                phyloname_taxonid = generate_phyloname_taxonid( phyloname, taxon_id )

                # Create genus_species for easy lookup
                genus_species = f"{genus}_{species}"

                # Write phyloname to output
                output = phyloname + '\n'
                phylonames_output.write( output )

                # Write phyloname_taxonid to output
                output = phyloname_taxonid + '\n'
                phylonames_taxonid_output.write( output )

                # Build mapping output line
                map_line_parts = [
                    phyloname,
                    phyloname_taxonid,
                    genus_species,
                    taxon_id,
                    taxon_name,
                    species_raw,
                    genus_raw if genus_raw else 'MISSING',
                    family_raw if family_raw else 'MISSING',
                    order_raw if order_raw else 'MISSING',
                    class_raw if class_raw else 'MISSING',
                    phylum_raw if phylum_raw else 'MISSING',
                    kingdom_raw if kingdom_raw else 'MISSING',
                    superkingdom_raw if superkingdom_raw else 'MISSING'
                ]

                output = '\t'.join( map_line_parts ) + '\n'
                map_output.write( output )

                processed_count += 1

                # Progress indicator every 100,000 lines
                if processed_count % 100000 == 0:
                    print( f"  Processed {processed_count:,} species..." )

            except Exception as e:
                # Log any processing errors
                print( f"Error on line {line_number}: {e}" )
                output = line + '\n'
                failed_output.write( output )
                failed_count += 1

    # Record generation end time
    end_time = datetime.now()
    duration = end_time - start_time

    # Write unknown clade reference table
    # Maps numbered clades (e.g., Kingdom42) to their defining clade below
    with open( UNKNOWN_CLADE_REFERENCE_FILE, 'w', encoding = 'utf-8' ) as reference_output:
        header = 'numbered_clade\tclade_type\tdefining_clade_below\n'
        reference_output.write( header )

        # Sort by clade type and number for readability
        for ( clade_type, defining_clade ), number in sorted(
            unknown_clade_assignments___numbers.items(),
            key = lambda x: ( x[ 0 ][ 0 ], x[ 1 ] )
        ):
            numbered_clade = f"{clade_type}{number}"
            output = f"{numbered_clade}\t{clade_type}\t{defining_clade}\n"
            reference_output.write( output )

    print( f"  Numbered unknown clades assigned: {unknown_clade_counter:,}" )

    # Write generation metadata
    with open( METADATA_FILE, 'w', encoding = 'utf-8' ) as metadata_output:
        output = f"""Phyloname Generation Metadata
========================================
Source database: {DATABASE_PATH}
Generation start (local): {start_time.strftime( '%Y-%m-%d %H:%M:%S' )}
Generation end (local): {end_time.strftime( '%Y-%m-%d %H:%M:%S' )}
Duration: {duration}
Species processed: {processed_count:,}
Failed entries: {failed_count:,}
Numbered unknown clades assigned: {unknown_clade_counter:,}
Script: 002_ai-python-generate_phylonames.py
"""
        metadata_output.write( output )

    # Print summary statistics
    print( "" )
    print( "=" * 70 )
    print( "Processing complete!" )
    print( "=" * 70 )
    print( f"Successfully processed: {processed_count:,} species" )
    print( f"Failed to process: {failed_count:,} entries" )
    print( f"Duration: {duration}" )
    print( "" )
    print( "Output files created:" )
    print( f"  - {PHYLONAMES_FILE} (standard phylonames)" )
    print( f"  - {PHYLONAMES_TAXONID_FILE} (phylonames with taxon ID)" )
    print( f"  - {MAP_FILE} (full mapping with NCBI data)" )
    print( f"  - {UNKNOWN_CLADE_REFERENCE_FILE} (numbered clade reference)" )
    print( f"  - {FAILED_FILE} (entries that could not be processed)" )
    print( f"  - {METADATA_FILE} (generation metadata)" )
    print( "" )
    print( "Next step: Run 003_ai-python-create_species_mapping.py" )
    print( "=" * 70 )


if __name__ == '__main__':
    main()
