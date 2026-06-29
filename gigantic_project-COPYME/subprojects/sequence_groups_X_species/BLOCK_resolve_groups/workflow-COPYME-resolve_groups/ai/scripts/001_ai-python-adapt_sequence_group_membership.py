# AI: Claude Code | Opus 4.8 | 2026 June 28 | Purpose: Adapt a producer's native group output into the STANDARD sequence-group membership (SequenceGroup_ID, Sequence_Identifier, Genus_Species)
# Human: Eric Edsinger

"""
Script 001 — Adapt a producer's sequence-group set into the standard membership.

This subproject resolves ANY "sequence group" onto the species-tree clades. The one
producer-specific step is reading the group set's native output into a single
STANDARD membership table; every downstream script (deconvolution, per-species map,
composite clades) reads only that standard table, so they are producer-agnostic.

Standard membership (1-output/1_ai-<group_set_label>-sequence_group_membership.tsv):
    SequenceGroup_ID  Sequence_Identifier  Genus_Species
one row per (member sequence, group).

Producers (config 'producer'):
  - orthogroups : reads orthogroups_gigantic_ids.tsv, a row per orthogroup
        OG_id <TAB> member_seq_id <TAB> member_seq_id <TAB> ...
    where each member id embeds its phyloname after '-n_' (Genus_species parsed
    from there). Adding a producer = add a small reader branch here; nothing
    downstream changes.

Fail-fast (§36): exits 1 if the input is missing, the producer is unknown, the
output is empty, or any member id has no parseable Genus_species (silent loss).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent ) )
import utils_sequence_groups as U


def read_orthogroups( producer_membership_path: Path ):
    """
    Yield ( sequence_group_id, sequence_identifier, genus_species ) from an
    orthogroups_gigantic_ids.tsv (one orthogroup per line; members tab-delimited
    after the orthogroup id; Genus_species parsed from each member's '-n_<phyloname>').
    """
    # OG000000	g_..-n_<phyloname>	g_..-n_<phyloname>	...
    # OG000001	g_..-n_<phyloname>	...
    with open( producer_membership_path, 'r' ) as input_membership:
        for line in input_membership:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            sequence_group_id = parts[ 0 ]
            for sequence_identifier in parts[ 1: ]:
                sequence_identifier = sequence_identifier.strip()
                if not sequence_identifier:
                    continue
                genus_species = U.genus_species_from_full_id( sequence_identifier )
                yield ( sequence_group_id, sequence_identifier, genus_species )


PRODUCER_READERS = {
    "orthogroups": read_orthogroups,
}


def main():
    parser = argparse.ArgumentParser( description = "Adapt a producer's sequence-group set into the standard membership" )
    parser.add_argument( '--config', required = True )
    parser.add_argument( '--output_dir', required = True )
    args = parser.parse_args()

    config = U.load_config( args.config )
    workflow_root = U.workflow_root_from_output_dir( args.output_dir )

    group_set_label = config[ "group_set_label" ]
    producer = config[ "producer" ]
    if producer not in PRODUCER_READERS:
        print( f"CRITICAL ERROR: unknown producer '{producer}'; known producers: {sorted( PRODUCER_READERS )}", file = sys.stderr )
        sys.exit( 1 )

    producer_membership_path = U.resolve_input_path( workflow_root, config[ "inputs" ][ "producer_membership" ] )
    if not producer_membership_path.is_file():
        print( f"CRITICAL ERROR: producer membership not found: {producer_membership_path}", file = sys.stderr )
        sys.exit( 1 )

    output_dir = Path( args.output_dir ) / "1-output"
    output_dir.mkdir( parents = True, exist_ok = True )
    output_path = output_dir / f"1_ai-{group_set_label}-sequence_group_membership.tsv"

    header = (
        "SequenceGroup_ID (identifier of the sequence group from the producer)\t"
        "Sequence_Identifier (full GIGANTIC member sequence identifier)\t"
        "Genus_Species (Genus_species of the member, parsed from the sequence identifier)\n"
    )

    rows_written = 0
    groups = set()
    members_without_species = []
    with open( output_path, 'w' ) as output_file:
        output_file.write( header )
        for ( sequence_group_id, sequence_identifier, genus_species ) in PRODUCER_READERS[ producer ]( producer_membership_path ):
            if not genus_species:
                if len( members_without_species ) < 5:
                    members_without_species.append( sequence_identifier )
                continue
            output = sequence_group_id + '\t' + sequence_identifier + '\t' + genus_species + '\n'
            output_file.write( output )
            rows_written += 1
            groups.add( sequence_group_id )

    if members_without_species:
        print( f"CRITICAL ERROR: {len( members_without_species )}+ member ids had no parseable Genus_species "
               f"(silent member loss); examples: {members_without_species}", file = sys.stderr )
        sys.exit( 1 )
    if rows_written == 0:
        print( f"CRITICAL ERROR: zero member rows written from {producer_membership_path.name}", file = sys.stderr )
        sys.exit( 1 )

    print( f"[001 {group_set_label}] adapted {producer}: {rows_written} member rows across {len( groups )} sequence groups "
           f"-> {output_path.name}" )


if __name__ == '__main__':
    main()
