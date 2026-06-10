# AI: Claude Code | Opus 4.8 | 2026 June 03 | Purpose: Compare ctenophore vs sponge at equivalent phylogenetic depth by summing OCL block-states along the path from Metazoa to each clade (basal clade = 1 block; depth-2 clade = 2 blocks summed)
# Human: Eric Edsinger
#
# structure_001 (Ctenophora basal): Ctenophora (1 block) vs Porifera path (Metazoa->parent + parent->Porifera).
# structure_003 (Porifera basal):   Porifera (1 block)   vs Ctenophora path (Metazoa->parent + parent->Ctenophora).
# States: O (origins, 2-output), P (conserved) and L (lost) (3-output per_block). A not computed by OCL; per-block X unavailable.

from pathlib import Path

PROJECT_ROOT = Path( __file__ ).resolve().parents[ 3 ]
OCL = PROJECT_ROOT / 'subprojects/ocl_phylogenetic_structures/BLOCK_orthogroups_X_ocl/workflow-RUN_1-ocl_analysis/OUTPUT_pipeline'

def load_structure( structure ):
    pc = OCL / structure / '1-output' / f'1_ai-{structure}_parent_child_table.tsv'
    children___parents = {}
    with open( pc ) as f:
        for line in f:
            parts = line.rstrip( '\n' ).split( '\t' )
            if len( parts ) < 3 or 'Parent' in parts[ 1 ]:
                continue
            block, parent, child = parts[ 0 ], parts[ 1 ], parts[ 2 ]
            if parent == child:
                continue
            children___parents[ child ] = parent

    pb = OCL / structure / '3-output' / f'3_ai-{structure}_conservation_loss-per_block.tsv'
    block_PL = {}  # (parent, child) -> (P, L)
    with open( pb ) as f:
        f.readline()
        for line in f:
            p = line.rstrip( '\n' ).split( '\t' )
            block_PL[ ( p[ 0 ], p[ 1 ] ) ] = ( int( p[ 3 ] ), int( p[ 4 ] ) )

    origins = OCL / structure / '2-output' / f'2_ai-{structure}_origins_summary-orthogroups_per_clade.tsv'
    block_O = {}  # 'parent::child' -> O
    with open( origins ) as f:
        f.readline()
        for line in f:
            p = line.rstrip( '\n' ).split( '\t' )
            block_O[ p[ 0 ].rsplit( '-', 1 )[ 0 ] ] = int( p[ 1 ] )
    return children___parents, block_PL, block_O

def path_blocks( children___parents, target, stop='C082_Metazoa' ):
    """Ordered list of (parent, child) blocks from stop down to target."""
    chain = []
    node = target
    while node != stop and node in children___parents:
        parent = children___parents[ node ]
        chain.append( ( parent, node ) )
        node = parent
    chain.reverse()
    return chain

def report( structure, target_id, target_name ):
    cp, block_PL, block_O = load_structure( structure )
    blocks = path_blocks( cp, target_id )
    tot_O = tot_P = tot_L = 0
    lines = []
    for ( parent, child ) in blocks:
        P, L = block_PL.get( ( parent, child ), ( 0, 0 ) )
        O = block_O.get( f'{parent}::{child}', 0 )
        tot_O += O; tot_P += P; tot_L += L
        lines.append( f"      {parent} -> {child}:  O={O}  P={P}  L={L}" )
    print( f"  {target_name} in {structure}  ({len(blocks)} block{'s' if len(blocks)!=1 else ''}):  SUM  O={tot_O}  P={tot_P}  L={tot_L}" )
    for l in lines:
        print( l )

print( "=== structure_001 (Ctenophora basal) — depth-equalized ===" )
report( 'structure_001', 'C086_Ctenophora', 'Ctenophora' )
report( 'structure_001', 'C090_Porifera', 'Porifera (parent_to_porifera + porifera)' )
print()
print( "=== structure_003 (Porifera basal, = 001 with sponge/cteno swapped) — depth-equalized ===" )
report( 'structure_003', 'C090_Porifera', 'Porifera' )
report( 'structure_003', 'C086_Ctenophora', 'Ctenophora (parent_to_ctenophora + ctenophore)' )
print( "\nNote: O=origins, P=conserved, L=lost (OCL block-states). A not computed by OCL; per-block X unavailable." )
